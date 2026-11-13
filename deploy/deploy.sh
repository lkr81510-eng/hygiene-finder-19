#!/usr/bin/env bash
# 서버(EC2)에서 실행하는 배포 스크립트. GitHub Actions 가 git pull 직후 호출한다.
#
# 절대 건드리지 않는 파일: backend/.env, backend/*.db (+ -wal/-shm)
#  - 둘 다 .gitignore 대상이라 git pull 로 바뀌지 않고, 이 스크립트도 읽거나 쓰지 않는다.
#  - git clean / reset --hard 같은 미추적 파일 삭제 명령은 쓰지 않는다.
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB_ROOT=/var/www/hygiene-finder
SERVICE=hygiene-api

log() { printf '\n==> %s\n' "$*"; }

cd "$APP_DIR"

# 안전장치: .env 나 DB 가 git 추적 대상이면 pull/배포 과정에서 덮어쓸 수 있으므로 중단
if git ls-files --error-unmatch backend/.env >/dev/null 2>&1 || [ -n "$(git ls-files 'backend/*.db')" ]; then
  echo "중단: backend/.env 또는 DB 파일이 git 에 추적되고 있습니다. .gitignore 를 확인하세요." >&2
  exit 1
fi

log "커밋 $(git log --oneline -1)"

log "백엔드 의존성"
backend/.venv/bin/pip install -q -r backend/requirements.txt

log "프론트 빌드"
cd "$APP_DIR/frontend"
npm ci --no-audit --no-fund --loglevel=error
npm run build
sudo mkdir -p "$WEB_ROOT"
if command -v rsync >/dev/null; then
  sudo rsync -a --delete dist/ "$WEB_ROOT/"
else
  sudo find "$WEB_ROOT" -mindepth 1 -delete
  sudo cp -r dist/. "$WEB_ROOT/"
fi
cd "$APP_DIR"

log "nginx 설정"
if ! sudo cmp -s deploy/nginx.conf /etc/nginx/sites-available/hygiene; then
  sudo cp deploy/nginx.conf /etc/nginx/sites-available/hygiene
  sudo nginx -t
  sudo systemctl reload nginx
  echo "nginx 설정을 갱신했습니다."
else
  echo "변경 없음"
fi

log "$SERVICE 재시작"
sudo systemctl restart "$SERVICE"
for i in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
    echo "API 정상 (${i}초)"
    curl -fsS -o /dev/null -w "nginx 경유 /api/health: %{http_code}\n" http://127.0.0.1/api/health
    exit 0
  fi
  sleep 1
done
echo "API 가 30초 안에 응답하지 않습니다." >&2
sudo journalctl -u "$SERVICE" -n 40 --no-pager >&2
exit 1
