# PDEP Vue-K8s 템플릿 이식 가이드 (Claude Code 참조용)

> 이 문서는 PDEP이 Vue 프로덕트 생성 시 자동으로 만들어주는 GitHub repo 템플릿 구조를
> 분석하고, 로컬에서 개발한 Vue 코드를 이 템플릿에 맞게 정리·이식하기 위한 절차를 담고 있다.
> Claude Code는 코드 이식 작업 시 이 문서의 구조와 절차를 그대로 따른다.

---

## 1. PDEP이 제공하는 Vue-K8s 템플릿 구조 (확인된 원본)

```
(repo root)
├── json-server/
├── public/
├── src/
├── .env
├── .eslintignore
├── .eslintrc.js
├── .gitattributes
├── .gitignore
├── .pretierrc
├── index.html
├── tsconfig.json
└── vite.config.ts
```

### 구조 분석

| 항목 | 의미 |
|---|---|
| `index.html`, `vite.config.ts`, `tsconfig.json` | **Vite 기반 Vue + TypeScript** 프로젝트 (Vue CLI 아님) |
| `.eslintrc.js`, `.eslintignore`, `.pretierrc` | ESLint + Prettier가 이미 표준 설정으로 세팅되어 있음 → 로컬 코드 이식 시 이 규칙을 따라야 함 (임의로 다른 설정 덮어쓰지 않음) |
| `.env` (단수, `.env.development`/`.env.production` 분리 없음) | **PDEP 템플릿은 환경변수 파일을 하나만 기본 제공**. 로컬 개발에서 계획했던 `.env.development` + `.env.production` 분리 방식과 다름 → 아래 3번에서 처리 방침 정리 |
| `json-server/` | **PDEP이 프론트엔드용 로컬 목업 API 서버(json-server)를 이미 템플릿에 포함**시켜 놓음. 즉 로컬 개발 시 실제 백엔드 없이 이 목업 서버로 프론트를 개발하는 것을 전제로 한 구조임 → 지금까지 사용해온 "목업 데이터" 방식과 정확히 같은 개념이므로, 이 폴더를 그대로 활용하면 됨 |
| `src/` | 내부 세부 구조(components/views/router/store 등)는 템플릿에 강제되어 있지 않음 → Vue 표준 관례대로 구성 |

### 템플릿에 없어서 확인이 필요한 것
- `Dockerfile`, `nginx.conf` 가 템플릿에 보이지 않음 → **PDEP CI가 이미지 빌드를 자동 처리하며 Dockerfile을 자동 생성/내장하고 있을 가능성이 높음.** 로컬에서 별도로 만든 Dockerfile을 넣어야 하는지, 아니면 불필요한지 PDEP 문서/CI 로그에서 확인 필요 (5번 참고)
- `package.json`이 목록에 없지만 Vite 프로젝트이므로 당연히 존재할 것 → 실제 repo 확인 시 package.json의 기존 scripts(`dev`, `build`, `lint` 등)를 그대로 유지할 것

---

## 2. 로컬 개발 코드 → 템플릿 매핑

| 로컬에서 만든 것 | 템플릿에서의 위치 | 처리 방침 |
|---|---|---|
| Vue 컴포넌트/뷰 | `src/` 하위 | 그대로 이식, 단 ESLint/Prettier 규칙에 맞게 포맷 재정리 |
| `src/api/axios.js` | `src/api/axios.ts` | 템플릿이 TypeScript 기반이므로 `.ts`로 변환, 타입 명시 |
| 목업 데이터 로직 | `json-server/` | 기존에 계획했던 "프론트 자체 mock" 대신, PDEP이 제공하는 `json-server` 폴더 구조(보통 `db.json` + 라우트 설정)에 맞춰 목업 데이터를 이전 |
| `.env.development`, `.env.production` | `.env` (단일 파일) | 3번 참고 |
| Dockerfile, nginx.conf | (템플릿에 없음) | 5번 확인 후 결정 — 없어도 되면 폐기, 필요하면 추가 |

---

## 3. 환경변수(.env) 처리 방침 — 백엔드 URL 반영 위치

PDEP 템플릿은 `.env` 파일 하나만 제공한다. Vite는 기본적으로 `.env`, `.env.local`,
`.env.[mode]` 를 모두 지원하지만, **템플릿이 단일 `.env`만 스캐폴딩했다는 것은 PDEP CI/CD가
빌드 시점에 `.env` 값을 환경별로 주입하거나 덮어쓰는 방식일 가능성이 높다.**

### 지금 확정할 수 있는 것
- **백엔드(FastAPI) 프로덕트가 이미 배포되어 실제 URL이 발급된 상태** → 이 URL을
  `.env`의 `VITE_API_BASE_URL`에 반영한다.

```env
# .env
VITE_API_BASE_URL=<발급된 FastAPI 프로덕트의 실제 URL>
```

```ts
// src/api/axios.ts
import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL
})

export default api
```

### 로컬 개발 중 (json-server 목업 사용 시)
- json-server를 로컬에서 띄워 테스트할 때는 `.env`의 값을 json-server 주소
  (예: `http://localhost:3001`)로 임시 변경해서 사용하고,
- 실제 배포/이식 시점에는 위에서 확인한 **FastAPI 실제 URL로 교체**한다.
- 즉 `.env` 하나를 로컬 목업용 값 ↔ 실제 백엔드 URL 값으로 **상황에 따라 바꿔 쓰는 방식**이며,
  이 전환을 코드 어디에도 하드코딩하지 않고 반드시 이 `.env` 파일 값 변경만으로 처리되게 한다.

### 확인 필요 (5번과 연결)
- [ ] PDEP CI가 배포 단계(dev/prod)별로 `.env` 값을 자동으로 다른 값으로 치환/주입하는지,
      아니면 개발자가 커밋 전에 직접 값을 바꿔야 하는지 확인
- [ ] 확인되면 이 문서의 이 섹션을 업데이트

---

## 4. json-server 목업 데이터 이전 절차

1. 로컬 개발 중 사용하던 목업 데이터(JSON 형태 또는 mock 함수 반환값)를 하나의
   `db.json` 형태로 통합 정리
2. PDEP 템플릿의 `json-server/` 폴더 내부 규칙(파일명, 라우트 매핑 방식)을 실제 repo에서 확인
3. 통합한 `db.json`을 해당 규칙에 맞게 배치
4. 프론트 코드에서 목업 호출 시 사용하던 임시 함수/조건분기(`if (mock) ... else ...`)가
   있다면 전부 제거 — API 호출은 항상 `src/api/axios.ts` 하나만 거치고,
   목업이냐 실제 백엔드냐는 오직 `.env`의 `VITE_API_BASE_URL` 값 차이로만 결정되게 정리

---

## 5. 이식 절차 (단계별)

**1단계 — 템플릿 원본 확보**
- PDEP이 생성한 실제 Vue 프로덕트 repo를 clone
- `package.json`의 기존 scripts, dependencies 확인 (임의로 덮어쓰지 않기 위함)
- `json-server/` 폴더 내부 구조 확인 (db.json 위치, 실행 스크립트 확인)

**2단계 — 로컬 개발 코드 정리**
- 2번 매핑표 기준으로 로컬 코드를 템플릿 구조에 맞게 재배치
- `.js` → `.ts` 필요한 파일 변환 (tsconfig.json 기준 타입 오류 확인)
- ESLint/Prettier 실행해서 템플릿의 기존 규칙 위반 여부 확인 (`npm run lint`)

**3단계 — 목업 → 실제 백엔드 전환 준비**
- 4번 절차대로 목업 데이터를 `json-server/`로 이전
- `.env`의 `VITE_API_BASE_URL`에 실제 FastAPI URL 반영 (3번 참고)
- FastAPI 쪽에 해당 프론트 도메인이 CORS `allow_origins`에 등록되어 있는지 교차 확인
  (프론트 도메인도 PDEP 배포 후 발급되므로, 둘 다 발급된 뒤 서로의 URL을 상대방 설정에 반영)

**4단계 — 로컬 최종 검증**
- `npm run build`로 빌드 오류 없는지 확인
- `npm run dev` 상태에서 실제 FastAPI URL로 API 호출이 정상 동작하는지 확인
  (CORS 에러 발생 시 FastAPI의 allow_origins 값 재확인)

**5단계 — repo 커밋 및 PDEP 이식**
- 템플릿의 `.gitignore`, `.eslintignore`가 이미 있으므로 이를 신뢰하고,
  node_modules/dist 등이 실수로 포함되지 않았는지 `git status`로 재확인
- PDEP이 연결한 실제 GitHub repo에 push
- PDEP CI 파이프라인 실행 → 빌드/배포 정상 여부 확인

---

## 6. Claude Code 작업 지시사항 (요약)

1. Vue 프로젝트는 반드시 TypeScript(Vite) 기준으로 작성 — `.js` 아님
2. API 호출은 `src/api/axios.ts` 단일 인스턴스만 사용, `baseURL`은
   `import.meta.env.VITE_API_BASE_URL`로만 지정 (하드코딩 금지)
3. 목업 데이터는 프론트 코드 내부에 분산시키지 말고 `json-server/` 폴더의 `db.json` 방식으로 통합
4. 기존 템플릿의 `.eslintrc.js`, `.pretierrc` 설정을 절대 임의로 교체/삭제하지 않고, 그 규칙을 따름
5. `.env`는 단일 파일 기준으로 관리하되, 로컬 목업 테스트용 값과 실제 배포용 값을 전환할 때
   반드시 이 파일의 값만 바꾸는 방식으로 처리 (다른 곳에 조건분기 코드 작성 금지)
6. Dockerfile/nginx.conf가 템플릿에 없다는 점을 인지하고, 실제 repo 확인 전까지는
   임의로 추가하지 않음 (5번 "확인 필요" 항목으로 남겨둠)

---

## 7. 확인 필요 사항 (실제 repo 확보 후 업데이트할 것)

- [ ] `json-server/` 내부 실제 파일 구성(예: `db.json`, `routes.json`, 실행 스크립트)
- [ ] `.env` 값을 PDEP CI가 배포 단계별로 자동 치환하는지 여부
- [ ] Dockerfile/nginx.conf가 실제로 템플릿에 없는지, 혹은 다른 위치(예: CI 설정 내)에
      내장되어 있는지
- [ ] 프론트 프로덕트 배포 후 발급되는 실제 도메인 값 (이 값을 FastAPI의
      `FRONTEND_ORIGIN` CORS 설정에 반영해야 함)
