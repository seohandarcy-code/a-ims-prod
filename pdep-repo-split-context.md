# vue-fastapi-nginx 프로젝트 — pdep 연동을 위한 Repo 분리 작업 컨텍스트

> ⚠️ **`pdep-vue-template-guide.md`로 대체됨.** 이 문서는 실제 PDEP 템플릿을 확인하기 전
> 추정 기반으로 작성된 초기 컨텍스트라, Dockerfile 예시(`python:3.12-slim`)나 `.env`
> 분리 방식(`.env.development`/`.env.production`) 등 일부 전제가 실제 구현(단일 `.env`,
> Python 3.10)과 다르다. 프론트엔드 이식 작업은 `pdep-vue-template-guide.md`를 기준으로
> 진행할 것 — 이 문서는 과거 논의 맥락 참고용으로만 남겨둔다.

> 이 문서는 로컬에서 개발 완료된 vue-fastapi-nginx 웹앱을 사내 DevOps 플랫폼(pdep)에
> 등록하기 위해, 기존 mono-repo 구조를 frontend/backend 별도 GitHub repo로 분리하고
> pdep/K8s 환경에 맞게 코드를 조정하는 작업의 전체 컨텍스트.
> Claude Code 작업 시 이 문서를 프로젝트 루트에 두고 참고자료로 활용.

---

## 1. 프로젝트 배경 및 목표

- **애플리케이션**: Vue(frontend) + Nginx(정적 서빙) + FastAPI(backend)
- **현재 상태**: 로컬 개발 완료, mono-repo(frontend/, backend/ 폴더 구조)로 관리 중
- **목표**: pdep(사내 DevOps 플랫폼) 등록을 위해 frontend/backend를 **별도 GitHub repo로 분리**
- **분리 이유**: 회사의 "프로덕트" 단위가 실제 빌드(이미지) 단위로 구성되며, FastAPI와 Vue+Nginx는 실행 환경이 달라 GitHub 단계부터 별도 관리 및 별도 프로덕트로 등록되어야 함
- **인프라 현황**: K8s 네임스페이스(dev/prod) 신청 완료, Service Account/RBAC 연결 완료, K8s Secret(dockerconfigjson, tls, basic-auth 등) 구성 완료

---

## 2. 전체 아키텍처 요약 (확정된 사항)

```
[Repo 구조]
github.com/my-team/my-web-frontend   (Vue + Nginx)
github.com/my-team/my-web-backend    (FastAPI)
  → 각각 독립적인 Jenkinsfile, 독립적인 pdep 프로덕트로 등록

[CI - 각 repo별 독립 실행]
GitHub push → Jenkins(pdep) webhook 감지 → lint/test → Docker 이미지 빌드
  → Nexus(이미지 레지스트리)에 push (frontend, backend 이미지 각각 별도 태그 관리)

[CD]
Nexus 이미지 → Helm(pdep 표준 Chart + values.yaml) → K8s YAML 렌더링
  → Service Account 인증으로 K8s API 전달 → 동일 네임스페이스(my-web-dev/prod) 안에
     frontend Deployment + backend Deployment 배치

[네트워크 - Host 기반 Ingress]
my-app-dev.company.com          → frontend-service
api-my-app-dev.company.com      → backend-service (nginx를 거치지 않고 직접 라우팅)

[Ops]
Prometheus/Grafana/Alertmanager + readiness/liveness probe (pdep 기본 제공)
```

---

## 3. ⚠️ 핵심 수정 필요 사항 — Repo 분리 시 반드시 반영

### 3-1. Vue의 API 호출 방식 변경 (가장 중요)

**문제**: Vue는 SPA로, API 호출 코드(`axios.get()` 등)는 **서버가 아니라 사용자 브라우저에서 실행**됨. 브라우저는 K8s 네임스페이스나 파드 내부 DNS(`backend-service`)를 전혀 알지 못하고, 오직 **공인 도메인**만 인식함. 따라서 "같은 네임스페이스 안 파드니까 자동 연결"되는 것이 아니며, 로컬 코드를 무수정으로 재사용할 수 없음.

**해결**: API 호출 base URL을 환경변수로 분리
```js
// src/api/axios.js (예시)
import axios from 'axios'

const instance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
})

export default instance
```
```
# .env.development (로컬 개발용)
VITE_API_BASE_URL=http://localhost:8000

# .env.production (K8s 배포용 - Host 기반 Ingress 도메인)
VITE_API_BASE_URL=https://api-my-app-dev.company.com
```
**작업 지시**: 기존 코드에서 `axios.get('/api/...')`, `fetch('/api/...')`처럼 상대경로/하드코딩된 API 호출이 있다면, 전부 위 구조(환경변수 기반 인스턴스)로 리팩터링할 것.

### 3-2. FastAPI CORS 설정 추가 (필수)

프론트(`my-app-dev.company.com`)와 백엔드(`api-my-app-dev.company.com`)가 서로 다른 도메인이 되므로, CORS 미설정 시 브라우저가 API 호출을 차단함.
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",              # 로컬 개발
        "https://my-app-dev.company.com",     # dev 배포
        # "https://my-app.company.com",       # prod 배포 (필요 시 추가)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 3-3. nginx.conf 단순화

Host 기반 Ingress를 쓰므로, nginx는 **정적 파일 서빙만** 담당하고 `/api` 프록시 로직은 불필요:
```nginx
server {
    listen 80;
    location / {
        root   /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;   # Vue Router history mode 대응
    }
}
```

### 3-4. 헬스체크/메트릭 엔드포인트 (Ops 대응)

pdep 모니터링 스택이 활용할 수 있도록 FastAPI에 최소한 헬스체크 엔드포인트 추가:
```python
@app.get("/health")
def health_check():
    return {"status": "ok"}
```

---

## 4. Repo 분리 작업 방법

### 방법 A: Git 히스토리 보존 (권장)
```bash
# git-filter-repo 설치
pip install git-filter-repo --break-system-packages

# frontend
git clone <원본 mono-repo 주소> my-web-frontend
cd my-web-frontend
git filter-repo --path frontend/ --path-rename frontend/:
git remote add origin https://github.com/my-team/my-web-frontend.git
git push -u origin main

# backend
git clone <원본 mono-repo 주소> my-web-backend
cd my-web-backend
git filter-repo --path backend/ --path-rename backend/:
git remote add origin https://github.com/my-team/my-web-backend.git
git push -u origin main
```

### 방법 B: 새로 시작 (히스토리 불필요 시)
```bash
mkdir my-web-frontend && cd my-web-frontend
cp -r <원본>/frontend/* .
git init && git add . && git commit -m "Initial commit"
git remote add origin https://github.com/my-team/my-web-frontend.git
git push -u origin main
# backend도 동일하게 반복
```

---

## 5. 분리 후 최종 Repo 구조

### my-web-frontend
```
my-web-frontend/
├── src/
│   └── api/axios.js          ← VITE_API_BASE_URL 사용하는 axios 인스턴스
├── .env.development
├── .env.production
├── Dockerfile                 (multi-stage: node build → nginx:alpine)
├── nginx.conf                  (정적 서빙 전용, 단순화됨)
├── Jenkinsfile                 (frontend 전용 CI 파이프라인)
└── README.md
```

### my-web-backend
```
my-web-backend/
├── main.py                     (CORS 설정 + /health 엔드포인트 포함)
├── requirements.txt
├── Dockerfile
├── Jenkinsfile                 (backend 전용 CI 파이프라인)
└── README.md
```

---

## 6. 각 repo Dockerfile (참고)

### frontend/Dockerfile
```dockerfile
FROM node:20 AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

### backend/Dockerfile
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 7. 네임스페이스/인프라 관련 — 변경 없음 (참고용 재확인)

- 네임스페이스는 repo 분리와 무관하게 그대로 유지: `my-web-dev`, `my-web-prod`
- 같은 네임스페이스 안에 frontend Deployment + backend Deployment가 계속 공존
- Service Account, K8s Secret(dockerconfigjson/tls/basic-auth) 구성은 이미 완료 상태이며 repo 분리와 무관하게 재사용

---

## 8. 아직 확인 필요한 사항

- [ ] pdep에서 "프로덕트 = 빌드(이미지) 단위"라는 이해가 맞는지, frontend/backend 각각 별도 프로덕트로 등록해야 하는지 최종 확인
- [ ] 각 repo별 Jenkinsfile을 pdep 표준 템플릿 기준으로 작성 (사내 템플릿 문법 확인 필요)
- [ ] prod 도메인 확정 시 CORS allow_origins, VITE_API_BASE_URL 값 업데이트

---

## 9. Claude Code 작업 시 체크리스트

1. 기존 mono-repo에서 frontend/backend 코드 분석
2. 위 3번 항목(API base URL 환경변수화, CORS, nginx.conf 단순화, 헬스체크 엔드포인트)을 코드에 반영
3. 방법 A 또는 B로 실제 repo 분리 수행 (히스토리 보존 여부 확인 후 진행)
4. 각 repo에 Dockerfile, Jenkinsfile 뼈대 생성
5. 분리 후 로컬에서 정상 동작 확인 (frontend .env.development로 로컬 backend 연결 테스트)
