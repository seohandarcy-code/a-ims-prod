

# Vue + FastAPI + Nginx 대시보드의 사내 GitHub·PDEP 전환 가이드

## 1. 문서 목적

현재 개발 중인 대시보드는 다음 기술로 구성되어 있다.

- Frontend: Vue
- Backend: FastAPI
- Reverse Proxy / Static Server: Nginx
- 개발 환경: Windows
- 향후 배포 환경: 사내 GitHub, Jenkins CI, 사내 Container Registry, PDEP/Kubernetes

이 문서는 현재 프로젝트를 사내 GitHub에 등록하고 PDEP 환경에 배포할 때 예상되는 문제, 확인해야 할 사내 정보, 필요한 기술 지식, 권장 프로젝트 구조, 사전 점검 항목을 정리한 문서다.

Claude Code는 이 문서를 기준으로 현재 프로젝트 구조와 설정을 검토하고, 필요한 파일을 생성하거나 수정할 때 참고한다.

---

# 2. 예상 배포 흐름

```text
개발자 PC
  ↓ git push
사내 GitHub
  ↓ Webhook 또는 주기적 감지
Jenkins
  ├─ Source Checkout
  ├─ Vue 의존성 설치 및 빌드
  ├─ FastAPI 의존성 설치 및 테스트
  ├─ Docker Image Build
  ├─ 보안 검사
  └─ 사내 Container Registry Push
       ↓
PDEP / Kubernetes
  ├─ Deployment 생성 또는 갱신
  ├─ Pod 실행
  ├─ Service 연결
  ├─ Ingress 또는 사내 Gateway 연결
  └─ 사용자 접속
```

각 구성요소의 역할은 다음과 같다.

| 구성요소 | 역할 |
|---|---|
| 사내 GitHub | 소스코드 및 설정 파일 버전 관리 |
| Jenkins | 빌드, 테스트, 이미지 생성, 배포 자동화 |
| 사내 Container Registry | Docker 이미지 저장 |
| PDEP / Kubernetes | 컨테이너 실행 및 운영 |
| Nginx / Ingress | 외부 요청을 Vue와 FastAPI로 라우팅 |
| ConfigMap | 일반 환경설정 관리 |
| Secret | 비밀번호, Token, 인증정보 관리 |

---

# 3. 작업 전에 반드시 확인해야 할 사내 정보

## 3.1 PDEP 프로젝트 및 Namespace 생성 방식

확인할 내용:

- PDEP 프로젝트를 직접 생성할 수 있는가
- 운영 담당자에게 생성 요청이 필요한가
- Namespace 명명 규칙이 있는가
- 개발, 검증, 운영 환경이 분리되는가
- 프로젝트별 리소스 제한이 있는가

예상 예시:

```text
dashboard-dev
dashboard-stage
dashboard-prod
```

---

## 3.2 사내 GitHub 인증 및 권한

확인할 내용:

- GitHub Enterprise 주소
- HTTPS 방식인지 SSH 방식인지
- 사내 SSO 인증 여부
- Personal Access Token 사용 여부
- Jenkins가 Repository를 읽을 권한이 있는지
- GitHub App 또는 Service Account를 사용하는지
- Branch Protection Rule이 적용되는지
- Pull Request 승인 규칙이 있는지

주의:

개발자 PC에서 Clone이 되더라도 Jenkins 계정이 Repository에 접근하지 못할 수 있다.

---

## 3.3 사내 Container Registry

확인할 내용:

- Registry 주소
- 프로젝트 또는 Repository 이름
- 로그인 방법
- Jenkins용 Credentials 발급 방식
- Image Push 권한
- PDEP의 Image Pull 권한
- Image 보존 기간
- 취약점 스캔 기준
- 허용되는 Base Image 목록

예상 이미지 이름:

```text
registry.company.local/my-team/dashboard-frontend:1.0.0
registry.company.local/my-team/dashboard-backend:1.0.0
```

---

## 3.4 Jenkins 실행 방식

확인할 내용:

- Jenkins Job을 직접 생성하는가
- 사내 표준 Pipeline Template이 있는가
- Repository 내 Jenkinsfile을 사용하는가
- Jenkins Agent의 OS와 실행 이미지
- Agent에 설치된 Node.js, Python, Java 버전
- Docker Build 명령 사용이 허용되는가
- Docker 대신 Kaniko, Buildah, Podman을 사용하는가
- 사내 npm, PyPI Repository 주소
- 보안 검사 단계
- 개발 및 운영 배포 승인 방식
- 배포 실패 알림 방식

회사 보안 정책에 따라 Jenkins에서 Docker Daemon을 직접 사용할 수 없을 수 있다.

---

## 3.5 Kubernetes 배포 방식

확인할 내용:

```text
kubectl apply
Helm
Kustomize
Argo CD
사내 PDEP UI
사내 표준 배포 Template
```

배포 방식에 따라 Repository의 `deploy` 디렉터리 구조와 Jenkinsfile이 달라진다.

---

# 4. 권장 Repository 구조

## 4.1 기본 구조

```text
dashboard-project/
├─ frontend/
│  ├─ src/
│  ├─ public/
│  ├─ package.json
│  ├─ package-lock.json
│  ├─ vite.config.js
│  ├─ Dockerfile
│  └─ .dockerignore
│
├─ backend/
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ api/
│  │  ├─ services/
│  │  └─ models/
│  ├─ tests/
│  ├─ requirements.txt
│  ├─ Dockerfile
│  └─ .dockerignore
│
├─ nginx/
│  ├─ nginx.conf
│  └─ Dockerfile
│
├─ deploy/
│  ├─ base/
│  │  ├─ deployment.yaml
│  │  ├─ service.yaml
│  │  ├─ ingress.yaml
│  │  └─ configmap.yaml
│  ├─ dev/
│  ├─ stage/
│  └─ prod/
│
├─ Jenkinsfile
├─ docker-compose.yml
├─ .gitignore
├─ .env.example
├─ README.md
└─ CHANGELOG.md
```

---

## 4.2 Helm 사용 시 예상 구조

```text
deploy/
└─ helm/
   └─ dashboard/
      ├─ Chart.yaml
      ├─ values.yaml
      ├─ values-dev.yaml
      ├─ values-stage.yaml
      ├─ values-prod.yaml
      └─ templates/
         ├─ deployment.yaml
         ├─ service.yaml
         ├─ ingress.yaml
         ├─ configmap.yaml
         └─ secret.yaml
```

---

# 5. 예상되는 주요 문제와 대응 방법

## 5.1 개발 PC에서는 실행되지만 Jenkins에서는 빌드 실패

주요 원인:

- Node.js 버전 차이
- npm 버전 차이
- Python 버전 차이
- `requirements.txt` 누락
- `package-lock.json` 누락
- Jenkins의 외부 인터넷 차단
- 사내 npm 또는 PyPI Repository 미설정
- Windows와 Linux의 경로 차이
- 파일명 대소문자 차이
- 로컬에만 설치된 패키지 의존

Linux는 파일명 대소문자를 구분한다.

```text
Dashboard.vue
dashboard.vue
```

위 두 파일은 Linux에서 서로 다른 파일이다.

권장 버전 고정:

```text
Node.js: 사내 표준 버전
Python: 사내 표준 버전
npm package: package-lock.json 기준
Python package: requirements.txt 또는 pyproject.toml 기준
```

Vue CI 빌드 권장 명령:

```bash
npm ci
npm run lint
npm run test --if-present
npm run build
```

Python Package는 버전을 명시한다.

권장:

```text
fastapi==버전
uvicorn[standard]==버전
pandas==버전
pydantic==버전
```

비권장:

```text
fastapi
uvicorn
pandas
```

---

## 5.2 사내망에서 npm 또는 pip 설치 실패

예상 오류:

```text
npm ERR! network timeout
Could not find a version that satisfies the requirement
SSL certificate verify failed
unable to get local issuer certificate
```

확인할 내용:

- 사내 npm Registry
- 사내 PyPI Repository
- Proxy 주소
- 사내 CA 인증서
- Jenkins Agent의 인증서 설치 여부
- 사내망에서 허용된 Package 목록

예상 `.npmrc`:

```ini
registry=https://npm.company.local/repository/npm-group/
strict-ssl=true
```

예상 `pip.conf`:

```ini
[global]
index-url = https://pypi.company.local/simple
```

SSL 검증을 임의로 끄는 방식보다 사내 CA 인증서를 정상 설치하는 방식을 우선한다.

---

## 5.3 Vue의 API 주소 문제

개발 환경에서 다음 코드가 있을 수 있다.

```javascript
axios.get('http://localhost:8000/api/dashboard')
```

이 코드는 운영 환경에서 문제가 된다.

브라우저 기준 `localhost`는 FastAPI Container가 아니라 사용자의 PC를 의미한다.

권장 방식:

```javascript
axios.get('/api/dashboard')
```

Nginx 또는 Ingress가 `/api` 요청을 FastAPI로 전달한다.

```nginx
location /api/ {
    proxy_pass http://backend-service:8000;
}
```

Claude Code는 프로젝트 전체에서 다음 문자열을 검색해야 한다.

```text
localhost
127.0.0.1
8000
5173
http://
https://
C:\
```

---

## 5.4 Vite 환경변수의 빌드 시점 문제

Vite 환경변수는 일반적으로 Runtime이 아니라 Build 시점에 포함된다.

```env
VITE_API_BASE_URL=/api
```

```javascript
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL
```

동일한 Docker Image를 개발, 검증, 운영 환경에서 재사용하려면 API 주소를 이미지에 고정하지 않는 것이 좋다.

가장 단순한 방식:

```text
/api
```

환경별로 주소가 달라야 한다면 Runtime Config 방식도 검토한다.

---

## 5.5 Nginx의 위치와 역할 문제

### 방식 A: Vue용 Nginx와 FastAPI 분리

```text
사용자
  ↓
Ingress
  ├─ /      → Frontend Nginx
  └─ /api   → FastAPI
```

### 방식 B: Nginx가 Vue와 FastAPI를 통합 라우팅

```text
사용자
  ↓
Nginx Pod
  ├─ Vue 정적 파일 제공
  └─ /api → FastAPI Service
```

### 방식 C: 사내 Ingress 또는 Gateway가 모두 처리

```text
사용자
  ↓
사내 Gateway / Ingress
  ├─ /      → Frontend Service
  └─ /api   → Backend Service
```

PDEP에서 공통 Ingress 또는 Gateway를 제공한다면 프로젝트의 별도 Reverse Proxy Nginx가 불필요할 수 있다.

단, Vue 정적 파일을 제공하기 위한 Nginx Container는 여전히 사용할 수 있다.

반드시 확인할 사항:

- PDEP에서 프로젝트별 Nginx가 허용되는가
- Ingress 경로 설정은 누가 관리하는가
- TLS 인증서는 누가 관리하는가
- `/api` Path Rewrite가 필요한가

---

## 5.6 Docker Compose와 Kubernetes의 차이

| Docker Compose | Kubernetes |
|---|---|
| service | Deployment + Service |
| container_name | 일반적으로 사용하지 않음 |
| ports | Service 또는 Ingress |
| volumes | Volume, PVC, ConfigMap |
| environment | ConfigMap, Secret |
| depends_on | 직접 대응 기능 없음 |
| restart | Deployment가 Pod 재생성 |
| network | Kubernetes Service DNS |

Kubernetes에는 `depends_on`이 없다.

따라서 FastAPI, Nginx, 데이터 저장소가 서로 다른 시점에 시작되어도 정상적으로 복구할 수 있어야 한다.

---

## 5.7 Health Check 미구현

FastAPI에 최소한 다음 Endpoint를 추가한다.

```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/health/live")
def liveness() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready")
def readiness() -> dict[str, str]:
    return {"status": "ready"}
```

Kubernetes 예시:

```yaml
livenessProbe:
  httpGet:
    path: /health/live
    port: 8000
  initialDelaySeconds: 20
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health/ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

차이:

- `livenessProbe`: Application이 멈췄는지 확인
- `readinessProbe`: 현재 요청을 받을 준비가 되었는지 확인

Readiness가 실패하면 Pod는 삭제되지 않고 Service 트래픽 대상에서 제외된다.

---

## 5.8 데이터 파일 경로 문제

Windows 절대 경로는 Linux Container에서 작동하지 않는다.

비권장:

```python
DATA_PATH = r"C:\dashboard\data\raw_dt_v2.dat"
```

권장:

```python
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "raw_dt_v2.dat"
```

운영 데이터라면 Docker Image 내부에 포함하지 않는 방식을 검토한다.

후보:

```text
Persistent Volume
사내 File Storage
Database
Object Storage
Data API
사내 Data Platform
```

반드시 결정해야 할 질문:

- 데이터는 누가 생성하는가
- 데이터는 얼마나 자주 갱신되는가
- 재배포 없이 데이터 갱신이 필요한가
- 여러 Pod가 동시에 읽는가
- 파일이 변경되는 동안 읽기 오류가 발생할 가능성이 있는가
- 데이터에 민감정보가 포함되는가

---

## 5.9 Container 내부 파일 저장 문제

다음 방식으로 저장한 파일은 Pod 재시작 시 사라질 수 있다.

```python
df.to_csv("/app/data/result.csv")
```

영구 저장이 필요하면 다음 중 하나가 필요하다.

```text
PersistentVolumeClaim
Database
사내 File Storage
Object Storage
외부 API
```

여러 Pod가 동시에 파일을 수정할 경우 동시성 문제도 고려해야 한다.

---

## 5.10 환경변수와 Secret 관리

GitHub에 포함하면 안 되는 정보:

```text
DB 비밀번호
API Key
Access Token
Registry 비밀번호
사내 시스템 계정
개인정보 포함 데이터
인증서 개인키
민감한 내부 접속정보
```

비권장:

```python
DB_PASSWORD = "password"
```

권장:

```python
import os

db_password = os.environ["DB_PASSWORD"]
```

일반 설정은 ConfigMap으로 관리한다.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: dashboard-config
data:
  APP_ENV: dev
  LOG_LEVEL: INFO
  DATA_PATH: /data/raw_dt_v2.dat
```

민감정보는 Kubernetes Secret 또는 사내 Vault, Secret Manager 정책을 따른다.

---

## 5.11 Image Tag를 latest만 사용하는 문제

비권장:

```text
dashboard-backend:latest
```

권장:

```text
dashboard-backend:1.0.0
dashboard-backend:20260718-153012
dashboard-backend:a8f3c21
```

Git Commit SHA 기반 Tag가 추적성에 유리하다.

```groovy
environment {
    IMAGE_TAG = "${GIT_COMMIT.take(7)}"
}
```

배포된 Image와 Git Commit을 연결할 수 있어야 한다.

---

## 5.12 CPU 및 Memory 제한 문제

PDEP 정책상 Resource 설정이 없으면 배포가 거절될 수 있다.

```yaml
resources:
  requests:
    cpu: "200m"
    memory: "256Mi"
  limits:
    cpu: "1000m"
    memory: "1Gi"
```

의미:

- `requests`: Pod 배치 시 확보해야 하는 최소 자원
- `limits`: Container가 사용할 수 있는 최대 자원

Pandas DataFrame은 원본 파일 크기보다 훨씬 많은 Memory를 사용할 수 있다.

---

## 5.13 FastAPI Worker 수 문제

운영 명령 예시:

```bash
uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4
```

각 Worker가 동일한 대용량 DataFrame을 Memory에 올리면 Worker 수만큼 Memory 사용량이 증가할 수 있다.

초기 권장:

```bash
uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 1
```

실제 부하와 Memory를 측정한 후 Worker 수 또는 Pod 수를 조정한다.

---

## 5.14 CORS 설정 문제

개발 중 다음 설정을 사용했을 수 있다.

```python
allow_origins=["*"]
```

운영에서는 보안 정책상 거부될 수 있다.

Vue와 FastAPI를 동일 Domain에서 `/api` 상대경로로 연결하면 CORS가 필요하지 않을 수 있다.

Domain이 분리될 경우 정확한 Origin을 지정한다.

```python
allow_origins=[
    "https://dashboard.company.local",
]
```

---

## 5.15 Reverse Proxy 뒤의 FastAPI 경로 문제

예상 문제:

- Swagger URL 오류
- HTTPS 환경인데 HTTP Redirect 생성
- `/api/docs` 접근 실패
- API Prefix 누락
- 내부 Service 이름이 외부 URL에 노출
- Path Rewrite 설정 불일치

외부 URL 예시:

```text
https://dashboard.company.local/api
```

필요한 경우:

```python
app = FastAPI(root_path="/api")
```

단, Nginx 또는 Ingress가 `/api`를 제거하고 전달하는지 그대로 전달하는지에 따라 설정이 달라진다.

---

## 5.16 한글, 인코딩, Font 문제

확인 항목:

- CSV 또는 DAT 파일이 UTF-8인지 CP949인지
- Linux Container에 필요한 한글 Font가 있는지
- Chart 이미지 또는 PDF 생성 기능이 있는지
- 파일명에 한글이 포함되어 있는지
- Nginx와 FastAPI Response Header의 Charset

CP949 데이터 예시:

```python
pd.read_csv(
    file_path,
    encoding="cp949",
)
```

---

## 5.17 Timezone 문제

Container 기본 Timezone은 UTC일 수 있다.

주의 대상:

- 기준연도
- 기준월 자동 계산
- 오늘 날짜
- 파일 갱신 시간
- Log 시간
- 월별 집계 기준
- Scheduler 실행 시간

Python 권장:

```python
from datetime import datetime
from zoneinfo import ZoneInfo

now = datetime.now(ZoneInfo("Asia/Seoul"))
```

---

# 6. GitHub 등록 전 확인 사항

## 6.1 권장 `.gitignore`

```gitignore
# Python
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.venv/
venv/

# Environment
.env
.env.*
!.env.example

# Vue / Node
node_modules/
dist/
.vite/

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Local and private data
data/private/
*.dat
*.xlsx
*.csv

# Credentials
*.pem
*.key
*.p12
*.jks
credentials.*
```

주의:

프로젝트에 필요한 Sample Data까지 모두 제외하면 Jenkins Test가 실패할 수 있다.

권장 분리:

```text
data/sample/sample_dashboard.csv
data/private/raw_dt_v2.dat
```

- `sample_dashboard.csv`: Git 등록 가능
- `raw_dt_v2.dat`: Git 등록 금지

---

# 7. README 필수 항목

```markdown
# 프로젝트 개요

## 시스템 구성

## Architecture

## 디렉터리 구조

## 로컬 실행 방법

## Docker 실행 방법

## 환경변수 목록

## Jenkins Pipeline 설명

## PDEP 배포 방법

## 접속 URL

## Health Check URL

## Log 확인 방법

## 장애 대응 방법

## Rollback 방법

## 담당 조직 및 담당자
```

환경변수 표 예시:

| 변수 | 의미 | 예시 | Secret 여부 |
|---|---|---|---|
| `APP_ENV` | 실행 환경 | `dev` | 아니요 |
| `LOG_LEVEL` | 로그 수준 | `INFO` | 아니요 |
| `DATA_PATH` | 데이터 경로 | `/data/raw.dat` | 아니요 |
| `DB_URL` | DB 주소 | 비공개 | 예 |
| `DB_PASSWORD` | DB 비밀번호 | 비공개 | 예 |

---

# 8. Jenkins Pipeline 예상 구조

아래 코드는 개념 예시이며 실제 사내 표준에 맞게 수정해야 한다.

```groovy
pipeline {
    agent any

    environment {
        REGISTRY = 'registry.company.local'
        PROJECT = 'dashboard'
        IMAGE_TAG = "${BUILD_NUMBER}"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Frontend Install') {
            steps {
                dir('frontend') {
                    sh 'npm ci'
                }
            }
        }

        stage('Frontend Test') {
            steps {
                dir('frontend') {
                    sh 'npm run lint'
                    sh 'npm run test --if-present'
                }
            }
        }

        stage('Frontend Build') {
            steps {
                dir('frontend') {
                    sh 'npm run build'
                }
            }
        }

        stage('Backend Install') {
            steps {
                dir('backend') {
                    sh '''
                        python -m venv .venv
                        . .venv/bin/activate
                        pip install -r requirements.txt
                    '''
                }
            }
        }

        stage('Backend Test') {
            steps {
                dir('backend') {
                    sh '''
                        . .venv/bin/activate
                        pytest
                    '''
                }
            }
        }

        stage('Docker Build') {
            steps {
                sh '''
                    docker build \
                      -t ${REGISTRY}/${PROJECT}/frontend:${IMAGE_TAG} \
                      frontend

                    docker build \
                      -t ${REGISTRY}/${PROJECT}/backend:${IMAGE_TAG} \
                      backend
                '''
            }
        }

        stage('Image Push') {
            steps {
                sh '''
                    docker push \
                      ${REGISTRY}/${PROJECT}/frontend:${IMAGE_TAG}

                    docker push \
                      ${REGISTRY}/${PROJECT}/backend:${IMAGE_TAG}
                '''
            }
        }

        stage('Deploy Dev') {
            steps {
                sh '''
                    kubectl set image \
                      deployment/dashboard-frontend \
                      frontend=${REGISTRY}/${PROJECT}/frontend:${IMAGE_TAG}

                    kubectl set image \
                      deployment/dashboard-backend \
                      backend=${REGISTRY}/${PROJECT}/backend:${IMAGE_TAG}
                '''
            }
        }
    }
}
```

사내 환경에서 변경될 가능성이 높은 항목:

```text
agent
credentials
npm registry
pip index
docker build
kaniko
registry login
security scan
kubectl
helm
deployment approval
notification
```

---

# 9. 권장 Branch 전략

초기에는 단순한 전략을 권장한다.

```text
main       운영 배포 가능 코드
develop    개발 통합 코드
feature/*  기능 개발
fix/*      일반 오류 수정
hotfix/*   운영 긴급 수정
```

예시:

```text
feature/dashboard-filter
feature/api-summary
fix/nginx-api-proxy
hotfix/data-path-error
```

권장 흐름:

```text
feature Branch 생성
→ 개발
→ Commit
→ Push
→ Pull Request
→ Code Review
→ develop Merge
→ 개발 PDEP 자동 배포
→ 검증
→ main Merge
→ 운영 배포 승인
```

운영 Branch에는 직접 Push하지 않고 Pull Request를 통해 Merge하도록 구성한다.

---

# 10. 최소 테스트 범위

## 10.1 FastAPI

테스트 대상:

```text
Health Check
Meta API
Summary API
Detail List API
Filter API
잘못된 Parameter 처리
데이터 파일 미존재 처리
빈 데이터 처리
Encoding 오류 처리
```

예시:

```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "alive"
```

---

## 10.2 Vue

최소 테스트 대상:

```text
npm ci 성공
Lint 성공
Production Build 성공
주요 Component Rendering
API 실패 시 Error Message
빈 데이터 처리
숫자 및 금액 Format
Filter 동작
Loading 상태
```

Pipeline 필수 명령:

```bash
npm ci
npm run lint
npm run test --if-present
npm run build
```

---

# 11. Logging 원칙

`print()`보다 Python `logging` 사용을 권장한다.

```python
import logging

logger = logging.getLogger(__name__)


def load_dashboard_data() -> None:
    logger.info("Dashboard data loading started")

    try:
        # Data processing
        logger.info("Dashboard data loading completed")
    except Exception:
        logger.exception("Dashboard data loading failed")
        raise
```

Log에 포함할 정보:

```text
요청 시간
API 경로
HTTP 상태코드
처리 시간
오류 유형
데이터 갱신 시간
배포 버전
Git Commit
Pod 이름
```

Log에 포함하면 안 되는 정보:

```text
비밀번호
Access Token
개인정보 원문
민감 데이터 전체
Authorization Header
Secret
```

가능하면 Standard Output과 Standard Error로 출력하여 PDEP의 중앙 Log System이 수집할 수 있도록 한다.

---

# 12. 배포 완료 판정 기준

Pod가 `Running`인 것만으로 배포 성공으로 판단하면 안 된다.

확인 항목:

```text
Pod Running
Readiness 정상
Liveness 정상
Service Endpoint 정상
Ingress 연결 정상
Vue 화면 정상
API 호출 정상
데이터 표시 정상
Browser Console 오류 없음
Backend Log 오류 없음
기존 기능 회귀 없음
```

---

# 13. Rollback 방법

Kubernetes Rollout 방식:

```bash
kubectl rollout history deployment/dashboard-backend
kubectl rollout undo deployment/dashboard-backend
```

이전 Image 지정 방식:

```bash
kubectl set image \
  deployment/dashboard-backend \
  backend=registry.company.local/dashboard/backend:a8f3c21
```

Rollback을 위해 반드시 다음이 관리되어야 한다.

- Git Commit
- Docker Image Tag
- Jenkins Build Number
- 배포 시간
- 배포 환경
- 변경 내용
- 이전 정상 버전

---

# 14. 현재 프로젝트에서 우선 확인해야 할 위험 요소

## 14.1 데이터 저장 위치

현재 대시보드가 DAT, CSV, XLSX 파일을 읽는다면 가장 먼저 결정해야 한다.

질문:

- 파일은 어디에서 생성되는가
- 파일은 누가 갱신하는가
- 갱신 주기는 얼마인가
- PDEP Pod에서 어떻게 접근하는가
- 여러 Pod가 동시에 읽어도 되는가
- Pod 재시작 시에도 유지되어야 하는가
- 운영 데이터에 민감정보가 있는가
- 파일 교체 중 읽기 오류를 어떻게 방지할 것인가

---

## 14.2 Vue API 주소

프로젝트 전체 검색 대상:

```text
localhost
127.0.0.1
8000
5173
http://
https://
VITE_
/api
```

권장 원칙:

```text
Vue → /api 상대경로 사용
Nginx 또는 Ingress → FastAPI Service로 전달
```

---

## 14.3 Windows 의존성

검색 대상:

```text
C:\
D:\
백슬래시 경로
PowerShell 전용 Script
BAT 파일
Windows Font
CP949
UNC 공유경로
```

비권장:

```python
path = "data\\raw_dt_v2.dat"
```

권장:

```python
from pathlib import Path

path = Path("data") / "raw_dt_v2.dat"
```

---

## 14.4 Encoding

확인:

- DAT 파일 Encoding
- CSV Encoding
- UTF-8 BOM 여부
- CP949 여부
- 한글 Column 이름
- 한글 파일명
- Linux Locale

---

## 14.5 Timezone

확인:

- Container Timezone
- PDEP Node Timezone
- Python Timezone
- Log Timezone
- 기준월 계산
- 날짜 경계 처리

권장:

```python
from datetime import datetime
from zoneinfo import ZoneInfo

now = datetime.now(ZoneInfo("Asia/Seoul"))
```

---

# 15. PDEP 전환 체크리스트

## 15.1 Source Code

- [ ] `localhost` 주소 제거
- [ ] Windows 절대경로 제거
- [ ] 경로 처리를 `pathlib`으로 통일
- [ ] `.env` Git 제외
- [ ] 비밀번호와 Token 제거
- [ ] `requirements.txt` 버전 고정
- [ ] `package-lock.json` 등록
- [ ] Logging 적용
- [ ] Health Check API 추가
- [ ] 오류 처리 추가
- [ ] 빈 데이터 처리 확인
- [ ] Encoding 확인
- [ ] Timezone 확인
- [ ] API Prefix 확인
- [ ] CORS 설정 확인

## 15.2 Docker

- [ ] Frontend Dockerfile 작성
- [ ] Backend Dockerfile 작성
- [ ] Nginx Container 필요 여부 결정
- [ ] Multi-stage Build 검토
- [ ] Non-root 사용자 실행
- [ ] `.dockerignore` 작성
- [ ] Base Image 사내 허용 여부 확인
- [ ] Image 크기 확인
- [ ] Local Docker Build 성공
- [ ] Container 재시작 후 정상 동작
- [ ] Health Check 정상
- [ ] Runtime 환경변수 적용 확인

## 15.3 GitHub

- [ ] Repository 생성
- [ ] Branch 전략 결정
- [ ] Branch Protection 확인
- [ ] Pull Request Template 확인
- [ ] Jenkins 접근 권한 확인
- [ ] Webhook 설정 확인
- [ ] 민감정보 포함 여부 검사
- [ ] README 작성
- [ ] `.gitignore` 작성
- [ ] `.env.example` 작성

## 15.4 Jenkins

- [ ] Jenkinsfile 작성
- [ ] Jenkins Agent 환경 확인
- [ ] Node.js 버전 확인
- [ ] Python 버전 확인
- [ ] npm 사내 Registry 확인
- [ ] PyPI 사내 Repository 확인
- [ ] Registry Credentials 확인
- [ ] Image Tag 규칙 결정
- [ ] Test 실패 시 배포 중단
- [ ] Security Scan 단계 확인
- [ ] 개발 및 운영 배포 조건 분리
- [ ] 배포 승인 방식 확인
- [ ] 알림 방식 확인

## 15.5 PDEP / Kubernetes

- [ ] Namespace 확인
- [ ] Deployment 작성
- [ ] Service 작성
- [ ] Ingress 또는 Gateway 확인
- [ ] ConfigMap 작성
- [ ] Secret 등록
- [ ] Resource requests/limits 설정
- [ ] Readiness Probe 설정
- [ ] Liveness Probe 설정
- [ ] 데이터 Volume 연결
- [ ] Image Pull Secret 확인
- [ ] Log 조회 방법 확인
- [ ] Monitoring 확인
- [ ] Rollback 방법 확인
- [ ] 개발 및 운영 환경 분리

---

# 16. 권장 학습 순서

## 1단계: Git 및 사내 GitHub

```text
Repository
Commit
Push
Branch
Pull Request
Merge
Tag
Release
Branch Protection
```

## 2단계: Docker

```text
Dockerfile
Build Context
Layer Cache
Multi-stage Build
Image Tag
Registry Push/Pull
Environment Variable
Volume
Non-root Container
```

## 3단계: Jenkins

```text
Jenkinsfile
Pipeline
Stage
Agent
Credentials
Artifact
Webhook
Build Parameter
Approval
Post Action
```

## 4단계: Kubernetes

```text
Pod
Deployment
Service
Ingress
ConfigMap
Secret
Namespace
Probe
Resource
PVC
Rollout
```

## 5단계: 운영

```text
Logging
Monitoring
Alert
장애 분석
Rollback
보안
권한
데이터 백업
배포 이력
```

---

# 17. 현실적인 첫 번째 완료 목표

처음부터 운영 자동화 전체를 구현하지 말고 다음 순서로 진행한다.

```text
1. 사내 GitHub에 Source Push
2. Jenkins가 Repository Checkout
3. Vue npm ci 성공
4. Vue npm run build 성공
5. FastAPI Package 설치 성공
6. FastAPI Test 성공
7. Frontend Docker Image 생성
8. Backend Docker Image 생성
9. 사내 Registry Push 성공
10. 개발 PDEP Namespace 배포
11. 내부 URL 접속 성공
12. /api 호출 성공
13. Data 표시 성공
14. Pod 재시작 후 정상 동작
15. 이전 Version Rollback 확인
```

그 이후 추가할 기능:

```text
Pull Request 자동 검증
Security Scan
운영 배포 승인
자동 Rollback
Monitoring
배포 알림
무중단 배포
Blue-Green Deployment
Canary Deployment
```

---

# 18. Claude Code가 우선 수행할 분석 작업

Claude Code는 현재 Repository를 열고 아래 항목을 순서대로 점검한다.

## 18.1 프로젝트 구조 분석

- Frontend, Backend, Nginx 디렉터리 확인
- 실행 Entry Point 확인
- Vue Build 명령 확인
- FastAPI Application 객체 위치 확인
- Nginx Routing 구조 확인
- Dockerfile 존재 여부 확인
- docker-compose.yml 존재 여부 확인

## 18.2 운영 부적합 코드 검색

다음 문자열을 전체 검색한다.

```text
localhost
127.0.0.1
C:\
D:\
8000
5173
.env
password
token
secret
api_key
```

## 18.3 의존성 분석

- Node.js 버전
- package-lock.json 존재 여부
- npm package 버전
- Python 버전
- requirements.txt 또는 pyproject.toml
- Version 미고정 Package
- Windows 전용 Package
- 사내망 설치가 어려운 Package

## 18.4 데이터 처리 분석

- 데이터 파일 위치
- 파일 경로 작성 방식
- 파일 Encoding
- 데이터 갱신 방식
- Container 내부 쓰기 여부
- 여러 Worker 또는 Pod에서의 공유 가능성
- Memory 사용 위험

## 18.5 배포 파일 생성 후보

필요한 경우 다음 파일을 생성한다.

```text
frontend/Dockerfile
frontend/.dockerignore
backend/Dockerfile
backend/.dockerignore
nginx/nginx.conf
docker-compose.yml
Jenkinsfile
deploy/deployment.yaml
deploy/service.yaml
deploy/ingress.yaml
deploy/configmap.yaml
.env.example
README.md
```

단, PDEP의 실제 배포 표준, Registry 주소, Namespace, Credentials 방식이 확인되기 전까지 사내 고유값은 Placeholder로 작성한다.

예:

```text
<INTERNAL_REGISTRY>
<PDEP_NAMESPACE>
<INGRESS_HOST>
<JENKINS_CREDENTIAL_ID>
<INTERNAL_NPM_REGISTRY>
<INTERNAL_PYPI_INDEX>
```

---

# 19. 가장 먼저 사내 담당자에게 확인할 세 가지

1. PDEP에서 프로젝트별 Nginx를 운영하는지, 사내 Ingress 또는 Gateway가 Reverse Proxy를 대신하는지
2. 대시보드가 사용하는 DAT, CSV, XLSX 운영 데이터를 어디에 저장하고 Pod에서 어떻게 접근할지
3. Jenkins의 Container Image Build 방식과 사내 Registry 주소 및 인증 방식

이 세 가지가 결정되어야 Dockerfile, Jenkinsfile, Kubernetes YAML의 최종 구조를 확정할 수 있다.
