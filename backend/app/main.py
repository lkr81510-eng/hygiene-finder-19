import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import config, db, sync

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("hygiene")
# httpx 는 INFO 로그에 요청 URL 전체(= 인증키 포함)를 남기므로 끈다.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

KST = timezone(timedelta(hours=9))
EXPIRY_WINDOW_DAYS = 90  # "만료 임박" 기준: 지정종료일이 오늘부터 3개월 이내

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


def _start_sync_task() -> None:
    task = asyncio.create_task(_background_sync())
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await asyncio.to_thread(db.init_db)
    if db.get_meta().get("status") == "running":
        # 이전 프로세스가 동기화 도중 종료된 경우 상태를 정리
        db.update_meta(status="error", message="이전 동기화가 중단되었습니다.")
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
        by_agency = _group(conn, "hg_asgn_nm", where, params)
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
    if config.SYNC_TOKEN and x_sync_token != config.SYNC_TOKEN:
        raise HTTPException(status_code=401, detail="유효한 X-Sync-Token 헤더가 필요합니다.")
    if not config.FOODSAFETY_API_KEY:
        raise HTTPException(status_code=400, detail="FOODSAFETY_API_KEY 가 설정되지 않았습니다.")
    if sync.is_running():
        raise HTTPException(status_code=409, detail="이미 동기화가 진행 중입니다.")
    _start_sync_task()
    return {"started": True, "status_url": "/api/sync"}
