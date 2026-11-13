"""SQLite 스키마와 접근 헬퍼.

컬럼은 C004 응답 필드명(식품안전나라 명세 기준)을 소문자로 그대로 쓰고,
검색/집계용 파생 컬럼(sido, sigungu, grade, is_active)을 추가했다.
"""

import sqlite3
from contextlib import contextmanager

from .config import DB_PATH

# (C004 응답 필드, 설명) — 순서는 명세 순서
API_FIELDS = [
    ("HG_ASGN_NM", "지정기관"),
    ("HG_ASGN_LV", "지정등급"),
    ("HG_ASGN_NO", "지정번호"),
    ("HG_ASGN_YMD", "지정일자"),
    ("INDUTY_NM", "업종"),
    ("LCNS_NO", "인허가번호"),
    ("BSSH_NM", "업소명"),
    ("PRSDNT_NM", "대표자"),
    ("ADDR", "주소"),
    ("ASGN_FROM", "지정시작일자"),
    ("ASGN_TO", "지정종료일자"),
    ("TELNO", "업소전화번호"),
    ("WRKR_REG_NO", "사업자등록번호"),
    ("ASGN_CANCEL_YMD", "지정취소일자"),
    ("CLSBIZ_DVS_CD_NM", "영업상태"),
    ("CLSBIZ_DT", "폐업일자"),
    ("CHNG_DT", "변경일자"),
    ("INSTT_CD_NM", "인허가관할기관"),
]

DERIVED_FIELDS = ["sido", "sigungu", "grade", "is_active", "sort_name"]

# 파생 컬럼 계산 방식이 바뀌면 올린다. 시작 시 기존 행의 파생 컬럼을 원본 값으로 다시 계산한다.
SCHEMA_VERSION = 2

# 지오코딩 결과 컬럼 (카카오 로컬 API). geocode_status:
#   NULL=미변환, ok_address=주소검색 성공, ok_keyword=키워드검색 성공, not_found=결과 없음, error=호출 실패
GEO_FIELDS = ["lat", "lng", "geocode_status"]
GEO_OK = ("ok_address", "ok_keyword")

COLUMNS = [name.lower() for name, _ in API_FIELDS] + DERIVED_FIELDS + GEO_FIELDS

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS shops (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    {", ".join(f"{name.lower()} TEXT" for name, _ in API_FIELDS)},
    sido TEXT,              -- 시도 (주소 첫 토큰, 약칭으로 정규화)
    sigungu TEXT,           -- 시군구 (주소 두 번째 토큰)
    grade TEXT,             -- 지정등급 공백 제거 (매우우수/우수/좋음/적합 ...)
    is_active INTEGER,      -- 1: 영업 중이고 지정 취소되지 않음
    sort_name TEXT,         -- 정렬용 업소명 (앞쪽 기호 제거)
    lat REAL,               -- 위도 (지오코딩)
    lng REAL,               -- 경도 (지오코딩)
    geocode_status TEXT     -- 지오코딩 상태 (GEO_FIELDS 설명 참고)
);
CREATE INDEX IF NOT EXISTS idx_shops_name ON shops(bssh_nm);
CREATE INDEX IF NOT EXISTS idx_shops_sido ON shops(sido);
CREATE INDEX IF NOT EXISTS idx_shops_grade ON shops(grade);
CREATE INDEX IF NOT EXISTS idx_shops_type ON shops(induty_nm);
CREATE INDEX IF NOT EXISTS idx_shops_active ON shops(is_active);

CREATE TABLE IF NOT EXISTS sync_meta (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    status TEXT,
    started_at TEXT,
    finished_at TEXT,
    total_count INTEGER,
    saved_count INTEGER,
    message TEXT
);
INSERT OR IGNORE INTO sync_meta (id, status) VALUES (1, 'never');

CREATE TABLE IF NOT EXISTS geocode_meta (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    status TEXT,
    started_at TEXT,
    finished_at TEXT,
    total INTEGER,          -- 이번 작업 대상 주소 수
    done INTEGER,
    ok INTEGER,
    not_found INTEGER,
    error INTEGER,
    shops_updated INTEGER,  -- 좌표가 저장된 업소 수 (같은 주소의 업소 포함)
    message TEXT
);
INSERT OR IGNORE INTO geocode_meta (id, status) VALUES (1, 'never');
"""


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


@contextmanager
def get_conn():
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(shops)")}
        # 마이그레이션: 기존 데이터는 그대로 두고 빠진 컬럼만 추가
        for col, typ in [("sort_name", "TEXT"), ("lat", "REAL"), ("lng", "REAL"), ("geocode_status", "TEXT")]:
            if col not in cols:
                conn.execute(f"ALTER TABLE shops ADD COLUMN {col} {typ}")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_shops_latlng ON shops(lat, lng)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_shops_geocode ON shops(geocode_status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_shops_sort ON shops(sort_name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_shops_asgn_to ON shops(asgn_to)")
        conn.commit()
        version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version < SCHEMA_VERSION:
        _rebuild_derived()
        with get_conn() as conn:
            conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            conn.commit()


def _rebuild_derived() -> None:
    """저장된 원본 컬럼으로 파생 컬럼을 다시 계산한다 (API 재호출 없이 마이그레이션)."""
    from .sync import derive  # 순환 import 방지

    api_cols = [name.lower() for name, _ in API_FIELDS]
    with get_conn() as conn:
        rows = conn.execute(f"SELECT id, {', '.join(api_cols)} FROM shops").fetchall()
        if not rows:
            return
        sets = ", ".join(f"{c} = ?" for c in DERIVED_FIELDS)
        with conn:
            conn.executemany(
                f"UPDATE shops SET {sets} WHERE id = ?",
                [[derive(dict(r))[c] for c in DERIVED_FIELDS] + [r["id"]] for r in rows],
            )


def shop_count() -> int:
    with get_conn() as conn:
        return conn.execute("SELECT COUNT(*) FROM shops").fetchone()[0]


def update_meta(table: str = "sync_meta", **fields) -> None:
    if not fields:
        return
    assert table in ("sync_meta", "geocode_meta")
    sets = ", ".join(f"{k} = ?" for k in fields)
    with get_conn() as conn:
        conn.execute(f"UPDATE {table} SET {sets} WHERE id = 1", list(fields.values()))
        conn.commit()


def get_meta(table: str = "sync_meta") -> dict:
    assert table in ("sync_meta", "geocode_meta")
    with get_conn() as conn:
        row = conn.execute(f"SELECT * FROM {table} WHERE id = 1").fetchone()
        return dict(row) if row else {}


def replace_all_shops(rows: list[dict]) -> int:
    """전체 데이터를 한 트랜잭션으로 교체한다. 실패하면 기존 데이터가 그대로 남는다.

    지오코딩 결과는 주소가 같으면 그대로 이어받는다. 그래서 동기화 뒤에는 새 주소(새 업소·주소 변경)만
    geocode_status 가 NULL 이 되어 다음 지오코딩 대상이 된다. 'error' 는 다시 시도하도록 이어받지 않는다.
    """
    placeholders = ", ".join("?" for _ in COLUMNS)
    sql = f"INSERT INTO shops ({', '.join(COLUMNS)}) VALUES ({placeholders})"
    with get_conn() as conn:
        with conn:
            known = {
                r["addr"]: (r["lat"], r["lng"], r["geocode_status"])
                for r in conn.execute(
                    "SELECT addr, lat, lng, geocode_status FROM shops "
                    "WHERE addr IS NOT NULL AND geocode_status IN ('ok_address', 'ok_keyword', 'not_found')"
                )
            }
            for r in rows:
                if r.get("addr") in known:
                    r["lat"], r["lng"], r["geocode_status"] = known[r["addr"]]
            conn.execute("DELETE FROM shops")
            conn.executemany(sql, [[r.get(c) for c in COLUMNS] for r in rows])
    return len(rows)
