import asyncio
import logging
import math
import time
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from . import config, db, geocode, sync

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("hygiene")
# httpx 는 INFO 로그에 요청 URL 전체(= 인증키 포함)를 남기므로 끈다.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

KST = timezone(timedelta(hours=9))
EXPIRY_WINDOW_DAYS = 90  # "만료 임박" 기준: 지정종료일이 오늘부터 3개월 이내

# 통계용 지정기관 그룹: "식품의약품안전처 식품안전정책국 식중독예방과" 같은 하위 부서는 식약처로 합친다.
AGENCY_GROUP_SQL = (
    "CASE WHEN hg_asgn_nm LIKE '식품의약품안전처%' THEN '식품의약품안전처' ELSE hg_asgn_nm END"
)

_tasks: set[asyncio.Task] = set()  # 백그라운드 작업 참조 유지


def _today() -> datetime:
    return datetime.now(KST)


def _expiry_range() -> tuple[str, str]:
    today = _today()
    return today.strftime("%Y%m%d"), (today + timedelta(days=EXPIRY_WINDOW_DAYS)).strftime("%Y%m%d")


async def _background_sync() -> None:
    try:
        await sync.run_sync()
    except sync.SyncError as e:
        log.warning("동기화 건너뜀/실패: %s", e)


async def _background_geocode(limit: int | None, retry_failed: bool, region: str | None = None) -> None:
    try:
        await geocode.run_geocode(limit=limit, retry_failed=retry_failed, region=region)
    except Exception as e:
        log.warning("지오코딩 실패: %s", e)


def _spawn(coro) -> None:
    task = asyncio.create_task(coro)
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


def _start_sync_task() -> None:
    _spawn(_background_sync())


def _require_token(token: str | None) -> None:
    if config.SYNC_TOKEN and token != config.SYNC_TOKEN:
        raise HTTPException(status_code=401, detail="유효한 X-Sync-Token 헤더가 필요합니다.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await asyncio.to_thread(db.init_db)
    if db.get_meta().get("status") == "running":
        # 이전 프로세스가 동기화 도중 종료된 경우 상태를 정리
        db.update_meta(status="error", message="이전 동기화가 중단되었습니다.")
    if db.get_meta("geocode_meta").get("status") == "running":
        # 지오코딩은 재시작 시 자동으로 이어서 하지 않는다 (POST /api/geocode 로 수동 시작)
        db.update_meta("geocode_meta", status="interrupted", message="서버 재시작으로 중단되었습니다. 다시 시작하면 남은 주소부터 이어집니다.")
    if not config.STARTUP_SYNC:
        log.info("STARTUP_SYNC=false: 시작 시 동기화를 건너뜁니다.")
    elif (count := db.shop_count()) > 0:
        log.info("DB에 %d건이 있어 시작 시 동기화를 건너뜁니다. 갱신하려면 POST /api/sync", count)
    else:
        _start_sync_task()
    yield
    for task in list(_tasks):
        task.cancel()


app = FastAPI(title="음식점 위생등급 조회 API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _where(*, name=None, region=None, type_=None, active_only=False, expiring=False) -> tuple[str, list]:
    where, params = [], []
    if name:
        where.append("bssh_nm LIKE ?")
        params.append(f"%{name.strip()}%")
    if region:
        where.append("sido = ?")
        params.append(region)
    if type_:
        where.append("induty_nm = ?")
        params.append(type_)
    if active_only:
        where.append("is_active = 1")
    if expiring:
        start, end = _expiry_range()
        where.append("asgn_to BETWEEN ? AND ?")
        params += [start, end]
    return (" WHERE " + " AND ".join(where)) if where else "", params


def _group(conn, col: str, where: str, params: list, order: str = "count DESC, key") -> list[dict]:
    rows = conn.execute(
        f"SELECT COALESCE({col}, '미상') AS key, COUNT(*) AS count FROM shops{where} GROUP BY key ORDER BY {order}",
        params,
    ).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/shops")
def list_shops(
    name: str | None = None,
    region: str | None = None,
    type: str | None = None,
    active_only: bool = False,
    expiring: bool = False,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    where, params = _where(name=name, region=region, type_=type, active_only=active_only, expiring=expiring)
    order = "asgn_to, sort_name" if expiring else "sort_name, bssh_nm"
    with db.get_conn() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM shops{where}", params).fetchone()[0]
        rows = conn.execute(
            f"""SELECT id, bssh_nm, induty_nm, addr, telno, sido, sigungu, hg_asgn_lv,
                       hg_asgn_ymd, asgn_from, asgn_to, hg_asgn_nm, clsbiz_dvs_cd_nm, is_active
                FROM shops{where}
                ORDER BY {order}
                LIMIT ? OFFSET ?""",
            [*params, size, (page - 1) * size],
        ).fetchall()
    return {
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size,
        "today": _today().strftime("%Y%m%d"),
        "expiry_window_days": EXPIRY_WINDOW_DAYS,
        "items": [dict(r) for r in rows],
    }


@app.get("/api/stats")
def stats(active_only: bool = False):
    where, params = _where(active_only=active_only)
    exp_where, exp_params = _where(active_only=active_only, expiring=True)
    with db.get_conn() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM shops{where}", params).fetchone()[0]
        active = conn.execute("SELECT COUNT(*) FROM shops WHERE is_active = 1").fetchone()[0]
        expiring = conn.execute(f"SELECT COUNT(*) FROM shops{exp_where}", exp_params).fetchone()[0]
        by_region = _group(conn, "sido", where, params)
        by_type = _group(conn, "induty_nm", where, params)
        by_agency = _group(conn, AGENCY_GROUP_SQL, where, params)
        by_year = _group(conn, "substr(hg_asgn_ymd, 1, 4)", where, params, "key")
        by_month = _group(conn, "substr(hg_asgn_ymd, 1, 6)", where, params, "key")
    return {
        "total": total,
        "active": active,
        "expiring": expiring,
        "expiry_window_days": EXPIRY_WINDOW_DAYS,
        "by_region": by_region,
        "by_type": by_type,
        "by_agency": by_agency,
        "by_year": by_year,
        "by_month": by_month,
        "sync": db.get_meta(),
    }


@app.get("/api/stats/region")
def region_breakdown(region: str = Query(..., min_length=1), active_only: bool = False):
    """시도 하나를 골랐을 때의 지역 × 업종 표 (창업 예정자의 경쟁 업소 현황용)."""
    where, params = _where(region=region, active_only=active_only)
    nat_where, nat_params = _where(active_only=active_only)
    with db.get_conn() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM shops{where}", params).fetchone()[0]
        if total == 0:
            raise HTTPException(status_code=404, detail=f"'{region}' 지역 데이터가 없습니다.")
        by_type = _group(conn, "induty_nm", where, params)
        national = {r["key"]: r["count"] for r in _group(conn, "induty_nm", nat_where, nat_params)}
        cells = conn.execute(
            f"""SELECT COALESCE(sigungu, ?) AS sigungu, COALESCE(induty_nm, '미상') AS type,
                       COUNT(*) AS count
                FROM shops{where} GROUP BY 1, 2""",
            [f"{region} 전체", *params],
        ).fetchall()

    types = [r["key"] for r in by_type]
    table: dict[str, dict] = {}
    for c in cells:
        row = table.setdefault(c["sigungu"], {"key": c["sigungu"], "total": 0, "types": {}})
        row["types"][c["type"]] = c["count"]
        row["total"] += c["count"]
    nat_total = sum(national.values()) or 1
    return {
        "region": region,
        "total": total,
        "types": types,
        "by_type": [
            {
                **r,
                "share": r["count"] / total,  # 지역 내 비중
                "national_share": national.get(r["key"], 0) / nat_total,  # 전국 비중 (비교용)
            }
            for r in by_type
        ],
        "sigungu": sorted(table.values(), key=lambda r: (-r["total"], r["key"])),
    }


@app.get("/api/sync")
def sync_status():
    return {**db.get_meta(), "running": sync.is_running()}


@app.post("/api/sync", status_code=202)
async def trigger_sync(x_sync_token: str | None = Header(default=None)):
    _require_token(x_sync_token)
    if not config.FOODSAFETY_API_KEY:
        raise HTTPException(status_code=400, detail="FOODSAFETY_API_KEY 가 설정되지 않았습니다.")
    if sync.is_running():
        raise HTTPException(status_code=409, detail="이미 동기화가 진행 중입니다.")
    if geocode.is_running():
        raise HTTPException(status_code=409, detail="지오코딩이 진행 중입니다. 끝난 뒤 동기화하세요.")
    _start_sync_task()
    return {"started": True, "status_url": "/api/sync"}


# ---------- 지오코딩 (주소 → 좌표) ----------


@app.get("/api/geocode")
def geocode_status():
    meta = db.get_meta("geocode_meta")
    total, done = meta.get("total") or 0, meta.get("done") or 0
    return {
        **meta,
        "running": geocode.is_running(),
        "progress": round(done / total, 4) if total else None,
        "coverage": geocode.coverage(),
    }


@app.post("/api/geocode", status_code=202)
async def start_geocode(
    limit: int | None = Query(None, ge=1, description="이번에 변환할 최대 주소 수 (없으면 남은 전체)"),
    retry_failed: bool = Query(False, description="true 면 'error' 로 기록된 주소도 다시 시도"),
    region: str | None = Query(None, description="시도 한정 (예: 대구, 서울, 전남광주통합특별시)"),
    x_sync_token: str | None = Header(default=None),
):
    _require_token(x_sync_token)
    if not config.KAKAO_REST_API_KEY:
        raise HTTPException(status_code=400, detail="KAKAO_REST_API_KEY 가 설정되지 않았습니다.")
    if geocode.is_running():
        raise HTTPException(status_code=409, detail="이미 지오코딩이 진행 중입니다.")
    if sync.is_running():
        raise HTTPException(status_code=409, detail="동기화가 진행 중입니다. 끝난 뒤 지오코딩하세요.")
    if region:
        with db.get_conn() as conn:
            if not conn.execute("SELECT 1 FROM shops WHERE sido = ? LIMIT 1", [region]).fetchone():
                raise HTTPException(status_code=404, detail=f"'{region}' 지역 업소가 없습니다.")
    _spawn(_background_geocode(limit, retry_failed, region))
    return {"started": True, "limit": limit, "retry_failed": retry_failed, "region": region, "status_url": "/api/geocode"}


@app.post("/api/geocode/cancel")
def cancel_geocode(x_sync_token: str | None = Header(default=None)):
    _require_token(x_sync_token)
    if not geocode.is_running():
        raise HTTPException(status_code=409, detail="진행 중인 지오코딩이 없습니다.")
    geocode.cancel()
    return {"cancelling": True}


# ---------- 사용자 검색어 → 좌표 ----------

LOOKUP_PER_MINUTE = 20  # IP 하나당 1분에 허용하는 주소 검색 수 (카카오 키 남용 방지)
_lookup_hits: dict[str, deque] = {}


def _client_ip(request: Request) -> str:
    host = request.client.host if request.client else "unknown"
    # nginx(같은 서버)를 거친 요청만 X-Real-IP 를 믿는다
    if host in ("127.0.0.1", "::1"):
        return request.headers.get("x-real-ip", host)
    return host


def _check_lookup_rate(ip: str) -> None:
    now = time.monotonic()
    hits = _lookup_hits.setdefault(ip, deque())
    while hits and now - hits[0] > 60:
        hits.popleft()
    if len(hits) >= LOOKUP_PER_MINUTE:
        retry = int(60 - (now - hits[0])) + 1
        raise HTTPException(
            status_code=429,
            detail=f"주소 검색이 너무 잦습니다. {retry}초 뒤 다시 시도하세요.",
            headers={"Retry-After": str(retry)},
        )
    hits.append(now)
    if len(_lookup_hits) > 5000:  # 오래된 IP 기록 정리
        for k in [k for k, v in _lookup_hits.items() if not v or now - v[-1] > 60]:
            _lookup_hits.pop(k, None)


@app.get("/api/geocode-address")
async def geocode_address(request: Request, q: str = Query(..., min_length=2, max_length=100)):
    """주소·동네·장소 이름을 좌표로 바꾼다. 카카오 키는 서버에서만 쓴다."""
    if not config.KAKAO_REST_API_KEY:
        raise HTTPException(status_code=503, detail="주소 검색이 설정되지 않았습니다.")
    _check_lookup_rate(_client_ip(request))
    try:
        result = await geocode.lookup(q)
    except geocode.GeocodeError as e:
        log.warning("주소 검색 실패: %s", e)
        raise HTTPException(status_code=502, detail="주소 검색 서비스에 일시적인 문제가 있습니다.")
    if not result:
        raise HTTPException(status_code=404, detail=f"'{q}' 위치를 찾지 못했습니다.")
    return result


# ---------- 내 주변 업소 ----------

EARTH_RADIUS_M = 6_371_008.8


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


@app.get("/api/nearby")
def nearby(
    lat: float = Query(..., ge=33.0, le=39.0, description="위도 (대한민국 범위)"),
    lng: float = Query(..., ge=124.0, le=132.0, description="경도 (대한민국 범위)"),
    radius: int = Query(1000, ge=50, le=5000, description="반경(m)"),
    type: str | None = None,
    expiring: bool = False,
    active_only: bool = True,
    limit: int = Query(100, ge=1, le=300),
):
    # 1) 위경도 범위(사각형)로 인덱스를 타서 후보를 좁히고  2) 정확한 거리(하버사인)로 원 안만 남긴다
    dlat = math.degrees(radius / EARTH_RADIUS_M)
    dlng = math.degrees(radius / (EARTH_RADIUS_M * math.cos(math.radians(lat))))
    # 업종 요약은 업종·만료 필터와 무관하게 반경 안 전체로 내므로, SQL 에서는 active_only 만 건다
    where, params = _where(active_only=active_only)
    box = "lat BETWEEN ? AND ? AND lng BETWEEN ? AND ?"
    where = f"{where} AND {box}" if where else f" WHERE {box}"
    params += [lat - dlat, lat + dlat, lng - dlng, lng + dlng]
    with db.get_conn() as conn:
        rows = conn.execute(
            f"""SELECT id, bssh_nm, induty_nm, addr, telno, sido, sigungu, hg_asgn_nm,
                       asgn_from, asgn_to, clsbiz_dvs_cd_nm, is_active, lat, lng
                FROM shops{where}""",
            params,
        ).fetchall()

    exp_start, exp_end = _expiry_range()
    in_radius, items = [], []
    for r in rows:
        d = _haversine_m(lat, lng, r["lat"], r["lng"])
        if d > radius:
            continue
        row = {**dict(r), "distance_m": round(d)}
        in_radius.append(row)
        if type and row["induty_nm"] != type:
            continue
        if expiring and not (row["asgn_to"] and exp_start <= row["asgn_to"] <= exp_end):
            continue
        items.append(row)
    items.sort(key=lambda x: (x["distance_m"], x["bssh_nm"] or ""))

    # 창업 관점 요약: 반경 안 업종별 업소 수 (업종·만료 필터 적용 전)
    by_type: dict[str, int] = {}
    for r in in_radius:
        by_type[r["induty_nm"] or "미상"] = by_type.get(r["induty_nm"] or "미상", 0) + 1
    expiring_in_radius = sum(1 for r in in_radius if r["asgn_to"] and exp_start <= r["asgn_to"] <= exp_end)

    cov = geocode.coverage()
    return {
        "center": {"lat": lat, "lng": lng},
        "radius": radius,
        "total": len(items),
        "summary": {
            "total": len(in_radius),
            "expiring": expiring_in_radius,
            "by_type": [{"key": k, "count": v} for k, v in sorted(by_type.items(), key=lambda kv: (-kv[1], kv[0]))],
        },
        "candidates_in_box": len(rows),
        "today": _today().strftime("%Y%m%d"),
        "expiry_window_days": EXPIRY_WINDOW_DAYS,
        "geocoded_ratio": round(cov["shops_located"] / cov["shops_total"], 4) if cov["shops_total"] else 0,
        "items": items[:limit],
    }
