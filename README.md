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

## SSO로 전환해서 로그인 검증하기 (4단계, 로컬 검증됨)

기본값은 여전히 `AUTH_MODE=local`이다(대시보드 공개, 관리자 편집만 아이디/비밀번호로
게이트 — 지금까지와 동일). `AUTH_MODE=sso`로 옵트인하면 **대시보드 자체가 로그인
게이트 뒤로 들어간다** — 로그인하지 않으면 화면을 볼 수 없고, **IdP 인증에
성공해도 관리자가 "접근 권한 관리" 화면에서 직접 등록한 사람만** 실제로 로그인이
허용된다(등록 시 `user`(조회 전용)/`admin`(편집 가능) role도 함께 정해진다 —
개인별 계정 도입은 아님, 역할이 2종류로 늘었을 뿐). IdP에 이미 로그인돼 있으면
(사내 다른 페이지 등) 버튼 클릭 없이 자동으로 로그인 상태가 된다. 상세 배경은
`docs/db-migration-roadmap.md` 4단계 참고.

사내 실제 SSO에 연결하기 전에, PostgreSQL 때와 같은 원칙으로 Docker 없이 로컬에
테스트용 IdP(Keycloak)를 직접 띄워서 리다이렉트 → 로그인 → 콜백 → 세션 발급까지
실제 흐름을 검증한다.

```powershell
# 1) Java 17 설치 (winget) — Keycloak은 JVM 기반이라 Docker 없이도 실행 가능
winget install --id EclipseAdoptium.Temurin.17.JDK -e --accept-package-agreements --accept-source-agreements --silent

# 2) Keycloak 배포판(zip) 다운로드 후 저장소 밖에 압축 해제
#    (PostgreSQL을 "C:\Program Files\"에 설치한 것과 같은 원칙 — 프로젝트 소스가 아닌 외부 도구)
#    https://github.com/keycloak/keycloak/releases 에서 keycloak-26.7.4.zip 다운로드 후
Expand-Archive keycloak-26.7.4.zip -DestinationPath C:\tools\keycloak

# 3) 개발 모드로 기동 (포트 8180 — nginx 8080/frontend 5173/backend 8000과 안 겹침)
$env:KC_BOOTSTRAP_ADMIN_USERNAME = "admin"
$env:KC_BOOTSTRAP_ADMIN_PASSWORD = "admin"
C:\tools\keycloak\keycloak-26.7.4\bin\kc.bat start-dev --http-port=8180

# 4) 별도 터미널에서 Admin REST API로 realm/client/테스트 사용자 생성
#    (콘솔 http://127.0.0.1:8180 에서 수동으로 해도 되지만, 재현 가능하도록 API로 스크립트화)
$token = (Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8180/realms/master/protocol/openid-connect/token" `
  -Body @{ grant_type = "password"; client_id = "admin-cli"; username = "admin"; password = "admin" }).access_token
$headers = @{ Authorization = "Bearer $token"; "Content-Type" = "application/json" }

# realm 생성
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8180/admin/realms" -Headers $headers `
  -Body (@{ realm = "ims"; enabled = $true } | ConvertTo-Json)

# confidential 클라이언트 생성 (redirect URI는 SSO_REDIRECT_URI와 정확히 일치해야 함)
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8180/admin/realms/ims/clients" -Headers $headers -Body (@{
  clientId = "ims-backend"; enabled = $true; publicClient = $false; clientAuthenticatorType = "client-secret"
  redirectUris = @("http://127.0.0.1:8080/api/v1/auth/sso/callback"); standardFlowEnabled = $true
} | ConvertTo-Json)

# 위에서 만든 클라이언트의 시크릿 값 확인 (아래 backend/.env의 SSO_CLIENT_SECRET에 사용)
$clientUuid = (Invoke-RestMethod -Uri "http://127.0.0.1:8180/admin/realms/ims/clients?clientId=ims-backend" -Headers $headers)[0].id
(Invoke-RestMethod -Uri "http://127.0.0.1:8180/admin/realms/ims/clients/$clientUuid/client-secret" -Headers $headers).value

# 테스트 로그인용 사용자 생성 + 비밀번호 설정 — 브레이크글래스로 쓸 계정
# (아래 SSO_ADMIN_ALLOWLIST에 넣어서 로그인할 때마다 자동으로 admin이 되게 한다)
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8180/admin/realms/ims/users" -Headers $headers -Body (@{
  username = "ims.admin"; email = "ims.admin@example.local"; enabled = $true; emailVerified = $true
  firstName = "IMS"; lastName = "Admin"
} | ConvertTo-Json)
$userId = (Invoke-RestMethod -Uri "http://127.0.0.1:8180/admin/realms/ims/users?username=ims.admin" -Headers $headers)[0].id
Invoke-RestMethod -Method Put -Uri "http://127.0.0.1:8180/admin/realms/ims/users/$userId/reset-password" -Headers $headers -Body (@{
  type = "password"; value = "test-password"; temporary = $false
} | ConvertTo-Json)

# 일반유저(조회 전용) 검증용 계정 — 이 계정은 나중에 "접근 권한 관리" 화면에서
# 관리자가 직접 등록해야 로그인이 허용된다(아래 검증 절차 2번)
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8180/admin/realms/ims/users" -Headers $headers -Body (@{
  username = "ims.viewer"; email = "ims.viewer@example.local"; enabled = $true; emailVerified = $true
  firstName = "IMS"; lastName = "Viewer"
} | ConvertTo-Json)
$viewerId = (Invoke-RestMethod -Uri "http://127.0.0.1:8180/admin/realms/ims/users?username=ims.viewer" -Headers $headers)[0].id
Invoke-RestMethod -Method Put -Uri "http://127.0.0.1:8180/admin/realms/ims/users/$viewerId/reset-password" -Headers $headers -Body (@{
  type = "password"; value = "test-password"; temporary = $false
} | ConvertTo-Json)
```

이제 `backend/.env`에 (`backend/.env.example` 참고) 아래처럼 설정하고 백엔드를
재기동하면 로그인 화면이 자동으로 OIDC 버튼으로 바뀐다(프론트/백엔드 코드는 변경
없음 — `AUTH_MODE` 하나로 분기):

```
AUTH_MODE=sso
SSO_ISSUER_URL=http://127.0.0.1:8180/realms/ims
SSO_CLIENT_ID=ims-backend
SSO_CLIENT_SECRET=<위 client-secret 조회 결과>
SSO_REDIRECT_URI=http://127.0.0.1:8080/api/v1/auth/sso/callback
SSO_ADMIN_ALLOWLIST=ims.admin@example.local
```

브라우저로 `http://127.0.0.1:8080`에 접속하면(로그인 전) 이제 대시보드 대신
"이 대시보드는 회사 계정으로 로그인해야 볼 수 있습니다"라는 로그인 게이트 화면만
보인다 — `/api/v1/meta`·`/dashboard`·`/status-detail`이 전부 `require_viewer`로
막혀 있기 때문이다(로그인 전 이 상태가 맞다). 아래 순서로 확인한다:

1. **admin 계정 로그인(브레이크글래스)**: 게이트의 "회사 계정으로 로그인" 클릭
   → Keycloak 로그인 페이지로 리다이렉트 → `ims.admin` / `test-password`로 로그인
   → 앱으로 콜백되며 대시보드가 보이고, `SSO_ADMIN_ALLOWLIST`에 있는 계정이라
   `allowed_users`에 자동으로 admin으로 등록된다. 사이드바 하단에 "관리자 설정"
   버튼이 보이고, 누르면 로그인 폼 없이 곧바로 "전체 데이터" 편집 화면이 열린다.
   우측 상단 배지에 이름과 "관리자" 표시가 뜨는지도 확인한다.
2. **일반유저 등록 + 로그인**: "관리자 설정" → "접근 권한 관리" 탭에서 `ims.viewer`
   (`ims.viewer@example.local`)를 이름/팀만 채우고 "관리자" 체크는 하지 않은 채
   등록한다. Keycloak 계정 콘솔(`http://127.0.0.1:8180/realms/ims/account/`)
   우측 상단 메뉴 → Sign out으로 IdP 세션을 끊은 뒤, 앱을 새로고침해 다시 뜬
   게이트에서 `ims.viewer` / `test-password`로 로그인한다. 대시보드는 정상적으로
   보이지만 **"관리자 설정" 버튼 자체가 DOM에 없다**(`v-if`로 아예 렌더 안 함).
   브라우저 개발자 도구에서 이 세션 토큰으로 `/api/v1/admin/raw-data`를 직접
   호출해보면(예: `fetch`) 403이 나는 것도 확인할 수 있다 — 버튼을 숨기는 건
   UX일 뿐, 실제 방어는 서버의 `require_admin` role 체크다.
3. **미등록 계정 거부**: Keycloak에 계정을 하나 더 만들어(위 스크립트 참고)
   "접근 권한 관리"에 등록하지 않은 채로 로그인을 시도하면, IdP 인증에는
   성공해도 "등록되지 않은 계정입니다. 관리자에게 접근 권한 등록을 요청하세요."
   화면만 뜨고 대시보드는 보이지 않는다.
4. **웹에서 삭제하면 실제로 로그인이 막히는지**: admin으로 다시 로그인해 "접근
   권한 관리" 탭에서 `ims.viewer`를 삭제한다(삭제 버튼 → 삭제 확인). Keycloak
   세션을 끊고 `ims.viewer`로 다시 로그인을 시도하면, 이번엔 3번과 같은
   access_denied 화면이 뜬다 — 접근 권한 관리 화면의 삭제가 실제로 로그인
   차단까지 이어지는지 이렇게 확인한다.
5. **사내 SSO 세션 자동 연계**: admin 계정으로 로그인된 상태에서 브라우저를
   새로고침(F5)해본다 — 로그인 게이트가 다시 뜨는 대신, "로그인 확인 중..."이
   짧게 보이고 곧바로 다시 로그인 상태로 돌아온다(Keycloak 세션이 살아있어
   `prompt=none` 조용한 재인증이 성공한 것). 반대로 Keycloak 계정 콘솔에서
   Sign out한 뒤 새로고침하면 이번엔 수동 게이트가 뜬다(IdP 세션이 없어 조용한
   시도가 실패로 끝난 것).
6. **로그아웃 동작**: 앱 안에서 "로그아웃"을 누른 뒤 새로고침하면, Keycloak
   세션이 여전히 살아있는 한 조용한 재인증으로 곧바로 다시 로그인된다 — 의도된
   동작이다(우리 앱 로그아웃은 우리 세션만 끊고 IdP 세션은 그대로 둔다). 진짜
   로그아웃을 확인하려면 위 2번처럼 Keycloak 계정 콘솔에서 Sign out해야 한다.

- `SSO_ADMIN_ALLOWLIST`는 브레이크글래스다 — 실제 로그인 허용/role은
  `allowed_users` DB가 결정하고, 이 목록에 있는 계정만 로그인할 때마다 admin으로
  자동 복구된다. **최초 배포 시 반드시 한 명 이상 채워야 한다** — 안 그러면
  `allowed_users`가 비어있는 상태에서 아무도 로그인할 수 없어 관리자 화면 자체에
  못 들어가는 락아웃이 생긴다.
- 검증이 끝나면 `backend/.env`의 `AUTH_MODE`를 다시 `local`로 되돌리면 기존
  대로 대시보드가 공개되고 아이디/비밀번호 로그인으로 즉시 복귀한다(코드 변경
  불필요).
- 로컬 Keycloak을 그만 쓰려면 `kc.bat` 프로세스를 종료하면 된다 — 별도 서비스로
  등록하지 않았으므로 터미널을 닫으면 함께 종료된다.

테스트는 `backend/tests/conftest.py`가 개발자의 로컬 `backend/.env`에 있는
`AUTH_MODE=sso`와 무관하게 항상 `AUTH_MODE=local`로 강제하므로, 이 상태에서
`pytest tests\`를 그대로 돌려도 영향이 없다. SSO 쪽 판정 로직은
`backend/tests/test_sso.py`가 `AUTH_MODE`와 무관한 순수 함수로, role 기반
게이트(`require_admin`/`require_viewer`)와 silent/access_denied 콜백 분기는
`backend/tests/test_roles.py`가, `allowed_users` CRUD와 마지막 admin 보호는
`backend/tests/test_access_store.py`/`test_access_api.py`가 각각 검증한다.

## 다른 서버로 옮겨서 실제 SSO 브로커에 연동하기

지금까지는 전부 **직접 관리하는 로컬 Keycloak**을 IdP로 검증했다. 실제 배포는
**본인이 관리하지 않는 회사 SSO 브로커**에 처음 연결하는 것이라 전제가 다르다 —
브로커가 어떤 클레임을 내려주는지 미리 알 수 없고(표준이 아님), 첫 시도에서
바로 로그인이 될 것이라고 기대하지 않는 게 맞다. 이 절은 "다른 컴퓨터로 코드를
옮기고, 그 서버에 맞는 값을 채우고, 실패하면 어디를 봐야 하는지"를 다룬다.
(백엔드 컨테이너화/K8s 매니페스트는 아직 없다 — 이 단계는 지금까지처럼
`scripts/start-dev.ps1` 네이티브 실행으로 충분하고, 실제 PDEP 배포는
`docs/db-migration-roadmap.md` 4단계가 이미 별도의 "예정" 단계로 분리해뒀다.)

### A. 레포 이관

```powershell
git clone <레포 URL>
cd A-IMS_prod\backend
python -m venv .venv
.venv\Scripts\pip.exe install -r requirements.txt
cd ..\frontend
npm install
```

(기본적인 실행 방법은 위 "Setup"/"Running" 절과 동일 — 이 절은 SSO 관련
설정 차이만 다룬다.)

### B. DB 준비

새 서버 전용 PostgreSQL 인스턴스가 필요하면 위 "PostgreSQL로 전환해서 개발하기"
절의 1~2번(설치, role/database 생성)을 그대로 따른다. `DATABASE_URL`(또는
`DB_*`)을 새 서버의 실제 접속 정보로 채운 뒤, **스키마를 명시적으로 생성**한다:

```powershell
cd backend
.venv\Scripts\python.exe -m alembic upgrade head
```

이번에 추가된 `0002_add_allowed_users` 리비전까지 포함해서 `investment_rows`/
`custom_column_defs`/`custom_column_values`/`backup_snapshot`/`allowed_users`
5개 테이블이 전부 생성된다(앱을 그냥 기동해도 `app/db/seed.py`가 없는 테이블을
자동으로 만들어주긴 하지만, 운영 환경에서는 이렇게 명시적으로 한 번 돌려서
확인하는 편이 안전하다). 기존 운영 데이터를 옮기는 경우는 위 "운영 중인
시스템의 데이터를 새 .dat로 통째로 교체하기" 절의 백업/재시딩 절차를 쓴다 —
단, `allowed_users`(접근 권한 목록)는 `.dat` 시딩 대상이 아니므로 새 서버에서는
브레이크글래스 계정으로 로그인한 뒤 "접근 권한 관리" 화면에서 다시 등록해야
한다.

### C. 환경변수 체크리스트 — 로컬 Keycloak 값 vs 실제 배포 값

| 변수 | 로컬 Keycloak 테스트 때 | 실제 배포에서 |
|---|---|---|
| `AUTH_MODE` | `sso` | `sso` |
| `DATABASE_URL` | 로컬 PostgreSQL | 새 서버의 실제 DB 접속 정보 |
| `SESSION_SECRET_KEY` | 비워둬도 됨(무작위 생성) | **고정값을 Secret으로 생성**: `python -c "import secrets; print(secrets.token_urlsafe(32))"` — 비워두면 재기동마다 진행 중이던 로그인이 깨짐 |
| `SESSION_COOKIE_SECURE` | `false`(http) | 배포가 HTTPS면 **반드시 `true`** |
| `SSO_ISSUER_URL` | `http://127.0.0.1:8180/realms/ims` | 브로커 관리자에게 받은 실제 issuer URL |
| `SSO_CLIENT_ID` / `SSO_CLIENT_SECRET` | Keycloak에서 직접 발급 | 브로커 관리자가 새 client 등록 후 발급 |
| `SSO_REDIRECT_URI` | `http://127.0.0.1:8080/api/v1/auth/sso/callback` | 실제 배포 도메인의 콜백 경로(`https://<도메인>/api/v1/auth/sso/callback`) — **브로커에 등록하는 값과 문자 그대로 일치**해야 함(http/https, 트레일링 슬래시, 포트까지) |
| `FRONTEND_BASE_URL` | 비움(같은 origin) | 프론트/백엔드가 다른 도메인이면 프론트의 실제 도메인 |
| `SSO_ADMIN_ALLOWLIST` | `ims.admin@example.local` | **본인의 실제 식별자**(아래 D, E 참고 — 브로커가 뭘 보내는지 확인 전엔 추측값으로 시작) |
| `SSO_USER_ID_CLAIM` | `email`(Keycloak 기본) | 브로커가 실제로 쓰는 클레임 이름(모르면 일단 `email`로 시작 후 E번 절차로 교정) |
| `CORS_ORIGINS` | 로컬 dev 기본값 | 프론트/백엔드가 다른 도메인이면 프론트 도메인 명시 |

`SSO_ADMIN_ALLOWLIST`/`SSO_USER_ID_CLAIM` 조합이 제일 위험하다 — 실제 브로커가
어떤 클레임에 사번/고유 식별자를 담아 보내는지 코드만 봐서는 알 방법이 없다
(표준이 아니라 브로커/IT 정책마다 다름). 확인 없이 배포하면 아무도 로그인
못 하는 락아웃이 될 수 있으니, 아래 E번 런북대로 **실패를 전제로** 접근한다.

### D. 브로커 관리자에게 미리 요청해둘 것

- Confidential 클라이언트 등록 + `client_id`/`client_secret` 발급
- Redirect URI 사전 등록(위 `SSO_REDIRECT_URI`와 정확히 일치)
- `openid email profile` scope 허용 여부(`backend/app/auth/oidc.py`가 요청하는
  기본 scope — 브로커가 다른 scope 이름/추가 동의를 요구하면 이 파일을 그때
  맞게 고치면 된다)
- 어떤 클레임에 사번/이메일 등 고유 식별자가 담기는지
- 사내망 방화벽에서 새 서버가 `{ISSUER}/.well-known/openid-configuration`에
  도달 가능한지(사내 전용 브로커라면 특정 대역에서만 열려 있을 수 있음)

### E. 최초 연동 런북 (실패를 전제로 한 순서)

1. `SSO_ISSUER_URL`부터 채우고 discovery가 실제로 열리는지 먼저 확인한다 —
   이게 안 되면 나머지는 다 소용없다(네트워크/URL부터 의심):
   ```powershell
   curl "<SSO_ISSUER_URL>/.well-known/openid-configuration"
   ```
2. 나머지 `SSO_*` 값을 채우고 `AUTH_MODE=sso`로 백엔드를 띄운다.
   `SSO_ADMIN_ALLOWLIST`에는 일단 본인의 이메일(추정값)을 하나 넣는다.
   `LOG_LEVEL=INFO` 이상으로 해둔다(아래 로그를 보려면 필요).
3. 브라우저로 로그인을 시도한다. **"등록되지 않은 계정입니다"(`#access_denied=1`)가
   뜨는 게 정상**이다 — 이제 백엔드 서버 로그(콘솔 출력 또는 로그 파일)를 본다.
   `/sso/callback`이 실패 시 아래 중 하나를 남긴다:
   - `SSO_USER_ID_CLAIM(...)에 해당하는 클레임을 찾지 못함 — 실제로 받은 클레임 키: [...]`
     → 여기 나온 실제 키 목록 중 사번/이메일에 해당하는 이름으로
     `SSO_USER_ID_CLAIM`을 고친다.
   - `등록되지 않은 계정의 로그인 시도: sso_id=...`
     → 여기 찍힌 값이 실제 클레임에서 뽑아낸 식별자다. 이 값을 그대로
     `SSO_ADMIN_ALLOWLIST`에 넣는다(추정값과 실제 값이 다를 수 있다 — 예:
     이메일 대소문자, 도메인 표기 차이).
   - `SSO 콜백 실패(silent=False): ...` → OIDC 흐름 자체가 실패한 것(잘못된
     client secret, redirect_uri 불일치, 시계 오차 등) — 예외 메시지를 보고
     브로커 관리자와 함께 원인을 좁힌다.
4. 값을 고치고 백엔드를 재기동해 다시 로그인을 시도한다. 로그인되면 "접근 권한
   관리" 화면에서 나머지 팀원을 등록한다(위 "SSO로 전환해서 로그인 검증하기"
   절의 검증 시나리오와 동일한 화면).

### F. client_id 발급 전, 로컬 로그인으로 먼저 접근 권한 등록하기

브로커에 client 등록을 신청했는데 `client_id`/`client_secret`이 아직 안 나온
경우(사내 정식 SSO 연동 서버에서 별도로 발급하는 경우가 흔함), 그동안
`AUTH_MODE=sso`의 나머지 부분(로그인 게이트, 접근 권한 관리)은 계속 개발/검증할
수 있다 — 새로 뭘 만들 필요 없이 **기존 로컬 비밀번호 로그인을 그대로 재사용**한다.

```
AUTH_MODE=sso
SSO_ALLOW_LOCAL_LOGIN=true
ADMIN_BOOTSTRAP_PASSWORD=change-me-per-environment   # 공유 서버면 반드시 기본값에서 변경
```

이렇게 설정하고 백엔드를 재기동하면 로그인 게이트 화면에 "회사 계정으로
로그인"(client_id 없으면 여전히 에러) 버튼과 함께 **"관리자 비밀번호로 로그인"**
폼이 같이 뜬다:

1. 비밀번호로 로그인(local 모드와 동일하게 `role=admin` 고정) → "접근 권한
   관리" 화면에서 실제 SSO 계정들(사번/이메일 등)을 미리 등록해둔다.
2. `client_id`/`client_secret`을 발급받으면 `.env`에 채우고, 이번엔 "회사
   계정으로 로그인" 버튼으로 실제 SSO 로그인을 시도해 방금 등록해둔 계정이
   실제로 올바른 role(admin/user)을 받는지 검증한다(위 E번 런북 그대로).
3. 검증이 끝나면 `SSO_ALLOW_LOCAL_LOGIN=false`로 되돌린다(계속 켜둬도 동작은
   하지만, 그럴 거면 비밀번호 관리에 더 신경 써야 한다 — 아래 경고 참고).

**주의**: 이 플래그는 SSO 게이트를 비밀번호로 우회하는 것과 같으므로, 본인만
접근하는 컴퓨터가 아니라 다른 사람도 닿을 수 있는 서버에서 켤 때는
`ADMIN_BOOTSTRAP_PASSWORD`를 반드시 기본값("0000")이 아닌 값으로 바꿔야 한다.

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
