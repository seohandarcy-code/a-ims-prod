# 팀 투자 관리 시스템 (IMS)

Vue 3 + Vite + TypeScript frontend, FastAPI backend, Nginx reverse proxy — local Windows development setup.
계획 문서는 `docs/`, 원본 계산 로직 참고 코드는 `legacy/`를 참고한다.

## 구조
```
backend/    FastAPI app + venv(backend/.venv) + SQLite DB(backend/data/app.db) + tests/
frontend/   Vue 3 + Vite + TypeScript app (eslint.config.js 포함)
nginx/      nginx.conf(로컬 dev용)
scripts/    start-dev.ps1 / stop-dev.ps1
docs/       계획 문서(plan_v5 등), DB 전환 로드맵(db-migration-roadmap.md), 환경변수/Secret
            카탈로그(ENV_AND_SECRETS.md), 디자인 리뷰 기록, 이번 단계 작업 지침(CLAUDE_DEV_FOCUS.md)
legacy/     원본 Streamlit 코드 및 raw 데이터(raw_new.dat)
```

지금 이 저장소는 **로컬에서 완벽히 동작하는 화면 개발**에만 집중한다 — 작업 범위와
원칙은 `docs/CLAUDE_DEV_FOCUS.md`를 따른다. Dockerfile/K8s manifest/Jenkinsfile 등
사내 PDEP 반입용 인프라 산출물은 이 저장소가 아니라 별도 스냅샷 저장소
(`IMS_DEV_handoff`)에 보존되어 있으며, PDEP 실제 규격이 확인되면 그때 다시 다룬다.

## Setup
```powershell
py -3.12 -m venv backend\.venv
backend\.venv\Scripts\pip.exe install -r backend\requirements.txt

cd frontend
npm install
cd ..
```
`requirements.txt`에 SQLite 데이터 계층에 필요한 `sqlalchemy`/`alembic`이 이미 포함되어 있어
별도 설치 단계는 없다. DB 파일 경로는 기본값(`backend/data/app.db`)을 그대로 쓰면 되고,
바꾸고 싶으면 `backend/.env`에 `DATABASE_URL`을 설정한다(`backend/.env.example` 참고).

## Running
```powershell
powershell -ExecutionPolicy Bypass -File scripts\start-dev.ps1
```
Open http://127.0.0.1:8080 — Nginx가 `/api/*`는 FastAPI(8000)로, 나머지는 Vite dev server(5173)로 프록시한다.

```powershell
powershell -ExecutionPolicy Bypass -File scripts\stop-dev.ps1
```

## 데이터 계층 (SQLite, 2026-09-16부터)

원래 plan_v5의 No-DB 구조(base/edits/current 파일 스냅샷)에서 SQLite로 전환했다. 상세
배경과 전체 로드맵(SQLite → PostgreSQL → 환경변수/Secret 관리 → SSO/사용자 권한 DB)은
`docs/db-migration-roadmap.md`를 참고한다.

**동작 방식**: 서버 기동 시 `backend/data/app.db`(SQLite, git에 커밋하지 않음)가
비어있으면 `backend/data/base/*.dat`로부터 **최초 1회만** 자동 시딩하고, 이후로는 오직
DB만 읽고 쓴다(`backend/app/db/seed.py`). 즉 `.dat`는 "처음 한 번 채워 넣는 씨앗 데이터"일
뿐이고, 관리자가 화면에서 편집한 내용은 전부 DB에 쌓인다 — `.dat`를 다시 읽지 않으므로
편집 내용이 서버 재기동으로 사라지지 않는다.

- `backend/data/base/raw_dt_new3.dat`(현재 `BASE_FILE`)는 git에 포함되어 있다 — 목업
  데이터이고 회사 정보가 없어 커밋해도 안전하며, 덕분에 fresh clone 직후 별도 파일 전달
  없이 `backend/data/app.db`가 자동 생성/시딩되어 바로 실행 가능하다.
- `backend/data/app.db`(및 `*.db-wal`/`*.db-shm`)는 `.gitignore` 대상이라 커밋되지 않는다.
  **fresh clone 후 첫 실행 시 자동 생성**되므로 별도 설치 단계가 필요 없다. 로컬 DB를
  지우고 처음부터 다시 시딩하고 싶으면 파일만 삭제하고 서버를 재기동하면 된다.
- **운영 DB 백업 → 로컬 개발 반영**: 운영에서 쌓인 데이터를 로컬로 가져오고 싶을 때는
  `GET /api/v1/admin/export/dat`(+`/export/column-types`)로 백업 스냅샷을 내려받은 뒤,
  ```powershell
  cd backend
  .venv\Scripts\python.exe scripts\reseed_from_dat.py --file <다운로드한.dat> --reset
  ```
  로 로컬 DB를 그 스냅샷 상태로 재구성한다.
- 스키마 마이그레이션은 Alembic으로 관리한다(`backend/alembic/`). 로컬 dev에서는 앱이
  기동 시 필요한 테이블을 알아서 만들어 주므로(`app/db/seed.py`) 평소에 Alembic 명령을
  직접 실행할 필요는 없다.

## 운영 중인 시스템의 데이터를 새 .dat로 통째로 교체하기

이미 `.dat`로 시딩되어 데이터가 쌓인 상태로 운영 중인 시스템에서, **원본 `.dat`를 새로
바꿔서 DB 내용을 통째로 다시 구성**하고 싶을 때의 방법이다(SQLite/PostgreSQL 둘 다 동일).

**핵심 전제**: `seed_if_empty()`(`backend/app/db/seed.py`)는 이름 그대로 **DB가
비어있을 때만** `.dat`로 자동 시딩한다. 이미 데이터가 쌓인 DB에 새 `.dat`만 갖다 놔도
서버를 재기동해봐야 아무 일도 일어나지 않는다 — 이 전제를 모르면 "분명 파일을
바꿨는데 왜 반영이 안 되지"라는 혼란이 생긴다.

두 가지 방법이 있고, 상황에 따라 고른다.

| 방법 | 언제 쓰나 | 옛 데이터는 |
|---|---|---|
| **A. 같은 DB를 재시딩** (권장) | 옛 데이터는 버리고 같은 시스템을 새 데이터로 완전히 교체 | 삭제됨(되돌릴 백업을 따로 뒀다면 복원 가능) |
| **B. 새 DB로 전환** | 옛 시스템은 그대로 보존하면서 별도의 새 환경을 새 데이터로 새로 띄움 | 그대로 남음(수동 정리 전까지 보존) |

### 방법 A: 같은 DB를 새 `.dat`로 재시딩 (권장)

`DATABASE_URL`/`DB_*` 등 접속 정보를 하나도 안 바꾼다 — 운영 환경의 Secret/ConfigMap을
건드릴 필요가 없다.

```powershell
cd backend
.venv\Scripts\python.exe scripts\reseed_from_dat.py --file <새로만든.dat> --reset
```

- `--reset`이 기존 테이블을 전부 비우고 새 `.dat` 내용으로 다시 채운다(`app/db/seed.py`의
  `replace_all_from_dataframe()` — 최초 시딩과 완전히 같은 코드 경로를 탄다).
- **이 스크립트는 DB에 직접 붙어 별도 프로세스로 동작한다.** 앱이 이미 떠 있다면 앱
  메모리 캐시(`DataStore`)는 이 변경을 바로 모른다 — **재시딩 후 앱을 재기동**해야 새
  데이터가 화면에 반영된다(짧은 다운타임 발생).
- 커스텀 컬럼(관리자가 추가한 컬럼) 타입까지 그대로 옮기고 싶으면 `--types <타입json>`도
  같이 넘긴다(`GET /api/v1/admin/export/column-types` 응답을 저장해둔 파일).

### 방법 B: 새 DB로 전환(옛 시스템 보존)

새 DB를 만들고 `DATABASE_URL`(또는 `DB_NAME`)이 그 DB를 가리키게 바꾸면, 그 DB는
비어있으니 앱 기동 시 **자동으로** 시딩된다. 다만 두 가지를 놓치기 쉽다:

1. **`BASE_FILE`은 환경변수가 아니라 코드에 박힌 경로다** — `backend/app/config.py`의
   `BASE_FILE`(현재 `backend/data/base/raw_dt_new3.dat`)을 새 `.dat` 파일로 가리키도록
   코드를 바꿔서 배포해야 한다(지금까지 `raw_dt_new2_rev.dat` → `raw_dt_new3.dat`로
   교체해온 것과 같은 방식 — 새 파일 추가 + `BASE_FILE` 갱신). `DB_NAME`만 바꾼다고
   시딩 내용이 저절로 바뀌지 않는다.
2. **옛 DB는 지워지지 않는다** — 보존이 목적이 아니라면 나중에 수동으로 정리해야 한다.

## PostgreSQL로 전환해서 개발하기 (2단계, 로컬 검증됨)

기본값은 여전히 SQLite다. `DATABASE_URL`을 설정한 개발자만 PostgreSQL로 옵트인하는
것이지, 프로젝트 전체의 기본 동작을 바꾸는 게 아니다. 상세 배경은
`docs/db-migration-roadmap.md` 2단계 참고.

```powershell
# 1) PostgreSQL 14 설치 (winget)
winget install --id PostgreSQL.PostgreSQL.14 -e --accept-package-agreements --accept-source-agreements --silent
# 설치 직후 postgres 슈퍼유저 비밀번호는 기본값 "postgres", 서비스는 자동 시작된다.

# 2) 이 프로젝트 전용 role/database 생성 (postgres 슈퍼유저를 앱 접속에 직접 쓰지 않는다)
$env:PGPASSWORD = "postgres"
$psql = "C:\Program Files\PostgreSQL\14\bin\psql.exe"
& $psql -U postgres -h 127.0.0.1 -p 5432 -c "CREATE ROLE ims_dev WITH LOGIN PASSWORD 'ims_dev_local_pw' CREATEDB;"
& $psql -U postgres -h 127.0.0.1 -p 5432 -c "CREATE DATABASE ims_dev OWNER ims_dev;"

# 3) 드라이버 설치 (requirements.txt에 이미 포함되어 있음)
cd backend
.venv\Scripts\pip.exe install -r requirements.txt

# 4) backend/.env에 DATABASE_URL 설정 (backend/.env.example 참고)
#    DATABASE_URL=postgresql+psycopg://ims_dev:ims_dev_local_pw@127.0.0.1:5432/ims_dev

# 5) 스키마 생성 (앱이 기동 시 자동으로도 만들어 주지만, Alembic으로 명시적으로 확인하려면)
.venv\Scripts\python.exe -m alembic upgrade head
```

이후 `scripts\start-dev.ps1`로 평소처럼 실행하면 `backend/data/base/*.dat`로부터 이
PostgreSQL DB에 최초 시딩되고, 이후로는 SQLite 때와 완전히 동일하게 동작한다(코드
변경 없음 — `app/data/store.py`가 SQLite/PostgreSQL 방언을 모른다).

테스트도 같은 방식으로 PostgreSQL 대상으로 돌릴 수 있다(평소 `pytest tests\`는
그대로 격리된 SQLite 임시 파일을 쓴다):
```powershell
$env:DATABASE_URL = "postgresql+psycopg://ims_dev:ims_dev_local_pw@127.0.0.1:5432/ims_dev_test"
.venv\Scripts\pytest.exe tests\
```

## 환경변수와 Secret

이 프로젝트의 환경변수/Secret 전체 카탈로그(무엇이 ConfigMap이고 무엇이 Secret인지,
운영 배포 관점)는 `docs/ENV_AND_SECRETS.md`가 정본이다. 이 절은 **로컬에서 어떻게
설정하고, 그 값이 실제 코드의 어디와 연결되는지**를 설명한다.

### 어디서 읽고, 어디에 설정하는가

- 백엔드는 `backend/app/config.py`가 유일한 진입점이다. 모듈 맨 위에서
  `load_dotenv()`를 호출해 `backend/.env` 파일(git 미추적, 직접 만들어야 함)을 읽고,
  이후 각 설정값을 `os.getenv(...)`로 꺼내 쓴다. `backend/.env.example`은 실제 값이
  없는 키 이름/설명만 담은 템플릿이다 — 처음 셋업할 때 이 파일을 복사해서 시작한다.
  ```powershell
  cd backend
  copy .env.example .env
  # .env를 열어 필요한 값만 채운다 (비워두면 각 변수의 기본 동작을 그대로 씀)
  ```
- 프론트엔드는 `frontend/.env.example`을 `frontend/.env`로 복사해서 쓰며,
  `import.meta.env.VITE_API_BASE_URL`로 읽는다(Vite 관례상 `VITE_` 접두사가 붙은
  변수만 클라이언트 번들에 노출된다).
- 두 `.env` 파일 모두 `.gitignore` 대상이라 커밋되지 않는다 — 실제 값은 항상 로컬
  파일 또는(배포 시) K8s ConfigMap/Secret에만 존재한다.

### 환경변수 값이 코드와 연결되는 지점

| 환경변수 | 코드 연결 지점 | 동작 |
|---|---|---|
| `DATABASE_URL` / `DB_HOST` 등 5종 | `backend/app/config.py`의 `_build_database_url()` → `DATABASE_URL` 상수 → `backend/app/db/engine.py`의 `create_engine(DATABASE_URL)` | 아래 "데이터 계층 접속 정보" 참고 |
| `ADMIN_BOOTSTRAP_PASSWORD` | `backend/app/config.py`의 `ADMIN_BOOTSTRAP_PASSWORD` → `backend/app/auth/state.py`의 `DEFAULT_PASSWORD` → `AdminAuthStore.__init__`이 초기 `_password`로 사용 | 서버가 (재)기동될 때마다 관리자 비밀번호가 이 값으로 리셋된다 |
| `DATA_DIR` | `config.py`의 `DATA_DIR` → `BASE_DIR`/`DATA_REV_DIR`/SQLite 기본 경로 계산에 사용 | `.dat` 시딩 소스 및 SQLite 파일 위치를 바꾼다 |
| `CURRENT_YEAR` / `CURRENT_MONTH_OVERRIDE` | `config.py` → `backend/app/data/normalize.py`의 `infer_current_month()` | 대시보드 "기준월" 계산에 영향 |
| `CORS_ORIGINS` | `config.py` → `backend/app/main.py`의 `CORSMiddleware` | 브라우저에서 API 호출을 허용할 origin 목록 |
| `HOST` / `PORT` | `scripts/start-dev.ps1`이 uvicorn 실행 인자로 직접 넘김 | 바인드 주소/포트 |
| `VITE_API_BASE_URL` (frontend) | `frontend/src/api/client.ts`의 `import.meta.env.VITE_API_BASE_URL` | 백엔드 API 베이스 URL |

### 데이터 계층 접속 정보 — 우선순위와 실제 동작

`_build_database_url()`(`backend/app/config.py`)이 매 프로세스 시작 시 아래 순서로
판단한다:

1. `DATABASE_URL`이 채워져 있으면 **그 값을 그대로** 사용(나머지 `DB_*`는 무시).
2. 비어 있고 `DB_HOST`만 채워져 있으면, `DB_HOST`/`DB_PORT`(기본 5432)/`DB_NAME`(기본
   `ims`)/`DB_USER`/`DB_PASSWORD`를 조합해 `postgresql+psycopg://...` DSN을 만든다 —
   `DB_USER`/`DB_PASSWORD`는 `urllib.parse.quote_plus`로 URL-safe하게 인코딩되므로,
   비밀번호에 `@`, `/`, 공백 같은 특수문자가 있어도 안전하다(사람이 DSN 문자열을
   직접 조립할 때 흔히 나는 실수를 코드가 대신 처리).
3. 둘 다 비어 있으면 `sqlite:///{DATA_DIR}/app.db`로 폴백(fresh clone 기본값).

**언제 어떤 방식을 쓰나:**
- 로컬 개발(기본): 아무것도 설정하지 않음 → SQLite.
- 로컬에서 PostgreSQL로 검증하고 싶을 때: `DATABASE_URL` 하나만 채움(아래
  "PostgreSQL로 전환해서 개발하기" 참고) — 값 하나로 빠르게 전환.
- 여러 컴퓨터/서버에 배포할 때: `DATABASE_URL` 대신 `DB_HOST`/`DB_PORT`/`DB_NAME`을
  ConfigMap으로, `DB_USER`/`DB_PASSWORD`만 Secret으로 나눠서 주입 — 서버마다 완성된
  DSN 문자열을 새로 만들 필요 없이, 접속 정보(호스트/이름)와 자격증명(계정/비밀번호)을
  독립적으로 교체·로테이션할 수 있다.

### 관리자 비밀번호도 서버마다 다르게

`ADMIN_BOOTSTRAP_PASSWORD`를 비워두면 기존처럼 `"0000"`이 초기 비밀번호다(로컬 개발
편의 유지). 여러 서버에 배포한다면 서버마다 이 값을 Secret으로 다르게 주입해서, 모든
환경이 똑같이 잘 알려진 기본 비밀번호를 공유하지 않게 하는 것을 권장한다. 어차피
서버가 재기동되면 항상 이 값으로 리셋되므로(파일 영속화 안 함, `backend/app/auth/state.py`),
운영 중 관리자가 바꾼 비밀번호가 아니라 "재기동 시 되돌아갈 기본값"이라는 점에
유의한다.

### 다른 컴퓨터/서버로 옮길 때 체크리스트

1. `backend/.env.example` → `backend/.env` 복사, 필요한 값만 채움(`DATABASE_URL` 또는
   `DB_*`, `ADMIN_BOOTSTRAP_PASSWORD`, 그 외 필요 시 `CORS_ORIGINS` 등).
2. `frontend/.env.example` → `frontend/.env` 복사, `VITE_API_BASE_URL`을 그 서버에서
   실제로 접근 가능한 백엔드 주소로 설정.
3. 두 `.env` 모두 커밋하지 않는다 — 서버별로 각자 만든다.
4. 배포 파이프라인(K8s 등)에서 이 값들을 ConfigMap/Secret으로 주입하는 방법은
   `docs/ENV_AND_SECRETS.md`의 분류표를 따른다.

## 테스트 & 린트
```powershell
# 백엔드
cd backend
.venv\Scripts\pytest.exe tests\

# 프론트엔드
cd frontend
npm run lint
npm run build
npm run test   # 현재는 placeholder (테스트 프레임워크 미도입)
```

## Health Check
- `GET /health` — 기존 단순 헬스체크.
- `GET /health/live` — liveness(프로세스 생존 여부).
- `GET /health/ready` — readiness(데이터 로드 완료 여부, `data_store.is_ready` 기반). 준비 전이면 503.
