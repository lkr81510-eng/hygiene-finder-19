# 음식점 위생등급 조회

식약처 식품안심업소(위생등급) 지정 현황 기반 · 창업 예정자를 위한 지역별 위생 우수업소 현황

**접속 주소: https://15-165-113-119.sslip.io**

식품의약품안전처 식품안전나라 오픈API **C004 (식품접객업소 식품안심업소(위생등급) 지정 현황)** 데이터로
식품안심업소를 검색하고, 지도에서 내 주변 업소를 찾고, 지역·업종별 현황을 비교하는 웹사이트입니다.

- [주요 기능](#주요-기능) · [화면 사용법](#화면-사용법) · [창업 예정자 활용 예시](#창업-예정자-활용-예시) · [데이터 출처와 한계](#데이터-출처와-한계)
- [로컬 실행](#로컬-실행) · [지오코딩](#지오코딩-주소--좌표) · [API](#api) · [데이터 설계](#데이터-설계) · [배포·운영](#배포운영)

## 주요 기능

| 화면 | 기능 |
|---|---|
| **업소 검색** (`/`) | 업소명·지역·업종 검색, 지정 상태 배지(지정 유효 / 만료 D-n / 지정 만료), 만료 3개월 이내 필터 |
| **내 주변** (`/nearby`) | 지도 클릭·주소 검색·내 위치로 기준점을 정하면 반경(500m/1km/3km) 안 업소를 거리순으로 표시, 업종별 요약 카드 |
| **통계** (`/stats`) | 지역 × 업종 경쟁 현황표(시군구별), 월별·연도별 지정 추이, 업종·지정기관·지역별 분포 |

2026-11-13 기준 데이터: 식품안심업소 47,108곳(영업 중 45,520곳), 이 중 99.93%(47,074곳)가 지도 좌표를 가지고 있습니다.

## 화면 사용법

### 업소 검색

1. 검색창에 업소명 일부를 입력하고 **검색** (예: `김밥`, `파리바게뜨`).
2. 지역·업종 드롭다운으로 좁힙니다. **영업 중인 업소만**은 기본으로 켜져 있습니다.
3. **만료 3개월 이내**를 켜면 지정종료일이 가까운 순으로 정렬됩니다.
4. 카드 오른쪽 위 배지로 지정 상태를 봅니다.
   - ✓ **지정 유효** / ! **만료 D-n** (3개월 이내) / ✕ **지정 만료**
5. 검색 조건은 주소창(URL)에 남으므로 링크를 그대로 공유할 수 있습니다.

### 내 주변

1. 기준 위치를 정합니다. 세 가지 방법이 있습니다.
   - **지도 클릭**: 클릭한 지점이 기준점이 됩니다.
   - **주소·동네 검색**: `대구 중구 국채보상로 600`, `수성못`, `강남역` 처럼 입력하고 **찾기**.
     같은 이름이 여러 지역에 있으면(예: `동성로`) 검색창 아래에 **다른 후보** 버튼이 나옵니다.
     지역명을 함께 쓰면 더 정확합니다(`대구 동성로`).
   - **내 위치**: 브라우저 위치 권한을 허용하면 현재 위치를 씁니다. 거부하면 지도 클릭이나 주소 입력을 안내합니다.
2. **반경**(500m / 1km / 3km), **업종**, **만료 3개월 이내** 필터를 고릅니다.
3. 지도 위 **요약 카드**에서 반경 안 전체 업소 수, 만료 임박 수, 업종별 업소 수와 비중을 봅니다.
   업종 카드를 누르면 그 업종만 보이고, 다시 누르면 해제됩니다.
4. 오른쪽(모바일은 아래) **목록**은 가까운 순입니다. 목록을 누르면 지도에서 해당 마커가 주황색으로 커지고,
   마커를 누르면 목록에서 해당 업소가 강조됩니다.
5. 지도 조작
   - 결과가 바뀌면 반경 원과 모든 마커가 보이도록 범위가 자동으로 맞춰집니다.
   - **Ctrl(⌘) + 마우스 휠**로 확대·축소합니다. 그냥 휠은 페이지 스크롤입니다. 모바일은 두 손가락으로 확대·축소합니다.
   - 확대·축소 후 원래대로 보려면 왼쪽 위 **⤢ (반경 전체 보기)** 버튼을 누릅니다.
6. 기준점·반경·필터는 URL에 남습니다(`/nearby?lat=…&lng=…&r=1000`).

> 반경 결과는 가까운 300곳까지만 목록·지도에 표시합니다. 그보다 많으면 반경을 줄이거나 업종을 고르세요.
> 요약 카드의 업종별 수는 이 제한과 업종·만료 필터에 상관없이 반경 안 전체 기준입니다.

### 통계

1. **영업 중인 업소만**을 켜고 끄며 기준을 바꿉니다.
2. **지역 × 업종 경쟁 현황**: 시도를 고르면
   - 업종별 업소 수, 그 지역 안의 비중, 전국 비중과의 차이(▲▼ %p)
   - 시군구 × 업종 표 (칸 색이 진할수록 많음, 열 제목을 누르면 정렬)
   - 업종 카드를 누르면 해당 지역·업종의 업소 목록으로 이동합니다.
   - 아래 **지역별** 막대를 눌러도 표의 지역이 바뀝니다.
3. **연도별 지정 추이**: 연도 합계와 월별 신규 지정 건수 (이번 달은 집계 중이라 옅게 표시).
4. **업종별 / 지정기관별 / 지역별** 막대, **표로 보기**로 숫자 표를 펼칠 수 있습니다.

## 창업 예정자 활용 예시

> 아래 숫자는 2026-11-13 데이터 기준 예시입니다.

**1. 후보 입지 두 곳의 경쟁 업소 비교**
`내 주변`에서 후보 주소를 차례로 입력하고 반경 500m·1km 요약 카드를 비교합니다.
예를 들어 대구 동성로(CGV 대구한일 부근) 반경 1km에는 식품안심업소 237곳이 있고,
휴게음식점 116곳(49%), 일반음식점 100곳(42%), 제과점 20곳(8%)입니다.
카페(휴게음식점)를 준비한다면 같은 업종 카드를 눌러 지도에서 경쟁 업소가 어디에 몰려 있는지 확인할 수 있습니다.

**2. 시군구 단위로 업종 밀집도 보기**
`통계 → 지역 × 업종 경쟁 현황`에서 시도를 고르면 시군구별 업종 분포가 나옵니다.
예: 서울에서는 강남구가 1,163곳으로 가장 많고 그중 일반음식점이 647곳입니다.
전국 비중과 비교한 ▲▼ 표시로 "이 지역은 전국보다 제과점 비중이 높다/낮다"를 바로 볼 수 있습니다.

**3. 위생 관리 수준의 기준 잡기**
반경 안에서 식품안심업소로 지정된 경쟁 업소가 많다면, 그 상권에서는 위생 지정이 사실상 기본 조건일 수 있습니다.
`업소 검색`에서 같은 업종·지역의 지정 업소를 찾아 지정기관과 지정 기간을 참고하세요.
`통계`의 월별 지정 추이로 지정 건수가 늘고 있는지도 확인할 수 있습니다.

**4. 만료 임박 업소로 상권 변화 살피기**
`만료 3개월 이내` 필터로 지정 기간이 곧 끝나는 업소를 봅니다(전국 2,646곳).
재지정 여부는 업소마다 다르므로, 일정 기간 뒤 다시 조회해 상권 안 업소 구성이 어떻게 바뀌는지 추적하는 용도로 씁니다.

**5. 프랜차이즈 분포 확인**
`업소 검색`에서 브랜드명(예: `파리바게뜨`, `스타벅스`)을 검색하고 지역 필터를 바꿔 보면,
위생 지정을 받은 같은 브랜드 매장이 어느 지역에 많은지 볼 수 있습니다.

## 데이터 출처와 한계

- 출처: 식품의약품안전처 식품안전나라 오픈API C004. 위치 검색과 좌표 변환은 카카오 로컬 API, 지도는 OpenStreetMap 입니다.
- **식품안심업소로 지정된 업소만** 들어 있습니다. 상권의 모든 음식점이 아니므로, 경쟁 강도를 볼 때는
  "위생 지정을 받은 업소 기준"이라는 점을 감안하세요.
- 2026년 3월 16일부터 위생등급(매우 우수/우수/좋음)이 식품안심업소 '적합'으로 통일되어, 현재 모든 업소의 등급이 '적합'입니다.
  그래서 화면에서는 등급 대신 지정 유효/만료 임박/만료 상태를 보여줍니다.
- 좌표가 없는 업소 34곳(0.07%)은 지도와 `내 주변`에 나오지 않습니다(군부대, 고속도로 휴게소, 공장·캠퍼스 내부,
  공항·역사, 신규 도로 등 카카오에서 찾지 못한 주소). 업소 검색과 통계에는 그대로 포함됩니다.
- 지역명은 주소 원문을 따릅니다. 예: 광주·전남 주소는 `전남광주통합특별시`로 표시됩니다.

## 프로젝트 구조

```
hygiene-finder-19/
├── backend/                 FastAPI + SQLite
│   └── app/
│       ├── main.py          API (검색, 통계, 내 주변, 동기화, 지오코딩)
│       ├── sync.py          식품안전나라 C004 전체 동기화
│       ├── geocode.py       카카오 로컬 API 주소 → 좌표 변환
│       ├── db.py            스키마, 마이그레이션
│       └── config.py        .env 설정
├── frontend/                React + Vite + Leaflet
│   └── src/pages/           SearchPage(업소 검색), NearbyPage(내 주변), StatsPage(통계)
├── deploy/
│   ├── nginx.conf           서버 nginx 설정 (HTTPS, /api 프록시)
│   └── deploy.sh            서버 배포 스크립트 (GitHub Actions 가 호출)
└── .github/workflows/deploy.yml   main push 시 EC2 자동 배포
```

## 로컬 실행

### 요구 사항

- Python 3.11 이상, Node.js 18 이상
- 식품안전나라 오픈API 인증키 ([이용 신청](https://www.foodsafetykorea.go.kr/api/openApiInfo.do?menu_grp=MENU_GRP31&menu_no=661&show_cnt=10&start_idx=1&svc_no=C004))
- 카카오 REST API 키 (`내 주변` 기능용, [카카오 개발자](https://developers.kakao.com)에서 앱 생성 후 카카오맵 사용 설정)

### 1. 인증키 설정 (`backend/.env`)

키는 코드에 넣지 않고 `backend/.env` 에서만 읽습니다. 이 파일은 `.gitignore` 대상이라 커밋되지 않습니다.

```bash
cd backend
cp .env.example .env          # Windows PowerShell: Copy-Item .env.example .env
```

`backend/.env` 를 편집기로 열어 키를 넣습니다.

```
FOODSAFETY_API_KEY=발급받은_식품안전나라_인증키
KAKAO_REST_API_KEY=발급받은_카카오_REST_API_키
```

| 변수 | 기본값 | 설명 |
|---|---|---|
| `FOODSAFETY_API_KEY` | (필수) | 식품안전나라 인증키 |
| `KAKAO_REST_API_KEY` | 없음 | 카카오 REST API 키. 없으면 지오코딩·주소 검색이 동작하지 않음 |
| `SYNC_TOKEN` | 없음 | 값을 넣으면 `POST /api/sync`, `POST /api/geocode` 에 `X-Sync-Token` 헤더 필요 (배포 시 필수 권장) |
| `STARTUP_SYNC` | `true` | DB가 비어 있을 때만 서버 시작 시 전체 동기화. `false` 면 항상 건너뜀 |
| `GEOCODE_RPS` | `8` | 카카오 API 초당 최대 호출 수 |
| `GEOCODE_WORKERS` | `4` | 지오코딩 동시 작업 수 |
| `DB_PATH` | `backend/hygiene.db` | SQLite 파일 경로 |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | 허용 출처 (쉼표 구분) |

### 2. 백엔드

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

DB가 비어 있으면 시작하면서 전체 데이터(약 4.7만 건)를 1000건 단위로 받아 저장합니다(약 10분).
이후 재시작 때는 동기화를 건너뜁니다. 갱신하려면 `POST /api/sync`. API 문서: http://localhost:8000/docs

### 3. 지도 좌표 만들기 (선택)

`내 주변` 을 쓰려면 지오코딩이 필요합니다. 로컬 확인용으로는 한 지역만 변환하면 충분합니다.

```bash
curl -X POST "http://localhost:8000/api/geocode?region=대구"   # 대구만 (약 5분)
curl http://localhost:8000/api/geocode                          # 진행률
```

### 4. 프론트엔드

```bash
cd frontend
npm install
npm run dev
```

http://localhost:5173 을 엽니다. `/api` 요청은 Vite 프록시가 `http://127.0.0.1:8000` 으로 전달합니다.
`localhost` 는 보안 컨텍스트로 취급되어 로컬에서도 `내 위치` 버튼이 동작합니다.

## 지오코딩 (주소 → 좌표)

- 카카오 로컬 API로 **주소 검색 → (결과 없으면) 시군구 + 업소명 키워드 검색** 순으로 시도합니다.
  키워드 결과는 시군구가 일치할 때만 채택해 다른 지역의 같은 이름 가게를 잘못 잡지 않습니다.
- 같은 주소는 한 번만 호출하고, 같은 주소의 업소 모두에 좌표를 저장합니다.
- 초당 호출 수 제한(`GEOCODE_RPS`), 네트워크·429·5xx 오류는 재시도, 끝내 실패하면 `geocode_status='error'`.
  인증 실패(401/403)면 작업 전체를 멈춥니다. 카카오 오류 메시지에 들어 있는 키 값은 저장·로그 전에 가립니다.
- **서버를 재시작해도 자동으로 시작하지 않습니다.** 수동으로만 시작하며, 중단되면 다시 시작했을 때 남은 주소부터 이어 갑니다.
- 동기화로 데이터를 교체할 때 주소가 같은 업소는 좌표를 이어받으므로, 동기화 후에는 새 주소만 변환하면 됩니다.

```bash
TOKEN=$(sed -n 's/^SYNC_TOKEN=//p' backend/.env)
curl -X POST -H "X-Sync-Token: $TOKEN" "http://127.0.0.1:8000/api/geocode"                    # 남은 주소 전체
curl -X POST -H "X-Sync-Token: $TOKEN" "http://127.0.0.1:8000/api/geocode?region=서울"        # 지역 한정
curl -X POST -H "X-Sync-Token: $TOKEN" "http://127.0.0.1:8000/api/geocode?retry_failed=true"  # error 건 재시도
curl -X POST -H "X-Sync-Token: $TOKEN" "http://127.0.0.1:8000/api/geocode/cancel"             # 중지
curl http://127.0.0.1:8000/api/geocode                                                        # 진행률
```

진행률 응답의 `done`/`total` 이 처리량, `ok`/`not_found`/`error` 가 결과, `coverage.shops_located` 가 좌표 보유 업소 수입니다.
전국 약 4.2만 주소 기준 약 90분이 걸렸습니다(초당 약 8건).

## API

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/api/shops?name=&region=&type=&active_only=&expiring=&page=&size=` | 업소 검색. `region` 은 시도(서울, 경기 …), `expiring=true` 면 지정종료일 3개월 이내만 (종료일 가까운 순) |
| GET | `/api/stats?active_only=` | 지역·업종·지정기관·연도·월별 집계, 만료 임박 수, 동기화 상태 |
| GET | `/api/stats/region?region=&active_only=` | 지역 × 업종: 시도 내 업종별 수·비중(전국 비중 포함), 시군구 × 업종 표 |
| GET | `/api/nearby?lat=&lng=&radius=1000&type=&expiring=&active_only=true&limit=100` | 반경(m, 50~5000) 안 업소를 거리순으로 (`distance_m` 포함, `limit` 최대 300). 위경도 사각형으로 먼저 거른 뒤 하버사인 거리로 판정. `summary` 에 반경 안 업종별 수(필터 적용 전) |
| GET | `/api/geocode-address?q=` | 주소·동네·장소 이름 → 좌표 (`alternatives` 에 다른 지역 후보). IP별 분당 20회 제한(초과 시 429), 결과 캐시. 카카오 키는 서버에서만 사용 |
| POST | `/api/geocode?limit=&region=&retry_failed=` | 지오코딩 시작 (백그라운드, `X-Sync-Token`) |
| GET | `/api/geocode` | 지오코딩 진행률과 전체 좌표 보유 현황 |
| POST | `/api/geocode/cancel` | 진행 중인 지오코딩 중지 (`X-Sync-Token`) |
| POST | `/api/sync` | 전체 동기화 시작 (백그라운드, `X-Sync-Token`) |
| GET | `/api/sync` | 동기화 상태 (`status`: never / running / ok / error) |

동기화와 지오코딩은 동시에 실행되지 않습니다(한쪽이 진행 중이면 409).

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

파생 컬럼:

- `sido`: 주소 첫 단어. 같은 시도의 표기만 약칭으로 통일(서울특별시 → 서울), 그 밖의 지역명은 원본 그대로
- `sigungu`: 주소 두 번째 단어 (세종은 시군구가 없어 비움)
- `grade`: 지정등급에서 공백을 뺀 값
- `is_active`: 폐업했거나 지정이 취소되었으면 0
- `sort_name`: 정렬용 업소명 (앞쪽 기호 `%`, `#`, `(` 등 제거)
- `lat`, `lng`, `geocode_status`: 지오코딩 결과. `geocode_status` 는 NULL(미변환) / `ok_address` / `ok_keyword` / `not_found` / `error`

통계의 지정기관별 집계에서는 "식품의약품안전처"로 시작하는 기관(하위 부서 포함)을 하나로 합칩니다.

마이그레이션은 서버 시작 시 자동으로 적용됩니다. 빠진 컬럼만 추가하고 기존 데이터는 유지하며,
파생 컬럼 계산 방식이 바뀌면 `db.SCHEMA_VERSION` 을 올려 저장된 원본 값으로 다시 계산합니다.
동기화는 모든 페이지를 받은 뒤 한 트랜잭션으로 교체하므로 중간에 실패해도 기존 데이터가 남습니다.

## 배포·운영

### 서버 구성 (AWS EC2, 서울 리전)

| 항목 | 내용 |
|---|---|
| OS | Ubuntu 26.04 LTS (t3.micro, 스왑 2GB) |
| 코드 | `/home/ubuntu/hygiene-finder-19` (GitHub 저장소 clone) |
| 백엔드 | systemd 서비스 `hygiene-api` (uvicorn, 127.0.0.1:8000, 재부팅 시 자동 시작) |
| 프론트 | `npm run build` 결과를 `/var/www/hygiene-finder` 에서 nginx 가 서빙 |
| nginx | [deploy/nginx.conf](deploy/nginx.conf) — HTTPS, `/api` → 127.0.0.1:8000 프록시 |
| 비밀 값 | 서버의 `backend/.env` (권한 600, git 에 없음) |

### HTTPS (Let's Encrypt)

도메인이 없어 IP를 이름에 넣으면 그 IP로 해석되는 무료 DNS `sslip.io` 를 사용합니다.
`내 위치`(브라우저 위치 정보)는 HTTPS 에서만 동작합니다.

- 주소: **https://15-165-113-119.sslip.io** — `http://` 와 IP 접속은 이 주소로 301 리다이렉트
- 발급: `sudo certbot certonly --webroot -w /var/www/letsencrypt -d 15-165-113-119.sslip.io`
- nginx 설정은 저장소 파일이 기준입니다. certbot 이 설정을 고치지 않도록 `certonly --webroot` 로 인증서만 받고,
  `/.well-known/acme-challenge/` 는 http 에서도 열어 둡니다.
- 자동 갱신: `certbot.timer` + `/etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh`(갱신 후 nginx reload).
  점검: `sudo certbot renew --dry-run`
- EC2 를 중지 후 시작하면 퍼블릭 IP 가 바뀝니다. 그 경우 `deploy/nginx.conf` 의 도메인 3곳과 인증서를 새 IP 로 다시 만들어야 합니다
  (Elastic IP 를 붙이면 고정됩니다).

### 자동 배포 (GitHub Actions)

`main` 에 push 하면 [.github/workflows/deploy.yml](.github/workflows/deploy.yml) 이 EC2 에 SSH 로 접속해
`git pull --ff-only` 후 [deploy/deploy.sh](deploy/deploy.sh) 를 실행합니다.

1. 백엔드 의존성 설치
2. 프론트 빌드 → `/var/www/hygiene-finder` 반영
3. `deploy/nginx.conf` 가 바뀌었으면 갱신 (`nginx -t` 통과 시에만 reload)
4. `hygiene-api` 재시작 후 `/api/health` 확인, 외부 https 접속 확인

- `backend/.env` 와 DB 파일은 git 추적 대상이 아니라 pull 로 바뀌지 않고, 배포 스크립트도 건드리지 않습니다.
  두 파일이 실수로 git 에 추가되면 배포가 중단됩니다.
- 커밋 메시지에 `[skip ci]` 를 넣으면 배포를 건너뜁니다(문서만 바꿀 때, 서버에서 긴 작업이 돌고 있을 때).
- Actions 탭의 `Run workflow` 로 수동 실행도 됩니다.

필요한 Secrets (저장소 Settings → Secrets and variables → Actions):

| 이름 | 값 |
|---|---|
| `EC2_HOST` | EC2 퍼블릭 IP |
| `EC2_USER` | `ubuntu` |
| `EC2_SSH_KEY` | `.pem` 키 파일 전체 내용 (`-----BEGIN` ~ `-----END` 줄 포함) |

### 운영 메모

- **배포 = 백엔드 재시작**입니다. 동기화나 지오코딩이 돌고 있을 때 push 하면 중단됩니다.
  기존 데이터는 유지되며, 다시 시작하면 됩니다(지오코딩은 남은 주소부터 이어 감).
- **자동 보안 업데이트 후 재시작 제외**: Ubuntu 자동 업데이트(needrestart)가 `hygiene-api` 를 재시작해 긴 작업이 끊긴 적이 있어,
  `/etc/needrestart/conf.d/90-hygiene-api.conf` 로 이 서비스만 자동 재시작에서 뺐습니다.
  업데이트된 라이브러리는 다음 배포나 재부팅 때 반영됩니다.
- 서버에서 수동 동기화·지오코딩 (토큰을 화면에 출력하지 않는 방식):

  ```bash
  cd ~/hygiene-finder-19/backend
  TOKEN=$(sed -n 's/^SYNC_TOKEN=//p' .env)
  curl -X POST -H "X-Sync-Token: $TOKEN" http://127.0.0.1:8000/api/sync      # 데이터 갱신 (약 10분)
  curl -X POST -H "X-Sync-Token: $TOKEN" http://127.0.0.1:8000/api/geocode   # 갱신 후 새 주소 좌표 변환
  ```

  서버 nginx 는 80 포트를 https 로 리다이렉트하므로, 서버 안에서는 `127.0.0.1:8000` 으로 직접 호출합니다.
- 진행률은 브라우저에서도 볼 수 있습니다: https://15-165-113-119.sslip.io/api/sync , https://15-165-113-119.sslip.io/api/geocode

## 변경 이력

**2026-11-13**
- 업소 검색·통계 사이트 첫 배포 (EC2, systemd, nginx)
- 등급 대신 지정 상태(유효/만료 임박/만료) 표시, 지역 × 업종 경쟁 현황표, 연도별 지정 추이
- GitHub Actions 자동 배포
- `내 주변` 지도 검색: 카카오 지오코딩(전국 99.93%), 반경 검색, 업종 요약 카드, Leaflet + OpenStreetMap
- HTTPS 적용 (Let's Encrypt, sslip.io), http → https 리다이렉트
- 지도 범위 자동 맞춤, Ctrl+휠 확대·축소, 반경 전체 보기 버튼
