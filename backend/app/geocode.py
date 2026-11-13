"""카카오 로컬 API 로 업소 주소를 좌표(위도/경도)로 변환한다.

- 주소 단위로 한 번만 호출하고, 같은 주소의 업소 모두에 좌표를 저장한다.
- geocode_status 가 NULL 인 주소만 대상 (retry_failed=True 면 'error' 도 포함).
  이미 좌표가 있거나 not_found 로 확인된 주소는 건너뛴다.
- 1) 주소 검색 → 2) 결과 없으면 키워드 검색(시군구 + 업소명) 순으로 시도한다.
- 초당 호출 수 제한, 일시 오류(네트워크/429/5xx)는 재시도, 끝내 실패하면 'error' 로 기록한다.
"""

import asyncio
import logging
import re
import time
from datetime import datetime, timezone

import httpx

from . import config, db

log = logging.getLogger("hygiene.geocode")

_lock = asyncio.Lock()
_cancel = asyncio.Event()

MAX_RETRIES = 3
PROGRESS_EVERY = 25  # 몇 건마다 진행률/DB 를 기록할지


class GeocodeError(Exception):
    pass


class _AuthError(GeocodeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _mask(text: str) -> str:
    """카카오 오류 메시지는 키를 그대로 되돌려 주므로(wrong appKey(...)) 저장·로그 전에 가린다."""
    text = re.sub(r"appKey\([^)]*\)", "appKey(***)", text)
    key = config.KAKAO_REST_API_KEY
    return text.replace(key, "***") if key else text


class RateLimiter:
    """초당 rps 회를 넘지 않게 호출 간격을 맞춘다 (여러 작업자가 공유)."""

    def __init__(self, rps: float):
        self.interval = 1.0 / max(rps, 0.1)
        self._next = 0.0
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        async with self._lock:
            now = time.monotonic()
            delay = self._next - now
            self._next = max(now, self._next) + self.interval
        if delay > 0:
            await asyncio.sleep(delay)


# ---------- 주소 정리 ----------

_ROAD_NUMBER = re.compile(r"^(.*?(?:로|길)\s*\d+(?:-\d+)?)(?:\s|$)")
_LOT_NUMBER = re.compile(r"^(.*?(?:동|가|리)\s+(?:산\s*)?\d+(?:-\d+)?)(?:\s|$)")


def address_queries(addr: str) -> list[str]:
    """주소 검색에 쓸 후보 문자열. 괄호/쉼표 뒤 상세주소를 떼고, 건물번호까지만 자른 형태도 시도한다."""
    base = re.split(r"[(,]", addr, maxsplit=1)[0].strip()
    base = re.sub(r"\s+", " ", base)
    out = [base] if base else []
    for pat in (_ROAD_NUMBER, _LOT_NUMBER):
        m = pat.match(base)
        if m and m.group(1).strip() not in out:
            out.append(m.group(1).strip())
    return out


def region_of(addr: str) -> str:
    """키워드 검색과 결과 검증에 쓰는 지역명: 시군구 (세종은 시도명)."""
    tokens = addr.split()
    if not tokens:
        return ""
    if tokens[0].startswith("세종") or len(tokens) < 2:
        return tokens[0]
    return tokens[1]


def keyword_query(addr: str, name: str) -> str | None:
    region = region_of(addr)
    name = re.sub(r"^[^0-9A-Za-z가-힣]+", "", name or "").strip()
    return f"{region} {name}".strip() if name else None


# ---------- 카카오 API ----------


async def _call(client: httpx.AsyncClient, limiter: RateLimiter, path: str, query: str) -> list[dict]:
    last: Exception | None = None
    for attempt in range(MAX_RETRIES):
        await limiter.wait()
        try:
            resp = await client.get(f"{config.KAKAO_API_BASE}{path}", params={"query": query, "size": 5})
            if resp.status_code in (401, 403):
                # 키 문제 — 계속해도 모두 실패하므로 작업 전체를 멈춘다 (키 값은 남기지 않는다)
                err = resp.json().get("message", "") if resp.headers.get("content-type", "").startswith("application/json") else ""
                raise _AuthError(_mask(f"카카오 API 인증 실패 ({resp.status_code}) {err}".strip()))
            if resp.status_code == 429 or resp.status_code >= 500:
                raise httpx.HTTPStatusError(f"HTTP {resp.status_code}", request=resp.request, response=resp)
            resp.raise_for_status()
            return resp.json().get("documents", []) or []
        except _AuthError:
            raise
        except (httpx.HTTPError, ValueError) as e:
            last = e
            await asyncio.sleep(1.0 * (2**attempt))
    raise GeocodeError(_mask(f"재시도 {MAX_RETRIES}회 실패: {type(last).__name__} {str(last)[:80]}"))


async def geocode_one(client, limiter, addr: str, name: str) -> tuple[str, float | None, float | None]:
    """(status, lat, lng). status: ok_address / ok_keyword / not_found"""
    for q in address_queries(addr):
        docs = await _call(client, limiter, "/v2/local/search/address.json", q)
        if docs:
            return "ok_address", float(docs[0]["y"]), float(docs[0]["x"])

    kq = keyword_query(addr, name)
    if kq:
        docs = await _call(client, limiter, "/v2/local/search/keyword.json", kq)
        region = region_of(addr)
        for d in docs:
            # 다른 지역의 같은 이름 가게를 잘못 잡지 않도록 시군구가 일치하는 결과만 채택
            place_addr = f"{d.get('road_address_name', '')} {d.get('address_name', '')}"
            if not region or region in place_addr:
                return "ok_keyword", float(d["y"]), float(d["x"])
    return "not_found", None, None


# ---------- 사용자 검색어 → 좌표 (단건) ----------

_lookup_limiter: RateLimiter | None = None
_lookup_cache: dict[str, dict | None] = {}
_LOOKUP_CACHE_MAX = 500


async def lookup(query: str) -> dict | None:
    """주소/동네/장소 이름을 좌표로 바꾼다. 주소 검색 → 키워드 검색 순. 결과는 메모리 캐시."""
    global _lookup_limiter
    if not config.KAKAO_REST_API_KEY:
        raise GeocodeError("KAKAO_REST_API_KEY 가 설정되지 않았습니다.")
    q = re.sub(r"\s+", " ", query).strip()
    if q in _lookup_cache:
        return _lookup_cache[q]
    if _lookup_limiter is None:
        _lookup_limiter = RateLimiter(config.GEOCODE_RPS)
    headers = {"Authorization": f"KakaoAK {config.KAKAO_REST_API_KEY}"}
    def addr_item(d):
        return {"lat": float(d["y"]), "lng": float(d["x"]), "label": d.get("address_name") or q, "source": "address"}

    def kw_item(d):
        label = d.get("place_name") or q
        addr = d.get("road_address_name") or d.get("address_name")
        return {"lat": float(d["y"]), "lng": float(d["x"]),
                "label": f"{label} ({addr})" if addr else label, "source": "keyword"}

    async def by_address(client):
        return [addr_item(d) for d in await _call(client, _lookup_limiter, "/v2/local/search/address.json", q)]

    async def by_keyword(client):
        return [kw_item(d) for d in await _call(client, _lookup_limiter, "/v2/local/search/keyword.json", q)]

    # 건물번호(숫자)가 있으면 정확한 주소일 가능성이 높아 주소 검색 먼저.
    # "동성로", "수성못" 같은 동네·장소 이름은 주소 검색이 전국의 같은 도로명 중 아무거나 고르므로
    # 인기 장소 순으로 주는 키워드 검색을 먼저 쓴다.
    order = (by_address, by_keyword) if re.search(r"\d", q) else (by_keyword, by_address)
    def area(item):  # "… (대구 중구 동성로 39)" → "대구 중구"
        return " ".join(re.sub(r"^.*\(", "", item["label"]).split()[:2])

    found: list[dict] = []
    async with httpx.AsyncClient(timeout=8, headers=headers) as client:
        primary = await order[0](client)
        found = list(primary)
        # 결과가 없거나 한 지역에만 몰려 있으면 다른 검색 방식 결과도 후보로 더한다
        # (예: "동성로" 키워드 검색은 부산 결과만 주지만, 주소 검색은 대구·부산·강진의 동성로를 모두 준다)
        if len({area(i) for i in primary}) < 2:
            found += await order[1](client)

    result = None
    if found:
        best, alts, seen = found[0], [], {area(found[0])}
        for item in found[1:]:
            if area(item) not in seen:
                seen.add(area(item))
                alts.append(item)
            if len(alts) >= 4:
                break
        result = {**best, "alternatives": alts}
    if len(_lookup_cache) >= _LOOKUP_CACHE_MAX:
        _lookup_cache.pop(next(iter(_lookup_cache)))
    _lookup_cache[q] = result
    return result


# ---------- 작업 ----------


def _pending(limit: int | None, retry_failed: bool, region: str | None = None) -> list[tuple[str, str]]:
    statuses = "geocode_status IS NULL" + (" OR geocode_status = 'error'" if retry_failed else "")
    sql = f"SELECT addr, MIN(bssh_nm) AS name FROM shops WHERE addr IS NOT NULL AND ({statuses})"
    params: list = []
    if region:
        sql += " AND sido = ?"
        params.append(region)
    sql += " GROUP BY addr ORDER BY MIN(id)"
    if limit:
        sql += f" LIMIT {int(limit)}"
    with db.get_conn() as conn:
        return [(r["addr"], r["name"]) for r in conn.execute(sql, params)]


def _save(results: list[tuple[str, float | None, float | None, str]]) -> int:
    with db.get_conn() as conn:
        with conn:
            cur = conn.executemany(
                "UPDATE shops SET lat = ?, lng = ?, geocode_status = ? WHERE addr = ?",
                [(lat, lng, status, addr) for addr, lat, lng, status in results],
            )
            return cur.rowcount


async def run_geocode(limit: int | None = None, retry_failed: bool = False, region: str | None = None) -> dict:
    if not config.KAKAO_REST_API_KEY:
        raise GeocodeError("KAKAO_REST_API_KEY 가 설정되지 않았습니다. backend/.env 를 확인하세요.")
    if _lock.locked():
        raise GeocodeError("이미 지오코딩이 진행 중입니다.")

    async with _lock:
        _cancel.clear()
        targets = await asyncio.to_thread(_pending, limit, retry_failed, region)
        counts = {"done": 0, "ok": 0, "not_found": 0, "error": 0, "shops_updated": 0}
        db.update_meta(
            "geocode_meta", status="running", started_at=_now(), finished_at=None,
            total=len(targets), message=f"지역 한정: {region}" if region else None, **counts,
        )
        log.info("지오코딩 시작: 대상 주소 %d개%s", len(targets), f" (지역 {region})" if region else "")

        queue: asyncio.Queue = asyncio.Queue()
        for t in targets:
            queue.put_nowait(t)
        buffer: list = []
        buf_lock = asyncio.Lock()
        fatal: list[str] = []
        limiter = RateLimiter(config.GEOCODE_RPS)

        async def flush() -> None:
            async with buf_lock:
                batch, buffer[:] = list(buffer), []
            if batch:
                counts["shops_updated"] += await asyncio.to_thread(_save, batch)
            db.update_meta("geocode_meta", **counts)

        async def worker(client: httpx.AsyncClient) -> None:
            while not queue.empty() and not fatal and not _cancel.is_set():
                addr, name = queue.get_nowait()
                try:
                    status, lat, lng = await geocode_one(client, limiter, addr, name)
                except _AuthError as e:
                    fatal.append(str(e))
                    return
                except GeocodeError as e:
                    log.warning("지오코딩 실패: %s", e)
                    status, lat, lng = "error", None, None
                key = "ok" if status in db.GEO_OK else status
                counts[key] += 1
                counts["done"] += 1
                async with buf_lock:
                    buffer.append((addr, lat, lng, status))
                if counts["done"] % PROGRESS_EVERY == 0:
                    await flush()

        headers = {"Authorization": f"KakaoAK {config.KAKAO_REST_API_KEY}"}
        try:
            async with httpx.AsyncClient(timeout=10, headers=headers) as client:
                await asyncio.gather(*(worker(client) for _ in range(max(1, config.GEOCODE_WORKERS))))
            await flush()
        except Exception as e:
            await flush()
            db.update_meta("geocode_meta", status="error", finished_at=_now(), message=_mask(str(e))[:300])
            raise

        if fatal:
            status, message = "error", fatal[0]
        elif _cancel.is_set():
            status, message = "cancelled", "중지 요청으로 멈췄습니다."
        else:
            status, message = "ok", (f"지역 한정: {region}" if region else None)
        db.update_meta("geocode_meta", status=status, finished_at=_now(), message=message, **counts)
        log.info("지오코딩 종료(%s): %s", status, counts)
        return db.get_meta("geocode_meta")


def cancel() -> None:
    _cancel.set()


def is_running() -> bool:
    return _lock.locked()


def coverage() -> dict:
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT COALESCE(geocode_status, 'pending') AS s, COUNT(*) AS n FROM shops GROUP BY s"
        ).fetchall()
    by = {r["s"]: r["n"] for r in rows}
    total = sum(by.values())
    located = by.get("ok_address", 0) + by.get("ok_keyword", 0)
    return {"shops_total": total, "shops_located": located, "by_status": by}
