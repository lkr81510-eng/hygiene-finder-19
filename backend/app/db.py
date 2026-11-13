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

COLUMNS = [name.lower() for name, _ in API_FIELDS] + DERIVED_FIELDS

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS shops (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    {", ".join(f"{name.lower()} TEXT" for name, _ in API_FIELDS)},
    sido TEXT,              -- 시도 (주소 첫 토큰, 약칭으로 정규화)
    sigungu TEXT,           -- 시군구 (주소 두 번째 토큰)
    grade TEXT,             -- 지정등급 공백 제거 (매우우수/우수/좋음/적합 ...)
    is_active INTEGER,      -- 1: 영업 중이고 지정 취소되지 않음
    sort_name TEXT          -- 정렬용 업소명 (앞쪽 기호 제거)
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
        if "sort_name" not in cols:
            conn.execute("ALTER TABLE shops ADD COLUMN sort_name TEXT")
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


def update_meta(**fields) -> None:
    if not fields:
        return
    sets = ", ".join(f"{k} = ?" for k in fields)
    with get_conn() as conn:
        conn.execute(f"UPDATE sync_meta SET {sets} WHERE id = 1", list(fields.values()))
        conn.commit()


def get_meta() -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM sync_meta WHERE id = 1").fetchone()
        return dict(row) if row else {}


def replace_all_shops(rows: list[dict]) -> int:
    """전체 데이터를 한 트랜잭션으로 교체한다. 실패하면 기존 데이터가 그대로 남는다."""
    placeholders = ", ".join("?" for _ in COLUMNS)
    sql = f"INSERT INTO shops ({', '.join(COLUMNS)}) VALUES ({placeholders})"
    with get_conn() as conn:
        with conn:
            conn.execute("DELETE FROM shops")
            conn.executemany(sql, [[r.get(c) for c in COLUMNS] for r in rows])
    return len(rows)
