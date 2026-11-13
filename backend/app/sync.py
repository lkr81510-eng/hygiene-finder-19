"""식품안전나라 C004 전체 데이터를 페이지 단위로 받아 SQLite 에 저장한다."""

import asyncio
import logging
import re
from datetime import datetime, timezone

import httpx

from . import config, db

log = logging.getLogger("hygiene.sync")

_lock = asyncio.Lock()

SIDO_ALIASES = {
    "서울특별시": "서울", "서울시": "서울",
    "부산광역시": "부산", "대구광역시": "대구", "인천광역시": "인천",
    "광주광역시": "광주", "대전광역시": "대전", "울산광역시": "울산",
    "세종특별자치시": "세종", "세종시": "세종",
    "경기도": "경기",
    "강원도": "강원", "강원특별자치도": "강원",
    "충청북도": "충북", "충청남도": "충남",
    "전라북도": "전북", "전북특별자치도": "전북",
    "전라남도": "전남",
    "경상북도": "경북", "경상남도": "경남",
    "제주도": "제주", "제주특별자치도": "제주",
}


class SyncError(Exception):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _mask(text: str) -> str:
    """오류 메시지에 URL 이 섞여도 인증키가 노출되지 않게 가린다."""
    key = config.FOODSAFETY_API_KEY
    return text.replace(key, "***") if key else text


_LEADING_SYMBOLS = re.compile(r"^[^0-9A-Za-z가-힣]+")
# 시군구 없이 바로 읍면동/도로명이 오는 시도
_NO_SIGUNGU = {"세종"}


def normalize(raw: dict) -> dict:
    row = {name.lower(): (str(raw.get(name) or "").strip() or None) for name, _ in db.API_FIELDS}
    return derive(row)


def derive(row: dict) -> dict:
    """원본 컬럼(소문자)으로 파생 컬럼을 채운다."""
    tokens = (row["addr"] or "").split()
    sido = tokens[0] if tokens else None
    # 지역명은 원본을 유지하되, 같은 시도의 표기 차이(서울특별시/서울시)만 약칭으로 통일한다.
    row["sido"] = SIDO_ALIASES.get(sido, sido) if sido else None
    if row["sido"] in _NO_SIGUNGU:
        row["sigungu"] = None
    else:
        row["sigungu"] = tokens[1] if len(tokens) > 1 else None

    name = row["bssh_nm"] or ""
    row["sort_name"] = _LEADING_SYMBOLS.sub("", name) or name

    grade = (row["hg_asgn_lv"] or "").replace(" ", "")
    row["grade"] = grade or "미지정"

    status = row["clsbiz_dvs_cd_nm"] or ""
    closed = "폐업" in status or bool(row["clsbiz_dt"])
    cancelled = bool(row["asgn_cancel_ymd"])
    row["is_active"] = 0 if (closed or cancelled) else 1
    return row


async def _fetch_page(client: httpx.AsyncClient, start: int, end: int) -> tuple[int, list[dict]]:
    url = f"{config.API_BASE_URL}/{config.FOODSAFETY_API_KEY}/{config.SERVICE_ID}/json/{start}/{end}"
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            body = resp.json().get(config.SERVICE_ID)
            if body is None:
                raise SyncError(f"예상치 못한 응답 형식: {resp.text[:200]}")
            result = body.get("RESULT", {})
            code = result.get("CODE", "")
            if code == "INFO-200":  # 해당하는 데이터가 없음
                return int(body.get("total_count") or 0), []
            if code != "INFO-000":
                raise SyncError(f"{code} {result.get('MSG', '')}".strip())
            return int(body.get("total_count") or 0), body.get("row", []) or []
        except SyncError:
            raise
        except Exception as e:  # 네트워크/일시 오류는 재시도
            last_err = e
            await asyncio.sleep(1.5 * (attempt + 1))
    raise SyncError(_mask(f"API 요청 실패 ({start}-{end}): {last_err!r}"))


async def run_sync() -> dict:
    if not config.FOODSAFETY_API_KEY:
        msg = "FOODSAFETY_API_KEY 가 설정되지 않았습니다. backend/.env 를 확인하세요."
        db.update_meta(status="error", finished_at=_now(), message=msg)
        raise SyncError(msg)

    if _lock.locked():
        raise SyncError("이미 동기화가 진행 중입니다.")

    async with _lock:
        db.update_meta(status="running", started_at=_now(), finished_at=None, saved_count=0, message=None)
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                total, first = await _fetch_page(client, 1, config.PAGE_SIZE)
                rows = list(first)
                db.update_meta(total_count=total)
                start = config.PAGE_SIZE + 1
                while start <= total:
                    end = min(start + config.PAGE_SIZE - 1, total)
                    _, page = await _fetch_page(client, start, end)
                    rows.extend(page)
                    log.info("C004 %d-%d / %d", start, end, total)
                    start = end + 1

            normalized = [normalize(r) for r in rows]
            saved = await asyncio.to_thread(db.replace_all_shops, normalized)
            db.update_meta(status="ok", finished_at=_now(), total_count=total, saved_count=saved, message=None)
            log.info("동기화 완료: %d건 저장 (total_count=%d)", saved, total)
            return db.get_meta()
        except Exception as e:
            msg = _mask(str(e))
            db.update_meta(status="error", finished_at=_now(), message=msg)
            log.error("동기화 실패: %s", msg)
            raise SyncError(msg) from None


def is_running() -> bool:
    return _lock.locked()
