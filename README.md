# 음식점 위생등급 조회

식약처 식품안심업소(위생등급) 지정 현황 기반 · 창업 예정자를 위한 지역별 위생 우수업소 현황

식품의약품안전처 식품안전나라 오픈API **C004 (식품접객업소 식품안심업소(위생등급) 지정 현황)** 데이터를 받아
업소 검색과 통계를 보여주는 웹사이트입니다.

- **업소 검색**: 업소명·지역·업종 검색, 지정 만료 임박(3개월 이내) 필터와 배지
- **통계**: 지역 × 업종 경쟁 현황표(시도 선택 → 업종별·시군구별 업소 수, 전국 비중 비교),
  월별·연도별 지정 추이, 업종별·지정기관별·지역별 분포

```
hygiene-finder-19/
├── backend/      FastAPI + SQLite (데이터 동기화, 검색/통계 API)
├── frontend/     React + Vite (검색 화면, 통계 화면)
└── deploy/       nginx 설정 예시
```

## 요구 사항

- Python 3.11 이상
- Node.js 18 이상
- 식품안전나라 오픈API 인증키 ([foodsafetykorea.go.kr](https://www.foodsafetykorea.go.kr/api/openApiInfo.do?menu_grp=MENU_GRP31&menu_no=661&show_cnt=10&start_idx=1&svc_no=C004)에서 이용 신청)

## 1. 인증키 설정 (`backend/.env`)

인증키는 코드에 넣지 않고 `backend/.env` 파일에서만 읽습니다. 이 파일은 `.gitignore`에 포함되어 있어 커밋되지 않습니다.

```bash
cd backend
cp .env.example .env          # Windows PowerShell: Copy-Item .env.example .env
```

그다음 `backend/.env`를 편집기로 열어 첫 줄에 발급받은 키를 넣습니다.

```
FOODSAFETY_API_KEY=발급받은_인증키
```

| 변수 | 기본값 | 설명 |
|---|---|---|
| `FOODSAFETY_API_KEY` | (필수) | 식품안전나라 인증키 |
| `STARTUP_SYNC` | `true` | DB가 비어 있을 때 서버 시작 시 전체 동기화 여부. `false` 면 항상 건너뜀 |
| `SYNC_TOKEN` | 없음 | 값을 넣으면 `POST /api/sync` 에 `X-Sync-Token` 헤더가 필요 (배포 시 권장) |
| `DB_PATH` | `backend/hygiene.db` | SQLite 파일 경로 |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | 허용 출처 (쉼표 구분) |

## 2. 백엔드 실행

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

처음 시작할 때(DB가 비어 있을 때) 백그라운드에서 전체 데이터를 1000건 단위로 받아 SQLite에 저장합니다.
전체 약 4.7만 건, 10분 정도 걸립니다. 이후 재시작 때는 DB에 데이터가 있으면 동기화를 건너뛰므로,
최신 데이터로 갱신하려면 `POST /api/sync` 를 호출하세요.
진행 상태는 `GET /api/sync` 로 확인할 수 있고, API 문서는 http://localhost:8000/docs 에 있습니다.

## 3. 프론트엔드 실행

```bash
cd frontend
npm install
npm run dev
```

http://localhost:5173 을 엽니다. `/api` 요청은 Vite 프록시가 `http://127.0.0.1:8000` 으로 전달합니다.

## API

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/api/shops?name=&region=&type=&active_only=&expiring=&page=&size=` | 업소 검색. `region` 은 시도(서울, 경기, 전남광주통합특별시 …), `expiring=true` 면 지정종료일 3개월 이내만 (종료일 가까운 순) |
| GET | `/api/stats?active_only=` | 지역별/업종별/지정기관별/연도별/월별 집계, 만료 임박 수, 동기화 상태 |
| GET | `/api/stats/region?region=&active_only=` | 지역 × 업종: 시도 내 업종별 수·비중(전국 비중 포함), 시군구 × 업종 표 |
| POST | `/api/sync` | 수동 전체 동기화 시작 (202 반환 후 백그라운드 실행) |
| GET | `/api/sync` | 동기화 상태 (`status`: never / running / ok / error) |

수동 동기화 예:

```bash
curl -X POST http://localhost:8000/api/sync                         # SYNC_TOKEN 미설정 시
curl -X POST -H "X-Sync-Token: 토큰값" http://localhost:8000/api/sync   # SYNC_TOKEN 설정 시
```

## 데이터 설계

DB 컬럼은 C004 응답 필드명을 소문자로 그대로 사용합니다.

| 응답 필드 | 컬럼 | 의미 |
|---|---|---|
| HG_ASGN_NM | hg_asgn_nm | 지정기관 |
| HG_ASGN_LV | hg_asgn_lv | 지정등급 |
| HG_ASGN_NO | hg_asgn_no | 지정번호 |
| HG_ASGN_YMD | hg_asgn_ymd | 지정일자 |
| INDUTY_NM | induty_nm | 업종 |
| LCNS_NO | lcns_no | 인허가번호 |
| BSSH_NM | bssh_nm | 업소명 |
| PRSDNT_NM | prsdnt_nm | 대표자 |
| ADDR | addr | 주소 |
| ASGN_FROM / ASGN_TO | asgn_from / asgn_to | 지정 시작/종료일자 |
| TELNO | telno | 전화번호 |
| WRKR_REG_NO | wrkr_reg_no | 사업자등록번호 |
| ASGN_CANCEL_YMD | asgn_cancel_ymd | 지정취소일자 |
| CLSBIZ_DVS_CD_NM | clsbiz_dvs_cd_nm | 영업상태 |
| CLSBIZ_DT | clsbiz_dt | 폐업일자 |
| CHNG_DT | chng_dt | 변경일자 |
| INSTT_CD_NM | instt_cd_nm | 인허가관할기관 |

검색·집계용 파생 컬럼:

- `sido`: 주소 첫 단어. 같은 시도의 표기만 약칭으로 통일 (서울특별시 → 서울). 그 밖의 지역명(예: 전남광주통합특별시)은 원본 그대로
- `sigungu`: 주소 두 번째 단어 (세종은 시군구가 없어 비움)
- `grade`: 지정등급에서 공백을 뺀 값 (현재 데이터는 모두 '적합')
- `is_active`: 폐업했거나 지정이 취소되었으면 0, 아니면 1
- `sort_name`: 정렬용 업소명. 앞쪽 기호(`%`, `#`, `(` 등)를 뺀 값

파생 컬럼 계산 방식이 바뀌면 `db.SCHEMA_VERSION` 을 올립니다. 서버 시작 시 저장된 원본 값으로 다시 계산하므로 API를 다시 호출하지 않아도 됩니다.

동기화는 모든 페이지를 받은 뒤 한 트랜잭션으로 테이블을 교체합니다. 중간에 실패하면 기존 데이터가 그대로 남습니다.

> 참고: 2026년 3월 16일부터 위생등급(매우 우수/우수/좋음)이 식품안심업소 '적합'으로 통일되었습니다.
> 실제 데이터도 모든 업소가 '적합'이라, 화면에서는 등급 대신 지정 유효/만료 임박/만료 상태를 보여줍니다.

## 배포 (EC2 + nginx 예시)

1. 프론트 빌드: `cd frontend && npm ci && npm run build` 후 `dist/` 내용을 `/var/www/hygiene-finder` 로 복사
2. 백엔드: 서버에 `backend/.env` 를 직접 만들고(`SYNC_TOKEN` 설정 권장) `uvicorn app.main:app --host 127.0.0.1 --port 8000` 을 systemd 등으로 실행
3. nginx: [deploy/nginx.conf](deploy/nginx.conf) 를 참고해 `/api` 를 8000 포트로 프록시

## 자동 배포 (GitHub Actions)

`main` 브랜치에 push 하면 [.github/workflows/deploy.yml](.github/workflows/deploy.yml) 이 EC2 에 SSH 로 접속해
`git pull --ff-only` 후 [deploy/deploy.sh](deploy/deploy.sh) 를 실행합니다.

1. 백엔드 의존성 설치 (`pip install -r requirements.txt`)
2. 프론트 빌드 (`npm ci && npm run build`) → `/var/www/hygiene-finder` 에 반영
3. `deploy/nginx.conf` 가 바뀌었으면 nginx 설정 갱신 (`nginx -t` 통과 시에만 reload)
4. `hygiene-api` 서비스 재시작 후 `/api/health` 확인

`backend/.env` 와 DB 파일은 git 추적 대상이 아니므로 pull 로 바뀌지 않고, 배포 스크립트도 건드리지 않습니다.
두 파일이 실수로 git 에 추가되면 배포가 중단됩니다.

필요한 Secrets (저장소 Settings → Secrets and variables → Actions):

| 이름 | 값 |
|---|---|
| `EC2_HOST` | EC2 퍼블릭 IP |
| `EC2_USER` | `ubuntu` |
| `EC2_SSH_KEY` | `.pem` 키 파일 전체 내용 (`-----BEGIN` ~ `-----END` 줄 포함) |

Secrets 가 없으면 워크플로는 경고만 남기고 배포를 건너뜁니다. Actions 탭에서 `Run workflow` 로 수동 실행도 됩니다.
> 동기화(`/api/sync`) 진행 중에 배포하면 서비스 재시작으로 동기화가 중단됩니다. 기존 데이터는 유지되며, 동기화를 다시 실행하면 됩니다.
