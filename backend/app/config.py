import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


# 인증키는 .env 의 FOODSAFETY_API_KEY 에서만 읽는다.
FOODSAFETY_API_KEY = os.getenv("FOODSAFETY_API_KEY", "").strip()

API_BASE_URL = os.getenv("FOODSAFETY_API_BASE", "http://openapi.foodsafetykorea.go.kr/api").rstrip("/")
SERVICE_ID = "C004"
# 식품안전나라 오픈API 는 1회 요청당 최대 1000건까지 반환한다.
PAGE_SIZE = int(os.getenv("SYNC_PAGE_SIZE", "1000"))

DB_PATH = Path(os.getenv("DB_PATH", str(BASE_DIR / "hygiene.db")))

# 서버 시작 시 동기화 여부 (개발 중 --reload 로 API 호출이 반복되는 것을 막고 싶을 때 false)
STARTUP_SYNC = _bool("STARTUP_SYNC", True)

# 값이 있으면 POST /api/sync 호출 시 X-Sync-Token 헤더가 일치해야 한다 (배포용)
SYNC_TOKEN = os.getenv("SYNC_TOKEN", "").strip()

CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if o.strip()
]
