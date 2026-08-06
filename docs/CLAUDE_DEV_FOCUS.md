# Claude Code 작업 지침: 지금은 애플리케이션 완성에만 집중

## 0. 이 문서의 위치

이 문서는 `CLAUDE_DEVOPS_WORKFLOW.md`(전체 로드맵)의 **Phase 0~3만 떼어내어 지금 당장 실행할 작업**으로 재구성한 것이다.

전체 로드맵(Jenkins Pipeline, Kubernetes 배포 정의, 로컬 DevOps Lab 구축)은 지금 단계에서 다루지 않는다. 이 문서가 다루는 범위는 오직 다음 하나다.

> Vue + FastAPI + Nginx 스택이 로컬 Docker Compose 환경에서 완벽하게 잘 돌아가고, 그대로 회사 GitHub에 반입해도 문제없는 깨끗한 Application Repository를 만든다.

Jenkinsfile, Kubernetes YAML, 로컬 Jenkins/Kind 실습 환경은 이 저장소와 별도로, 이후 단계에서 진행한다. Claude Code는 이번 작업에서 그 영역을 건드리지 않는다.

---

## 1. 핵심 원칙 (반드시 지킬 것)

1. **지금은 애플리케이션 동작 완성이 유일한 목표다.** Dockerfile은 로컬 실행이 되는 최소 수준으로만 유지하고, Jenkins/Kubernetes 관련 파일은 이번 작업 범위에 포함하지 않는다.
2. **Dockerfile을 정교하게 최적화하지 않는다.** 사내 PDEP 플랫폼이 CI 단계에서 Dockerfile을 템플릿 기반으로 자동 생성하거나 표준 형식을 요구할 가능성이 있다. 그 형식이 확인되기 전까지, Dockerfile은 "docker compose로 로컬 실행이 되는 정도"면 충분하다. 과도한 멀티스테이지 최적화, non-root 세팅 등은 나중에 PDEP 요구사항을 확인한 뒤 추가한다.
3. **회사 반입 가능성을 해치는 요소를 만들지 않는다.** localhost 하드코딩, Windows 절대경로, 실제 Secret 값, 개인 PC 종속 설정은 절대 넣지 않는다.
4. **추측하지 않는다.** 사내 Registry 주소, PDEP Namespace, Credential ID 등은 알 수 없으므로 Placeholder(`<CONFIRM_WITH_PDEP_ADMIN>` 등)로 남긴다.
5. **작업 전 분석 → 계획 제시 → 승인 후 실행** 순서를 지킨다. 코드를 먼저 대규모로 바꾸지 않는다.

---

## 1-1. 기존 산출물과의 관계 (이 저장소 한정 예외 조항)

이 저장소에는 이전 라운드(사내 PDEP 반입 준비 Phase 1~6)에서 이미 만들어진
`Jenkinsfile`, `deploy/`(K8s manifest), 최적화된 `backend/Dockerfile`·`nginx/Dockerfile`이
존재한다. 이번 Phase 0~3 작업에서는:

- 위 파일들을 **삭제하지 않고 그대로 둔다** (되돌리는 것도 아님 — 그냥 건드리지 않음).
- 하지만 **더 이상 갱신하거나 참조하지 않는다.** Phase 3에서 만드는
  `docker-compose.yml`/`frontend/Dockerfile`/`backend/Dockerfile`(최소 버전)은
  기존 `backend/Dockerfile`을 덮어쓰지 않고 별도로 관리하거나, 최소 버전으로
  교체가 필요하면 그 시점에 사용자에게 먼저 확인한다.
- README에는 "Jenkinsfile/deploy/는 이전 라운드 산출물이며 이번 Phase에서는
  갱신 대상이 아니다"라는 안내를 추가한다.
- PDEP 실제 규격이 확인되면, 그때 이 파일들을 최신 애플리케이션 구조에 맞춰
  다시 검토한다 (지금은 참고용 초안으로만 남긴다).

---

## 2. 지금 작업할 저장소 구조

```text
dashboard-app/
├─ frontend/
│  ├─ src/
│  ├─ public/
│  ├─ package.json
│  ├─ package-lock.json
│  ├─ vite.config.js
│  ├─ Dockerfile          # 최소 수준, 로컬 실행 목적
│  └─ .dockerignore
│
├─ backend/
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ api/
│  │  ├─ services/
│  │  ├─ models/
│  │  └─ core/
│  ├─ tests/
│  ├─ requirements.txt
│  ├─ Dockerfile          # 최소 수준, 로컬 실행 목적
│  └─ .dockerignore
│
├─ nginx/
│  └─ nginx.conf
│
├─ sample-data/
│  └─ sample_dashboard.csv
│
├─ docs/
│  └─ CURRENT_STATE_ANALYSIS.md
│
├─ .env.example
├─ .gitignore
├─ docker-compose.yml
└─ README.md
```

이번 단계에서는 `deploy/`, `Jenkinsfile`, `scripts/verify-local.*` 는 만들지 않는다. (전체 로드맵의 이후 Phase에서 다룸)

---

## 3. 작업 순서 (Phase 0 → Phase 3만)

### Phase 0. 현재 상태 분석 (코드 수정 금지)

Claude Code가 먼저 수행:

- 현재 디렉터리 구조 파악
- Vue Entry Point / 실행 명령 확인
- FastAPI Entry Point / 실행 명령 확인
- Nginx Routing 구조 확인 (있다면)
- localhost, 127.0.0.1, Windows 절대경로 사용 위치 검색
- 환경변수/Secret 하드코딩 여부 검색
- 기존 Docker 관련 파일 유무 확인
- 데이터 파일 위치와 사용 방식 확인

결과물: `docs/CURRENT_STATE_ANALYSIS.md`

이 단계에서는 코드를 수정하지 않는다. 확실하지 않은 부분은 "확인 필요"로 남긴다.

### Phase 1. 깨끗한 Application Repository 정리

- `.gitignore` 작성/보완
- `.env.example` 작성 (실제 `.env`는 제외)
- localhost/Windows 절대경로 → 환경변수 또는 상대경로로 정리
- Vue API 호출을 `/api` 상대경로로 통일
- Python 경로를 `pathlib` 기반으로 정리
- Sample Data와 운영 Data 분리
- FastAPI에 `health/live`, `health/ready` 엔드포인트 추가
- README에 로컬 실행 방법 작성

완료 기준: 새 폴더에 clone해서 README만 보고 실행 가능해야 한다.

### Phase 2. 로컬 검증 스크립트 (선택, 있으면 좋음)

- `scripts/verify-local.sh` / `.ps1`
- 검증 항목: npm ci, lint, test, build / pip install, pytest / docker compose config 검증 / 금지 파일·의심 Secret 탐지

### Phase 3. Docker 실행 환경 (최소 수준)

포함 파일:
```text
frontend/Dockerfile
backend/Dockerfile
nginx/nginx.conf
docker-compose.yml
```

요구사항:
1. Frontend는 Production Build 사용 (`npm run build`)
2. FastAPI는 `0.0.0.0`에서 실행
3. Vue는 `/api` 상대경로로 Backend 접근
4. Docker Compose 서비스명으로 통신 (localhost 금지)
5. Secret은 이미지에 포함하지 않음
6. **Dockerfile 최적화(멀티스테이지 세부 튜닝, non-root 등)는 이번 단계에서 필수 아님** — PDEP 요구사항 확인 후 다음 단계에서 보강

완료 기준:
```powershell
docker compose build --no-cache
docker compose up -d
docker compose ps
```
- Vue 화면 정상 표시
- FastAPI Health Check 정상
- `/api` 라우팅 정상
- 컨테이너 재시작 시 정상 복구

---

## 4. 이번 단계에서 하지 않는 것 (다음 단계로 명확히 분리)

```text
Jenkinsfile 작성
Kubernetes/Helm 배포 정의 작성
로컬 Jenkins/Registry/kind 설치
PDEP 연동 (Credential, Webhook, Namespace 신청)
Dockerfile 정교화/최적화
```

이 항목들은 `CLAUDE_DEVOPS_WORKFLOW.md`의 Phase 4 이후에서, 그리고 **PDEP이 실제로 Dockerfile을 자동 생성/요구하는 방식을 확인한 뒤** 진행한다. 확인 전까지 미리 만들어두지 않는다 (이중 작업 방지).

---

## 5. Claude Code 금지사항 (동일하게 유지)

```text
실제 회사 Registry 주소 추측
실제 PDEP Namespace 추측
Jenkins Credential ID 추측
운영 Secret 생성
실제 운영 Data Git 등록
개인 Token Commit
Windows 절대경로 하드코딩
localhost 기반 Container 연결
latest Tag만 사용하는 배포 정의
검증 없이 대규모 구조 변경
```

확실하지 않은 내용은 다음처럼 표시한다.
```text
<CONFIRM_WITH_PDEP_ADMIN>
<INTERNAL_REGISTRY>
<PDEP_NAMESPACE>
```

---

## 6. 완료 기준 (이번 단계의 최종 목표)

```text
새 폴더에서 git clone 가능
.env.example 존재, 실제 Secret 미포함
npm ci 성공
npm run build 성공
pytest 성공
docker compose build 성공
docker compose up 성공, 3개 서비스 정상 동작
Health Check 성공
README만 보고 실행 가능
git status 깨끗함 (불필요 파일 없음)
```

이 기준을 통과하면 "회사 반입 가능한 애플리케이션 저장소"는 완성된 것이고, 이후 PDEP 실제 확인 결과에 맞춰 Jenkinsfile/Kubernetes 정의를 채우는 다음 단계로 넘어간다.

---

## 7. Claude Code에 처음 전달할 Prompt

```text
프로젝트 루트의 이 문서(CLAUDE_DEV_FOCUS.md)를 먼저 전체 읽어줘.

이번 작업의 범위는 Phase 0~3까지만이야.
Jenkinsfile, Kubernetes 배포 정의, 로컬 DevOps Lab 구축은 이번 작업에 포함하지 마.

먼저 Phase 0(현재 상태 분석)부터 진행해줘.
코드는 아직 수정하지 말고 다음을 분석해서 docs/CURRENT_STATE_ANALYSIS.md 초안을 작성해줘.

- 현재 디렉터리 구조
- Vue Entry Point와 Build 명령
- FastAPI Entry Point와 실행 명령
- Nginx Routing 구조 (있다면)
- Docker 관련 파일 현황
- localhost, 127.0.0.1, Windows 절대경로 사용 위치
- 환경변수와 Secret 하드코딩 가능성
- Data 파일 위치와 사용 방식
- Git에 포함하면 안 되는 파일

분석 후에는 Phase 1 작업 계획(변경 대상 파일과 이유)을 먼저 제시하고,
내가 승인하면 그때 진행해줘.
확실하지 않은 내용은 추측하지 말고 '확인 필요'로 표시해줘.
```
