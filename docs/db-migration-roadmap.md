# 데이터 계층 DB 전환 로드맵

`docs/투자관리시스템_고도화_개발계획서_v4.md` §1.3(f)/§2.4는 No-DB(파일 스냅샷) 구조를
확정하면서도 "데이터 규모가 커지거나 다중 인스턴스가 필요해지면 SQLite → PostgreSQL
순서로 전환을 검토"한다고 옵션을 남겨두었다. 2026-09-16, 그 전환을 시작하기로
결정했다. 이 문서는 전체 4단계 계획과 현재 진행 상태를 추적한다.

| 단계 | 내용 | 상태 | 상세 |
|---|---|---|---|
| 1 | SQLite 전환 | **완료 (2026-09-16)** | 아래 "1단계: SQLite" 참고 |
| 2 | PostgreSQL 전환 | 예정 | 아래 "2단계: PostgreSQL(예정)" 참고 |
| 3 | DevOps 환경변수/Secret 관리 문서화 | **완료 (2026-09-16)** | `docs/ENV_AND_SECRETS.md` |
| 4 | SSO 연동 + 자체 사용자 권한 DB | 예정 | 아래 "4단계: SSO/사용자 권한 DB(예정)" 참고 |

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

## 2단계: PostgreSQL (예정)

1단계에서 이미 SQLAlchemy Core + Alembic으로 만들어 둔 덕분에, 전환은 원칙적으로
`DATABASE_URL`만 바꾸면 된다(`postgresql+psycopg://user:password@host:5432/ims`).
착수 전 확인/검토할 것:

- **접속 정보**: 사내 PDEP이 제공하는 PostgreSQL 인스턴스 주소/자격증명. 배포 시
  `DATABASE_URL` 전체를 K8s Secret으로 주입(`docs/ENV_AND_SECRETS.md` 참고).
- **드라이버**: `psycopg`(sync) 추가 설치. `sqlalchemy`/`alembic`은 이미 도입되어 있어
  추가 코드 변경 없이 대부분 동작해야 하지만, SQLite는 관대한 타입 시스템이라 실제
  전환 시 `alembic upgrade head`를 PostgreSQL 대상으로 한 번 드라이런해 컬럼
  타입(TEXT 전제)이 문제없는지 확인 필요.
- **금액 컬럼 타입 최적화(선택)**: 1단계는 기존 파일 시절과 동일하게 금액 컬럼도
  TEXT로 저장해 검증/정규화 로직(`app/data/normalize.py`)을 그대로 재사용했다.
  PostgreSQL 전환 시점에 NUMERIC으로 바꾸는 것을 후보로 검토할 수 있다(필수 아님).
- **Replica 정책 재검토**: No-DB/SQLite 시절 Replica=1 제약은 "파일 동시쓰기 문제
  방지"가 근거였다. PostgreSQL은 진짜 동시쓰기를 지원하므로 백엔드를
  Replica>1로 늘릴 수 있는 선택지가 생기지만, `backend/app/auth/state.py`의
  관리자 인증 상태가 여전히 프로세스 메모리 전용이라 그 부분을 먼저 해결하지
  않으면 다중 인스턴스에서 로그인 세션이 파드마다 따로 논다 — 4단계(SSO)와
  함께 재검토.
- K8s 매니페스트(PVC, CronJob 백업 등)는 `docs/투자관리시스템_고도화_개발계획서_v5.md`
  기준 infra-devops 작업 범위이며, 이번 1단계에서는 건드리지 않았다.

## 3단계: DevOps 환경변수/Secret 관리 (완료)

`docs/ENV_AND_SECRETS.md` 참고 — 현재 변수 목록 + 2/4단계에서 추가될 변수를 TBD로
미리 표기해 두었다.

## 4단계: SSO 연동 + 자체 사용자 권한 DB (예정)

`docs/투자관리시스템_고도화_개발계획서_v3.md` §2.2/`docs/투자관리시스템_고도화_개발계획서_v4.md`
§1.3(d)가 정의한 `AuthProvider` 추상화(`LocalFileAuthProvider`/`SSOAuthProvider`,
`AUTH_MODE=local|sso`)를 실제로 구현하는 단계. 1단계에서 만든 SQLite/PostgreSQL
인프라를 그대로 재사용해 다음을 추가한다(스키마 후보, 아직 미구현):

- `users` — 사번/표시명/역할, SSO 사용 시 최근 로그인 캐시
- `sso_identity` — SSO가 제공하는 subject/발급자 등 외부 식별자 매핑
- 기존 단일 관리자 로그인(`backend/app/auth/state.py`)은 이 단계에서 `users` 테이블의
  시드 행 하나로 치환 가능하도록, 지금 스키마 설계 시 특별히 막아둔 것은 없다.

착수 전 확인 필요(v3/v4 문서의 미해결 open question과 동일): 사내 SSO 연동이
필수/권장인지, SSO 프로토콜(OIDC/SAML 등)과 클레임 스펙.
