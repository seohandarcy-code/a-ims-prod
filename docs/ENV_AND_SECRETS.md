# 환경변수 / Secret 관리

실제 DevOps 플랫폼(PDEP, Docker/Kubernetes)에서 이 시스템을 운영한다는 전제로,
현재 사용 중인 환경변수와 향후 단계(`docs/db-migration-roadmap.md`)에서 추가될
변수를 한곳에 정리한다. 배포 시 출처 구분은
`docs/vue_fastapi_nginx_github_pdep_guide.md` §5.10/§15.5의 관례를 따른다 —
**일반 설정은 ConfigMap, 민감정보는 Secret(또는 사내 Vault/Secret Manager)**.

## Backend (`backend/.env.example`)

| 변수명 | 용도 | 기본값/예시 | Secret? | 배포 출처 | 비고 |
|---|---|---|---|---|---|
| `APP_ENV` | 실행 환경 구분(참고용) | `development` | 아니오 | ConfigMap | **코드에서 실제로 읽지 않음** — 표기만 해둔 값 |
| `HOST` | 바인드 호스트(참고용) | `127.0.0.1` | 아니오 | ConfigMap | **코드에서 실제로 읽지 않음** — 실제 바인드 주소는 `scripts/start-dev.ps1`의 uvicorn 인자가 결정. 바꾸려면 그 스크립트를 직접 고치거나 uvicorn을 수동으로 `--host`/`--port` 지정해 실행 |
| `PORT` | 바인드 포트(참고용) | `8000` | 아니오 | ConfigMap | **코드에서 실제로 읽지 않음** — 위 `HOST`와 동일 |
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
| `AUTH_MODE` | 로그인 게이트 스위치 | `local` | 아니오 | ConfigMap | `local`(대시보드 공개, 관리자 편집만 아이디/비밀번호 게이트) 또는 `sso`(대시보드 전체가 로그인 게이트, user/admin 2단계 role). 아래 "SSO 로그인" 절 참고 |
| `SESSION_SECRET_KEY` | OAuth state/nonce 세션 쿠키 서명 키(`SessionMiddleware`) | (빈 값 → 기동마다 무작위 생성) | **예** | **Secret** | `AUTH_MODE`와 무관하게 항상 로드되지만 실제로 쓰이는 건 SSO 로그인 흐름뿐. 아래 "SSO 로그인" 절 참고 |
| `SESSION_COOKIE_SECURE` | 세션 쿠키 Secure 플래그 | `false` | 아니오 | ConfigMap | 실제 HTTPS 배포에서는 `true`로 설정(안 그러면 쿠키가 평문 HTTP로도 전송 가능한 상태로 남음). `true`인데 배포가 HTTP면 브라우저가 쿠키 저장을 거부해 로그인이 깨짐 |
| `FRONTEND_BASE_URL` | SSO 콜백이 리다이렉트할 프론트 도메인 | (빈 값 → 상대경로 `/#...`) | 아니오 | ConfigMap | 프론트/백엔드가 같은 origin이면 비움. 도메인이 분리되면 프론트의 실제 도메인(`https://ims.company.com` 등)을 채워야 콜백이 백엔드 자기 자신이 아니라 프론트로 정확히 돌아감 |
| `SSO_ISSUER_URL` | OIDC 발급자(디스커버리) URL | (빈 값) | 아니오 | ConfigMap | `{값}/.well-known/openid-configuration`을 자동 조회 |
| `SSO_CLIENT_ID` | OIDC 클라이언트 ID | (빈 값) | 아니오 | ConfigMap | |
| `SSO_CLIENT_SECRET` | OIDC 클라이언트 시크릿 | (빈 값) | **예** | **Secret** | |
| `SSO_REDIRECT_URI` | IdP가 인가 코드를 돌려줄 콜백 URL | (빈 값) | 아니오 | ConfigMap | IdP 클라이언트 설정의 Redirect URI와 정확히 일치해야 함 |
| `SSO_ADMIN_ALLOWLIST` | 브레이크글래스 admin 계정 목록(콤마 구분) | (빈 값) | **예**(계정 식별자이므로) | **Secret** | 실제 로그인 허용 여부는 DB `allowed_users`가 결정 — 이 목록은 그게 비어도 항상 admin으로 복구되는 안전망. 최초 배포 시 반드시 채울 것. 아래 "SSO 로그인" 절 참고 |
| `SSO_USER_ID_CLAIM` | `allowed_users.sso_id` 및 브레이크글래스 목록과 대조할 OIDC 클레임 이름 | `email` | 아니오 | ConfigMap | 표준 OIDC 클레임 아님 — IdP마다 다르므로 IT팀 확인 필요(사번/UPN 등 권장) |

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

### SSO 로그인 (`AUTH_MODE` / `SSO_*`)

`AUTH_MODE=local`(기본값)이면 지금까지와 100% 동일하다 — 대시보드는 공개, 관리자
편집만 아이디/비밀번호로 게이트한다. `AUTH_MODE=sso`면 **대시보드 자체가 로그인
게이트 뒤에 있다** — 로그인하지 않으면 화면을 볼 수 없고, **관리자가 DB
(`allowed_users`, 관리자 화면 "접근 권한 관리" 탭)에 직접 등록한 사람만** 로그인이
허용된다(IdP 인증에 성공해도 등록 안 돼 있으면 거부됨). 등록 시 `admin`(편집
가능)/`user`(조회 전용) 2단계 role도 함께 정해진다(개인별 계정을 도입한 게 아니라
역할이 2종류로 늘어난 것, `docs/db-migration-roadmap.md` 4단계 참고). 세션
발급/검증(`backend/app/auth/state.py`)은 두 모드가 공유하므로 이 스위치 하나로만
전환된다. IdP에 이미 로그인돼 있으면(사내 다른 페이지 등) 버튼 클릭 없이
`prompt=none` 방식으로 자동 재인증된다 — 아래 README 절 참고.

**왜 DB로 관리하나**: 사내 SSO는 직접 관리하지 않는 시스템이라 "IdP 인증 성공 =
접근 허용"은 위험하다 — 회사 SSO 계정이 있는 누구나(다른 팀 포함) 자동으로 조회
권한을 갖게 된다. 그래서 관리자가 볼 수 있는 사람을 직접 등록/관리하는 방식으로
바꿨다. 또한 조직/부서 정보는 표준 OIDC 클레임이 아니라 IdP마다 다르게 내려주므로
(또는 아예 안 내려줄 수도 있음), 이름/팀도 클레임을 그대로 믿지 않고 관리자가
직접 입력해 DB로 관리한다.

- `SSO_ADMIN_ALLOWLIST`는 **브레이크글래스**다 — `allowed_users`를 잘못 건드려도
  (예: 실수로 admin을 전부 지움) 이 목록에 있는 계정은 로그인할 때마다 자동으로
  admin으로 복구된다. **최초 배포 시 반드시 한 명 이상 채워야 한다** — 안 그러면
  `allowed_users`가 비어있는 상태에서 아무도 로그인할 수 없어 관리자 화면 자체에
  못 들어가는 락아웃이 생긴다.
- `SSO_USER_ID_CLAIM`(기본 `email`)으로 `allowed_users.sso_id`와 대조할 클레임을
  고른다 — IdP가 사번 클레임을 따로 내려준다면 그 이름으로 바꾼다. 실제 배포 전
  IT팀에 어떤 클레임에 무엇이 담기는지 반드시 확인한다.
- `SESSION_SECRET_KEY`를 비워두면 프로세스가 뜰 때마다 무작위 값으로 새로 생성된다
  (로컬 개발은 이걸로 충분). 실 배포에서는 고정값을 Secret으로 반드시 넣는다 —
  안 그러면 재기동마다 진행 중이던 로그인 리다이렉트(state/nonce)가 깨지고,
  Replica가 여러 개면 파드마다 다른 키를 써서 요청이 다른 파드로 튈 때 같은 문제가
  생긴다.
- 로컬 테스트 IdP(Keycloak) 설치 절차는 `README.md`의 "SSO로 전환해서 로그인
  검증하기" 절 참고. **실제 회사 SSO 브로커에 처음 연결하는 절차**는 `README.md`의
  "다른 서버로 옮겨서 실제 SSO 브로커에 연동하기" 절 참고 — 브로커마다 클레임
  이름이 달라 처음엔 실패하는 게 정상이며, `/sso/callback`의 서버 로그(경고 시
  받은 클레임 키 목록, 거부된 `sso_id` 값)로 원인을 확인하고 `SSO_USER_ID_CLAIM`/
  `SSO_ADMIN_ALLOWLIST`를 맞춰가는 절차를 그 절에서 다룬다.

## Frontend (`frontend/.env.example`)

| 변수명 | 용도 | 기본값/예시 | Secret? | 배포 출처 | 비고 |
|---|---|---|---|---|---|
| `VITE_API_BASE_URL` | 백엔드 API 베이스 URL | (빈 값) | 아니오 | ConfigMap(빌드 타임) | PDEP Vue 템플릿은 `.env` 하나만 쓰고 배포 단계별로 CI가 값을 주입하는 것으로 추정(`pdep-vue-template-guide.md` §3, 미확정) |

## 향후 단계 예고 (TBD — 아직 코드에 없음)

`AUTH_MODE`/`SSO_*`는 위 표로 이동했다(4단계 로컬 검증 완료). 아래는 "여러
사용자가 각자 SSO로 로그인 + 개인별 권한"으로 범위를 넓히는 미래 확장 시나리오용
후보이며, 지금은 코드에 없다 — 착수하면 이 표로 옮긴다.

| 변수명(가안) | 용도 | Secret? | 비고 |
|---|---|---|---|
| (미정 — 개인별 계정 도입 시 `users`/`sso_identity` 테이블과 함께 설계) | | | `docs/db-migration-roadmap.md` 4단계 "PDEP 실연동" 절 참고 |

## 원칙

- 코드에 자격증명/토큰을 하드코딩하지 않는다 — 전부 `os.environ`(backend) 또는
  `import.meta.env`(frontend, `VITE_` 접두사)로만 읽는다.
- `.env.example`에는 항상 값이 없는 키 이름만 커밋한다(`backend/.env.example`,
  `frontend/.env.example`). 실제 `.env`는 `.gitignore` 대상.
- `latest` 같은 비고정 이미지 태그를 쓰지 않는다(`docs/vue_fastapi_nginx_github_pdep_guide.md` §5.11) —
  이 문서의 직접 대상은 아니지만 배포 파이프라인 전체의 재현성과 연결되어 있어 함께 적어둔다.
- 확실하지 않은 사내 규격(Registry 주소, Namespace, Secret Manager 정책 등)은
  추측하지 않고 `<CONFIRM_WITH_PDEP_ADMIN>` 형태로 남긴다(`docs/CLAUDE_DEV_FOCUS.md` 관례 준용).
