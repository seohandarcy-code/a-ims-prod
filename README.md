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
