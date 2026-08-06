# 팀 투자 관리 시스템 (IMS)

Vue 3 + Vite + TypeScript frontend, FastAPI backend, Nginx reverse proxy — local Windows development setup.
계획 문서는 `docs/`, 원본 계산 로직 참고 코드는 `legacy/`를 참고한다.

## 구조
```
backend/    FastAPI app + venv(backend/.venv) + No-DB 데이터(backend/data) + tests/
frontend/   Vue 3 + Vite + TypeScript app (eslint.config.js 포함)
nginx/      nginx.conf(로컬 dev용)
scripts/    start-dev.ps1 / stop-dev.ps1
docs/       계획 문서(plan_v5 등), 디자인 리뷰 기록, 이번 단계 작업 지침(CLAUDE_DEV_FOCUS.md)
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

## Running
```powershell
powershell -ExecutionPolicy Bypass -File scripts\start-dev.ps1
```
Open http://127.0.0.1:8080 — Nginx가 `/api/*`는 FastAPI(8000)로, 나머지는 Vite dev server(5173)로 프록시한다.

```powershell
powershell -ExecutionPolicy Bypass -File scripts\stop-dev.ps1
```

## 데이터 계층
`backend/data`는 plan_v5의 No-DB 구조(base/edits/current)를 따른다. 이번 라운드는 조회 전용이라
`edits/edit_log.jsonl`은 비어 있으며, 편집 API는 다음 라운드에서 이 로그에 append하는 방식으로 붙는다.

`backend/data/base/raw_2026_07.dat`는 git에 포함되어 있다 — 목업 데이터이고 회사 정보가
없어 커밋해도 안전하며, 덕분에 fresh clone 직후 별도 파일 전달 없이 바로 실행 가능하다.

`backend/data/edits`, `backend/data/current`는 `.gitignore`에 등록되어 계속 추적하지
않는다. `edits/edit_log.jsonl`은 앱 실행 중 append되는 런타임 상태 파일이라 git으로
관리하면 편집 테스트마다 diff가 쌓이는 문제가 생기고, `current/current_dataset.dat`는
매 기동 시 base+edits를 병합해 자동 재생성되는 파생 파일이라 커밋할 필요가 없다(둘 다
없어도 앱이 스스로 만들거나 빈 상태로 처리한다).

향후 실제 회사 데이터로 교체할 때는 `base/raw_2026_07.dat`를 다시 `.gitignore`에
등록하고, 실제 배포에서는 PVC/ConfigMap 등으로 주입하는 방식으로 전환해야 한다.

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
