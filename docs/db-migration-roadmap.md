# 데이터 계층 DB 전환 로드맵

`docs/투자관리시스템_고도화_개발계획서_v4.md` §1.3(f)/§2.4는 No-DB(파일 스냅샷) 구조를
확정하면서도 "데이터 규모가 커지거나 다중 인스턴스가 필요해지면 SQLite → PostgreSQL
순서로 전환을 검토"한다고 옵션을 남겨두었다. 2026-09-16, 그 전환을 시작하기로
결정했다. 이 문서는 전체 4단계 계획과 현재 진행 상태를 추적한다.

| 단계 | 내용 | 상태 | 상세 |
|---|---|---|---|
| 1 | SQLite 전환 | **완료 (2026-09-16)** | 아래 "1단계: SQLite" 참고 |
| 2 | PostgreSQL 전환 | **로컬 검증 완료 (2026-09-17)**, PDEP 실연동은 예정 | 아래 "2단계: PostgreSQL" 참고 |
| 3 | DevOps 환경변수/Secret 관리 문서화 | **완료 (2026-09-16)** | `docs/ENV_AND_SECRETS.md` |
| 4 | SSO 연동(로그인 게이트 + user/admin 2단계 권한) | **로컬 Keycloak 검증 완료 (2026-09-18)**, PDEP 실연동은 예정 | 아래 "4단계: SSO 연동" 참고 |

## 1단계: SQLite (완료)

- `.dat` 파일(`backend/data/base/*.dat`, 필요 시 `backend/data/data_rev/*_rev.dat`)은
  이제 **최초 시딩 소스로만** 쓰인다. DB(`backend/data/app.db`)가 비어있을 때만
  자동으로 1회 시딩되고, 이후로는 이 파일들을 다시 읽지 않는다(`backend/app/db/seed.py`).
- 이후 모든 읽기/쓰기는 `DATABASE_URL`(기본값 `sqlite:///backend/data/app.db`)을 통한다.
- 관리자 편집 UI/API는 변경 없음 — `backend/app/data/store.py`의 공개 인터페이스가
  그대로 유지되고, 내부 구현만 파일 I/O에서 DB 트랜잭션으로 바뀌었다.
- **운영 백업 ↔ 로컬 개발 재시딩**: `GET /api/v1/admin/export/dat`(+`/export/column-types`)로
  운영 DB의 현재 상태를 `.dat`로 내려받아, 로컬에서
  `backend/scripts/reseed_from_dat.py --file <다운로드파일> --reset`을 실행하면
  로컬 SQLite DB가 그 스냅샷 상태로 재구성된다. 두 방향(시딩/재시딩) 모두
  `app/db/seed.py`의 `replace_all_from_dataframe()` 하나를 공유해 동작이 항상 일관된다.
- 스키마: `backend/app/db/models.py` — `investment_rows`(39개 core 컬럼, 전부 TEXT),
  `custom_column_defs`/`custom_column_values`(관리자가 런타임에 추가하는 컬럼용 EAV),
  `backup_snapshot`(단일 슬롯 되돌리기용 JSON 스냅샷). Alembic 초기 마이그레이션:
  `backend/alembic/versions/0001_initial.py`.
- ORM 대신 SQLAlchemy **Core**(Table 객체)를 썼다 — 이 앱은 처음부터 끝까지 pandas
  DataFrame을 주고받는 구조라(계산 로직이 전부 `app/calc/*`에 pandas로 있음), Core의
  select()/insert() 결과를 DataFrame으로 바로 옮기는 편이 ORM 객체 매핑보다 잘 맞는다.

## 2단계: PostgreSQL

1단계에서 이미 SQLAlchemy Core + Alembic으로 만들어 둔 덕분에, 전환은 정말로
`DATABASE_URL`만 바꾸면 됐다 — 2026-09-17 로컬 PostgreSQL 14로 실제 검증 완료.

### 로컬 검증 (완료)

- Windows에 PostgreSQL 14 네이티브 설치(winget `PostgreSQL.PostgreSQL.14`), 이 프로젝트
  전용 role/database(`ims_dev`/`ims_dev`, 테스트용 `ims_dev_test`)를 별도로 생성 —
  `postgres` 슈퍼유저를 앱 접속에 그대로 쓰지 않는다.
- `backend/requirements.txt`에 `psycopg[binary]` 드라이버 추가.
- `alembic upgrade head`를 PostgreSQL 대상으로 실행 → 코드 변경 없이 4개 테이블 정상
  생성 확인(`app/db/models.py`가 전부 `Text`/`Integer`라 방언 문제 없음).
- `backend/tests/conftest.py`가 `DATABASE_URL`이 이미 설정돼 있으면 그 값을 존중하도록
  수정 — `DATABASE_URL=postgresql+psycopg://ims_dev:ims_dev_local_pw@127.0.0.1:5432/ims_dev_test pytest tests/`
  로 기존 테스트 스위트 49개를 그대로 PostgreSQL 대상으로 실행해 전부 통과 확인(평소
  `pytest tests/`는 여전히 SQLite 임시 파일을 자동으로 씀 — 기본 경험 변화 없음).
- 앱을 `backend/.env`의 `DATABASE_URL`로 PostgreSQL을 가리키게 기동 → 최초 시딩, 관리자
  로그인/행 편집/되돌리기/`export/dat` 다운로드까지 SQLite 때와 동일하게 동작 확인.
- 로컬에서 PostgreSQL로 전환해 개발하는 절차는 `README.md`의 "PostgreSQL로 전환해서
  개발하기" 절 참고.
- **환경변수/Secret 확장(2026-09-17)**: 다른 컴퓨터/서버로 옮겨갈 때를 대비해
  `backend/app/config.py`의 `_build_database_url()`이 `DATABASE_URL` 하나뿐 아니라
  `DB_HOST`/`DB_PORT`/`DB_NAME`/`DB_USER`/`DB_PASSWORD` 조합도 지원하도록 확장했다
  (둘 다 없으면 SQLite로 폴백). 또한 관리자 초기 비밀번호가 코드에 `"0000"`으로
  고정돼 있던 것을 `ADMIN_BOOTSTRAP_PASSWORD` 환경변수로 오버라이드 가능하게
  바꿨다 — 여러 서버가 전부 같은 잘 알려진 기본 비밀번호를 공유하지 않도록.
  상세는 `docs/ENV_AND_SECRETS.md`와 `README.md` "환경변수와 Secret" 절 참고.

### PDEP 실연동 (예정, 착수 전 확인/검토할 것)

- **접속 정보**: 사내 PDEP이 제공하는 PostgreSQL 인스턴스 주소/자격증명/버전
  (로컬 검증은 PostgreSQL 14 기준 — PDEP 실제 버전은 미확인,
  `<CONFIRM_WITH_PDEP_ADMIN>`). `DATABASE_URL` 전체를 Secret 하나로 받을지,
  `DB_HOST`/`DB_PORT`/`DB_NAME`은 ConfigMap + `DB_USER`/`DB_PASSWORD`만 Secret으로
  나눠 받을지는 PDEP의 Secret 관리 정책에 맞춰 고르면 된다(둘 다 코드가 이미 지원).
- **금액 컬럼 타입 최적화(선택)**: 1단계는 기존 파일 시절과 동일하게 금액 컬럼도
  TEXT로 저장해 검증/정규화 로직(`app/data/normalize.py`)을 그대로 재사용했다.
  NUMERIC으로 바꾸는 것을 후보로 검토할 수 있다(필수 아님, 로컬 검증에서도 그대로 둠).
- **Replica 정책 재검토**: No-DB/SQLite 시절 Replica=1 제약은 "파일 동시쓰기 문제
  방지"가 근거였다. PostgreSQL은 진짜 동시쓰기를 지원하므로 백엔드를
  Replica>1로 늘릴 수 있는 선택지가 생기지만, `backend/app/auth/state.py`의
  관리자 인증 상태가 여전히 프로세스 메모리 전용이라 그 부분을 먼저 해결하지
  않으면 다중 인스턴스에서 로그인 세션이 파드마다 따로 논다 — 4단계(SSO)와
  함께 재검토.
- K8s 매니페스트(PVC, CronJob 백업 등)는 `docs/투자관리시스템_고도화_개발계획서_v5.md`
  기준 infra-devops 작업 범위이며, 이번 로컬 검증에서는 건드리지 않았다.

## 3단계: DevOps 환경변수/Secret 관리 (완료)

`docs/ENV_AND_SECRETS.md` 참고 — 현재 변수 목록 + 2/4단계에서 추가될 변수를 TBD로
미리 표기해 두었다.

## 4단계: SSO 연동

`docs/투자관리시스템_고도화_개발계획서_v3.md` §2.2/`docs/투자관리시스템_고도화_개발계획서_v4.md`
§1.3(d)가 정의한 `AuthProvider`/`AUTH_MODE=local|sso` 이름을 그대로 가져다 썼다.
다만 **범위는 v3/v4 원안보다 좁다** — 개인별 계정 + `담당자` 매칭 + 행 단위 권한이라는
v3/v4 원안은 이번에도 부활시키지 않았고, `users`/`sso_identity` 같은 개인별 계정
테이블도 도입하지 않았다(1단계에서 만든 SQLite/PostgreSQL 인프라는 이 스코프에서는
딱히 추가로 쓸 일이 없다 — 인증 상태는 여전히 `backend/app/auth/state.py`의 프로세스
메모리 세션이다). **역할은 지금도 딱 2종류(`user`/`admin`)뿐**이다.

처음(2026-09-18 오전) 착수할 때는 "로그인 **수단**만 비밀번호 → OIDC로 교체하고
대시보드는 계속 공개, admin 역할만 유지"로 범위를 더 좁게 잡았었다. 같은 날
로컬 검증을 반복하면서 범위가 세 차례 더 넓어졌다 — 지금은 아래 네 가지가 모두
적용된다:

1. **대시보드 자체가 로그인 게이트 뒤에 있다**(`AUTH_MODE=sso`일 때) — 로그인하지
   않으면 화면 자체를 볼 수 없다. 이전엔 관리자 편집 화면만 게이트돼 있었다.
2. **로그인 자체가 관리자가 등록한 사람만 가능하다** — DB의 `allowed_users`
   테이블(관리자 화면 "접근 권한 관리" 탭, `backend/app/auth/access_store.py`)에
   등록돼 있어야 세션이 발급된다. IdP 인증에는 성공해도 등록이 안 돼 있으면
   거부된다(`#access_denied=1`). 등록 시 `user`(조회 전용)/`admin`(편집 가능)
   role도 함께 정해진다. (중간 단계에선 "IdP 인증 성공 = 로그인 성공, allowlist는
   role만 가름"이었는데, 사내 SSO를 직접 관리하지 않는 배포를 생각해보니 "인증
   성공 = 접근 허용"이 아니어야 한다는 쪽으로 다시 좁아졌다 — 아래 "DB 기반
   접근 제어" 참고.)
3. **사내 SSO 세션이 있으면 버튼 클릭 없이 자동으로 연계된다** — 다른 사내
   페이지 등에서 이미 로그인돼 있으면(IdP 세션이 살아있으면) 우리 앱도
   `prompt=none` 방식의 조용한 재인증으로 자동으로 로그인 상태가 된다.
4. **우측 상단에 접속자 정보(팀·이름·관리자 배지)가 표시된다** — SSO 콜백이
   `allowed_users`에서 가져온 이름/팀을 세션 발급과 함께 프론트로 넘겨준다.

`AUTH_MODE=local`(기본값)은 이 확장과 무관하게 100% 그대로다 — 대시보드 공개,
관리자 편집만 비밀번호로 게이트. local 모드는 사용자를 구분할 방법이 없어(공유
admin 비밀번호 1개) `user`/`admin` 구분 자체가 성립하지 않기 때문에, 이 기능
전체가 `AUTH_MODE=sso`일 때만 적용된다.

### DB 기반 접근 제어 (`allowed_users`, 완료, 2026-09-18)

- **스키마**: `backend/app/db/models.py`의 `allowed_users`(`sso_id` PK, `name`,
  `team`, `is_admin`, `created_at`) — `custom_column_defs`와 같은 단순 flat
  메타데이터 테이블 스타일. Alembic
  `backend/alembic/versions/0002_add_allowed_users.py`로 추가(`0001_initial.py`는
  수정 금지 관례를 따름).
- **저장소**: `backend/app/auth/access_store.py` — `DataStore`(pandas 캐시 +
  백업/버전 관리)와 성격이 달라 얽매이지 않고, `engine`을 직접 쓰는 얇은 CRUD
  함수로 분리(`get_by_sso_id`/`list_all`/`create`/`update`/`delete`/
  `upsert_bootstrap_admin`). 마지막 남은 admin을 삭제/강등하려 하면
  `LastAdminError`(409)로 막는다 — 전체 락아웃 방지.
- **브레이크글래스**: `SSO_ADMIN_ALLOWLIST`(env, Secret)에 매칭되는 계정은
  로그인할 때마다 `upsert_bootstrap_admin()`으로 admin이 보장된다 — 행이 없으면
  새로 만들고, 있으면 `is_admin=True`만 보장하고 이름/팀은 건드리지 않는다(관리자가
  화면에서 고친 값을 덮어쓰지 않기 위함). `ADMIN_BOOTSTRAP_PASSWORD`가 "재기동마다
  항상 이 값으로 리셋"되는 것과 같은 원칙 — env가 최종 안전망.
- **관리자 CRUD API**: `backend/app/api/access.py`
  (`/api/v1/admin/access-users`, `require_admin` 게이트) + 프론트
  "접근 권한 관리" 탭(`AdminAccessPanel.vue`, `AUTH_MODE=sso`일 때만 노출)에서
  등록·이름/팀/admin 여부 수정·삭제를 직접 한다.
- **클레임 매칭 키 이름 변경**: `SSO_ADMIN_CLAIM` → `SSO_USER_ID_CLAIM` — 이제
  "허용 목록과 대조하는 클레임"이 아니라 "`allowed_users.sso_id`와 대조하는
  매칭 키"라는 더 근본적인 역할이라 이름을 맞췄다(아직 배포 전이라 변경 비용 낮음).
- **왜 DB로 관리하나**: 사내 SSO는 직접 관리하지 않는 시스템이라 "IdP 인증
  성공 = 접근 허용"은 위험하다(회사 SSO 계정이 있는 누구나 조회 가능해짐).
  또한 조직/부서 정보는 표준 OIDC 클레임이 아니라 IdP마다 다르게 내려주거나
  아예 없을 수 있어(SAML/OIDC 클레임 스펙은 회사마다 다름), 이름/팀도 클레임을
  그대로 믿지 않고 관리자가 직접 입력해 DB로 관리하기로 했다. 이것도 여전히
  "누가 볼 수 있는지/누가 admin인지"만 관리하는 접근 제어이지, 투자 데이터를
  사람별로 다르게 보여주는 행 단위 권한(v3/v4 원안의 `담당자` 매칭)이 아니다.

### 로컬 검증 — SSO 로그인 게이트 전반 (완료, 2026-09-18)

- **세션 발급/검증은 로그인 수단과 무관하게 공유**: 기존 `AdminAuthStore`(세션
  발급 `issue_session(role)`/검증 `is_valid()`·`get_role()`/로그아웃)는 local이든
  sso든 그대로 재사용된다. local은 항상 `role="admin"`으로, sso는
  `allowed_users` 조회 결과로 `role`을 정해 세션을 발급한다.
- **role 기반 게이트 2종**(`backend/app/api/deps.py`): `require_admin`은 세션이
  유효하고 role이 `"admin"`이어야 통과(관리자 편집 API, 지금까지와 동일 위치).
  신규 `require_viewer`는 `AUTH_MODE=local`이면 no-op(대시보드 공개 유지),
  `sso`면 role 무관하게 유효한 세션만 요구(대시보드 조회 API 3종에 적용:
  `/meta`, `/dashboard`, `/status-detail`).
- **프로토콜**: OIDC(`authlib`). `backend/app/auth/oidc.py`가
  `SSO_ISSUER_URL`의 `.well-known/openid-configuration`을 자동 디스커버리한다.
- **로컬 테스트 IdP**: Docker 없이(이 PC엔 미설치, PostgreSQL 때와 같은 네이티브
  우선 원칙) JDK 17(winget `EclipseAdoptium.Temurin.17.JDK`) + Keycloak 26.7.4
  독립 서버 배포판(zip, GitHub 릴리스에서 직접 다운로드, `C:\tools\keycloak-26.7.4`)을
  설치해 `bin\kc.bat start-dev --http-port=8180`로 기동. Admin REST API로 realm(`ims`),
  confidential 클라이언트(`ims-backend`), 브레이크글래스 계정(`ims.admin`) +
  테스트 계정 5개(`ims.test1`~`ims.test5`)를 만들어 브라우저로 접근 제어
  생명주기 전체를 실제로 돌며 확인했다:
  1. `ims.admin` 로그인 → 브레이크글래스로 `allowed_users`에 자동 admin 등록,
     "관리자 설정" 버튼이 보이고 클릭하면 로그인 폼 없이 곧바로 "전체 데이터"
     편집 화면이 열림, 우측 상단 배지에 이름/관리자 표시 확인.
  2. 관리자 화면 "접근 권한 관리" 탭에서 `ims.test1`~`ims.test3`을 일반유저로
     등록.
  3. `ims.test1` 로그인 → 대시보드는 보이되 "관리자 설정" 버튼이 DOM에 아예
     없음, 우측 상단 배지에 팀/이름 표시(관리자 배지 없음) 확인.
  4. 미등록 계정 `ims.test4` 로그인 시도 → "등록되지 않은 계정입니다" 화면
     확인(IdP 인증에는 성공하지만 앱 세션은 발급 안 됨).
  5. 관리자가 "접근 권한 관리" 탭에서 `ims.test2`를 **삭제** → `ims.test2`로
     재로그인 시도 시 이번엔 access_denied로 바뀐 것을 확인(웹에서 삭제한 게
     실제로 로그인 차단까지 이어짐).
  6. 관리자가 `ims.test4`를 등록 → `ims.test4` 로그인 성공 확인(등록
     생명주기: 추가→로그인 가능→삭제→로그인 불가→재등록→로그인 가능, 전체
     한 바퀴 실제로 확인).
- **허용 목록은 브레이크글래스**: `SSO_ADMIN_ALLOWLIST`(콤마 구분)는 로그인 가능
  여부도, role도 직접 정하지 않는다 — 실제 로그인 허용/role은 `allowed_users`
  DB가 결정하고, 이 목록은 거기 매칭되는 계정을 로그인할 때마다 admin으로
  자동 등록/복구해주는 안전망이다(위 "DB 기반 접근 제어" 절 참고). **최초 배포
  시 반드시 한 명 이상 채워야 한다** — 안 그러면 `allowed_users`가 비어있는
  상태에서 아무도 로그인할 수 없어 관리자 화면 자체에 못 들어가는 락아웃이
  생긴다.
- **토큰 전달**: 콜백이 프론트로 리다이렉트할 때 세션 토큰(+role)을 쿼리스트링이
  아니라 URL 프래그먼트(`#token=...&role=...`)에 실어 보낸다(서버 로그/리퍼러에
  안 남음). 프론트는 "토큰은 메모리에만, 새로고침하면 로그아웃"이라는 기존
  원칙(`useAdminAuth.ts`)을 유지한 채로, 콜백 직후 1회만 그 값을 메모리에 채워
  넣고 URL에서 지운다.
- **사내 SSO 세션 자동 연계(조용한 재인증)**: 우리 세션을 쿠키 등으로 영속화하는
  대신, `prompt=none` 방식의 OIDC 재인증을 페이지 로드 시 1회 시도한다
  (`/api/v1/auth/sso/login?silent=1`, 최상위 리다이렉트 — iframe 아님, 3rd-party
  쿠키 차단의 영향을 안 받음). IdP(Keycloak) 세션이 살아있으면 로그인 폼 없이
  즉시 콜백으로 돌아와 세션을 발급받고, 없으면 `login_required`류 오류로 돌아와
  `#sso_required=1`로 리다이렉트된다 — 이때만 수동 "회사 계정으로 로그인" 게이트를
  보여주고, 자동으로 재시도하지 않는다(무한 리다이렉트 루프 방지). 로컬에서
  실제로 확인한 방법: `ims.admin`으로 한 번 로그인한 뒤 브라우저를 새로고침하면
  로그인 폼 없이 짧은 리다이렉트만 보이고 곧바로 다시 로그인 상태가 됨(Keycloak
  세션이 우리 앱 토큰과 별개로 살아있다는 뜻).
- **로그아웃 의미**: 우리 앱의 "로그아웃"은 우리 세션 토큰만 지운다. Keycloak/사내
  IdP 세션 자체는 그대로 살아있으므로, 로그아웃 직후 새로고침하면 조용한
  재인증이 곧바로 다시 로그인시킨다 — 의도된 동작으로 남겨둔다(사내 SSO
  게이트형 도구에서 흔한 동작). 완전한 로그아웃(OIDC RP-Initiated Logout,
  `end_session_endpoint` 호출)은 이번에 만들지 않았다 — 필요해지면 다음 확장
  후보.
- **중요한 부수 발견**: `backend/tests/conftest.py`가 `DATABASE_URL`은 존중하되
  (2단계 로컬 PostgreSQL 검증용) `AUTH_MODE`는 그러지 않았던 시절, 로컬
  `backend/.env`에 `AUTH_MODE=sso`를 남겨둔 채 `pytest`를 돌리면 python-dotenv가
  그 값을 그대로 읽어버려 local 모드를 전제하는 기존 테스트 38개가 한꺼번에
  깨지는 문제를 실제로 겪었다. `conftest.py`가 이제 `AUTH_MODE`를 항상 `local`로
  강제하도록 고쳐서, 로컬 `.env`에 어떤 값이 있든 테스트 스위트는 항상 결정적으로
  동작한다.
- 설치/설정 절차는 `README.md`의 "SSO로 전환해서 로그인 검증하기" 절 참고.

### 실제 SSO 브로커 연동 준비 (완료, 2026-09-23)

로컬 Keycloak 검증까지는 "직접 관리하는 IdP"였지만, 실제로는 관리하지 않는
회사 SSO 브로커에 붙게 된다는 걸 다시 점검하면서 세 가지를 보강했다:

- **`/sso/callback`에 로깅 추가**(`backend/app/api/auth.py`) — 지금까지는 로그가
  한 줄도 없어서, 낯선 브로커가 예상과 다른 클레임을 보내거나 OIDC 흐름이 실패해도
  원인을 알 방법이 없었다. 이제 (1) `SSO_USER_ID_CLAIM`에 해당하는 클레임을 못
  찾으면 **실제로 받은 클레임 키 목록**(값은 개인정보라 안 찍음), (2) 미등록
  계정의 로그인 시도 시 그 `sso_id` 값(관리자가 등록해줘야 하는 바로 그 값),
  (3) `OAuthError` 발생 시 예외 메시지, (4) 로그인 성공 시 `sso_id`/`role`을
  각각 로그로 남긴다. 실제 브로커에 처음 붙일 때는 한 번에 성공하지 않는 게
  정상이라 이 로그가 사실상 유일한 진단 수단이다.
- **`FRONTEND_BASE_URL`**(`app/config.py`, 기본값 빈 문자열) — 콜백의 프론트
  리다이렉트가 지금까지 상대경로 `/`로 고정돼 있었는데, `frontend/nginx.conf`에
  이미 "PDEP이 프론트/백엔드 도메인을 분리할 수 있다"는 전제가 남아있어서, 분리된
  순간 로그인이 깨지는 걸 막기 위해 추가했다. 비워두면 지금까지와 100% 동일.
- **`SESSION_COOKIE_SECURE`**(`app/config.py`, 기본값 `false`) — 세션 쿠키
  (OAuth state/nonce)에 Secure 플래그를 붙일지 여부. 실제 HTTPS 배포에서 켠다.

상세 절차(환경변수 체크리스트, 브로커 관리자에게 요청할 것, 실패를 전제로 한
연동 런북)는 `README.md`의 "다른 서버로 옮겨서 실제 SSO 브로커에 연동하기" 절 참고.

### PDEP 실연동 (예정, 착수 전 확인/검토할 것)

- 사내 SSO 연동이 실제로 필수/권장인지, 프로토콜이 정말 OIDC인지(SAML 등 다른
  프로토콜이면 `backend/app/auth/oidc.py`만 교체하면 되도록 이미 그 파일 하나에
  OIDC 관련 로직을 모아뒀다), 클레임 스펙(사번/이메일 등 어떤 필드를
  `allowed_users`/`SSO_ADMIN_ALLOWLIST` 대조에 쓸 수 있는지 — `SSO_USER_ID_CLAIM`으로 설정).
- 백엔드 컨테이너화/K8s 매니페스트는 아직 없다(프론트 Dockerfile만 존재) — 실제
  PDEP 배포 착수 시 별도로 준비해야 한다.
- 향후 "여러 사용자가 각자 로그인 + 개인별 권한"으로 범위를 넓히고 싶어지면, 그때
  `users`/`sso_identity` 테이블과 `담당자` 매칭을 v3/v4 원안대로 다시 설계한다(지금
  스키마가 이걸 막아두지는 않았다 — 그냥 아직 안 만들었을 뿐).
- 완전한 로그아웃(OIDC RP-Initiated Logout — `end_session_endpoint`에 `id_token_hint`를
  실어 호출)이 필요해지면 그때 추가한다. 지금은 우리 앱 로그아웃이 IdP 세션까지
  끊지 않는다(위 "로그아웃 의미" 참고).
