# 환경변수 / Secret 관리

실제 DevOps 플랫폼(PDEP, Docker/Kubernetes)에서 이 시스템을 운영한다는 전제로,
현재 사용 중인 환경변수와 향후 단계(`docs/db-migration-roadmap.md`)에서 추가될
변수를 한곳에 정리한다. 배포 시 출처 구분은
`docs/vue_fastapi_nginx_github_pdep_guide.md` §5.10/§15.5의 관례를 따른다 —
**일반 설정은 ConfigMap, 민감정보는 Secret(또는 사내 Vault/Secret Manager)**.

## Backend (`backend/.env.example`)

| 변수명 | 용도 | 기본값/예시 | Secret? | 배포 출처 | 비고 |
|---|---|---|---|---|---|
| `APP_ENV` | 실행 환경 구분 | `development` | 아니오 | ConfigMap | |
| `HOST` | 바인드 호스트 | `127.0.0.1` | 아니오 | ConfigMap | 컨테이너에서는 `0.0.0.0` |
| `PORT` | 바인드 포트 | `8000` | 아니오 | ConfigMap | |
| `DATA_DIR` | 데이터 디렉터리(PVC 마운트 경로) | `data` | 아니오 | ConfigMap | `.dat` 시딩 소스, SQLite 파일이 이 아래에 위치 |
| `CURRENT_YEAR` | 기준 연도 | `2026` | 아니오 | ConfigMap | |
| `CURRENT_MONTH_OVERRIDE` | 기준월 수동 지정(비우면 자동 추정) | (빈 값) | 아니오 | ConfigMap | 운영에서는 보통 비움 |
| `LOG_LEVEL` | 로깅 레벨 | `INFO` | 아니오 | ConfigMap | |
| `CORS_ORIGINS` | 허용 Origin(콤마 구분) | (빈 값 → 로컬 dev 기본값) | 아니오 | ConfigMap | Nginx 동일 origin 프록시 확정 시 불필요해질 수 있음 |
| `DATABASE_URL` | 데이터 계층 접속 문자열(완성된 DSN) | `sqlite:///./data/app.db` | **예** | **Secret** | 아래 "데이터 계층 접속 정보" 절 참고. 설정돼 있으면 `DB_*`보다 우선 |
| `DB_HOST` | DB 호스트 (`DATABASE_URL` 없을 때 조합용) | (빈 값) | 아니오 | ConfigMap | 값이 있어야 `DB_*` 조합 경로가 활성화됨 |
| `DB_PORT` | DB 포트 | `5432` | 아니오 | ConfigMap | 비우면 5432 |
| `DB_NAME` | DB 이름 | `ims` | 아니오 | ConfigMap | 비우면 `ims` |
| `DB_USER` | DB 사용자명 | (빈 값) | **예** | **Secret** | |
| `DB_PASSWORD` | DB 비밀번호 | (빈 값) | **예** | **Secret** | |
| `ADMIN_BOOTSTRAP_PASSWORD` | 관리자 초기 비밀번호(재기동마다 이 값으로 리셋) | (빈 값 → 기존 `"0000"`) | **예** | **Secret** | `backend/app/auth/state.py` 참고 |

### 데이터 계층 접속 정보 (`DATABASE_URL` / `DB_*`)

`backend/app/config.py`의 `_build_database_url()`이 아래 우선순위로 실제 `DATABASE_URL`
값을 결정한다(코드가 실제로 이렇게 동작함 — 2026-09-17 로컬 PostgreSQL 검증 시 확인):

1. **`DATABASE_URL`이 설정돼 있으면 그 값을 그대로 쓴다** — 나머지 `DB_*` 값은 전부
   무시된다. 로컬 개발처럼 값 하나로 충분한 경우에 쓴다. 예)
   `postgresql+psycopg://ims_dev:ims_dev_local_pw@127.0.0.1:5432/ims_dev`
2. **`DATABASE_URL`이 없고 `DB_HOST`가 설정돼 있으면**, `DB_HOST`/`DB_PORT`/`DB_NAME`/
   `DB_USER`/`DB_PASSWORD`를 조합해 DSN을 자동으로 만든다(`urllib.parse.quote_plus`로
   `DB_USER`/`DB_PASSWORD`를 URL-safe하게 인코딩하므로, 비밀번호에 특수문자가 있어도
   안전하다). 배포 환경에서 host/port/name은 ConfigMap, user/password는 Secret으로
   나눠 관리하고 싶을 때 이 방식을 쓴다 — K8s Secret은 보통 개별 키-값으로 관리하고
   비밀번호만 로테이션하는 경우가 많아, 이 방식이 실제 운영에는 더 잘 맞을 수 있다.
3. **둘 다 없으면 SQLite로 폴백**(`DATA_DIR` 아래 `app.db`) — fresh clone 시 기본값.

1단계(SQLite)에서는 `DATABASE_URL`이 자격증명을 담지 않는 파일 경로라 비민감하지만,
처음부터 **Secret으로 취급**한다 — 2단계(PostgreSQL)에서 이 값(또는 `DB_PASSWORD`)이
자격증명을 포함하게 될 때, 배포 계약(어떤 env var를 Secret에서 읽는가)을 단계 간
동일하게 유지하기 위함이다. PDEP이 완성된 DSN 하나(`DATABASE_URL`)를 선호하는지,
개별 값(`DB_*`)을 선호하는지는 별도 확인 필요 — `<CONFIRM_WITH_PDEP_ADMIN>`.

로컬 PostgreSQL 설치·role 생성 절차는 `README.md`의 "PostgreSQL로 전환해서 개발하기"
절 참고.

## Frontend (`frontend/.env.example`)

| 변수명 | 용도 | 기본값/예시 | Secret? | 배포 출처 | 비고 |
|---|---|---|---|---|---|
| `VITE_API_BASE_URL` | 백엔드 API 베이스 URL | (빈 값) | 아니오 | ConfigMap(빌드 타임) | PDEP Vue 템플릿은 `.env` 하나만 쓰고 배포 단계별로 CI가 값을 주입하는 것으로 추정(`pdep-vue-template-guide.md` §3, 미확정) |

## 향후 단계 예고 (TBD — 아직 코드에 없음)

아래는 `docs/db-migration-roadmap.md`의 4단계에서 실제로 도입될 때 이 표에
정식으로 옮겨 적을 항목이다. 지금은 이름과 방향만 예약해 둔다.

| 변수명(가안) | 단계 | 용도 | Secret? | 비고 |
|---|---|---|---|---|
| `AUTH_MODE` | 4단계 | `local`(현재 단일 관리자 로그인) / `sso` 전환 스위치 | 아니오 | `docs/투자관리시스템_고도화_개발계획서_v4.md` §1.3(d)에 개념 정의됨 |
| `SSO_ISSUER_URL` / `SSO_CLIENT_ID` / `SSO_CLIENT_SECRET` | 4단계 | SSO(OIDC 등) 연동 정보 | `SSO_CLIENT_SECRET`은 **Secret**, 나머지는 ConfigMap | 사내 SSO 프로토콜/클레임 스펙 확인 필요 |

## 원칙

- 코드에 자격증명/토큰을 하드코딩하지 않는다 — 전부 `os.environ`(backend) 또는
  `import.meta.env`(frontend, `VITE_` 접두사)로만 읽는다.
- `.env.example`에는 항상 값이 없는 키 이름만 커밋한다(`backend/.env.example`,
  `frontend/.env.example`). 실제 `.env`는 `.gitignore` 대상.
- `latest` 같은 비고정 이미지 태그를 쓰지 않는다(`docs/vue_fastapi_nginx_github_pdep_guide.md` §5.11) —
  이 문서의 직접 대상은 아니지만 배포 파이프라인 전체의 재현성과 연결되어 있어 함께 적어둔다.
- 확실하지 않은 사내 규격(Registry 주소, Namespace, Secret Manager 정책 등)은
  추측하지 않고 `<CONFIRM_WITH_PDEP_ADMIN>` 형태로 남긴다(`docs/CLAUDE_DEV_FOCUS.md` 관례 준용).
