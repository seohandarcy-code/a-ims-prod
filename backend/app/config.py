from __future__ import annotations

import os
import secrets
import urllib.parse
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / os.getenv("DATA_DIR", "data")

BASE_DIR = DATA_DIR / "base"
DATA_REV_DIR = DATA_DIR / "data_rev"

# 2026-08-04: 팀/PJT/파트 3단계 조직 계층을 도입하며 raw_2026_07.dat(29컬럼, "조직" 단일
# 레벨)에서 raw_dt_new.dat(38컬럼, 팀/PJT/파트+9개 신규 컬럼)로 전환.
# 2026-08-05: 기성(집행) 데이터 정합성 수정 + 투자완료 컬럼이 추가된 raw_dt_new2.dat(39컬럼)로
# 재전환. 이전 파일들은 롤백용으로 base/ 아래 그대로 보존한다.
# 2026-08-06: 기준월(9월)보다 미래 시점이 "이미 실적"으로 잘못 기록된 3건(NO 12/18/31)을 바로잡은
# raw_dt_new2_rev.dat(컬럼 구조 동일, 39컬럼)로 교체. 상세 내역은 data/base/DATA_CHANGES2_rev.md 참고.
# 2026-09-17: 팀명 변경("A-Infra기술팀" → "인프라AX/PI기술팀")에 따라 `팀` 컬럼 값만 치환한
# raw_dt_new3.dat로 교체(그 외 컬럼 구조/값 동일). 상세는 data/base/DATA_CHANGES3.md 참고.
BASE_FILE = BASE_DIR / "raw_dt_new3.dat"
REV_FILE = DATA_REV_DIR / f"{BASE_FILE.stem}_rev.dat"

# 커스텀 컬럼(관리자가 추가한 컬럼)의 타입을 기억하는 sidecar 메타 파일 — DB 전환 이전
# 클론에서 최초 시딩할 때만 참고한다(app/db/seed.py.seed_if_empty). 시딩 이후로는
# custom_column_defs 테이블이 이 정보를 대신한다.
CUSTOM_COLUMN_TYPES_FILE = DATA_REV_DIR / "custom_column_types.json"

# 2026-09-16: No-DB 파일 스냅샷 방식에서 SQLite(1단계)로 전환. 위 BASE_FILE/REV_FILE은
# 이제 "최초 시딩" 소스로만 쓰이고, 이후 런타임 읽기/쓰기는 전부 DATABASE_URL을 거친다.
# 2026-09-17: PostgreSQL(2단계)을 로컬에서 검증. 접속 정보는 두 가지 방식을 모두
# 지원한다 — 우선순위 순서:
#   1) DATABASE_URL이 설정돼 있으면 그 값을 그대로 쓴다(로컬 개발처럼 값 하나로
#      충분한 경우 — 사람이 완성된 DSN 문자열을 직접 관리).
#   2) DATABASE_URL이 없고 DB_HOST가 설정돼 있으면 DB_HOST/DB_PORT/DB_NAME/DB_USER/
#      DB_PASSWORD를 조합해 DSN을 만든다(실제 배포 환경처럼 ConfigMap=host/port/name,
#      Secret=user/password로 나눠 관리하고 싶은 경우 — 사람이 DSN 문자열을 직접
#      조립하지 않아도 되고, user/password는 이 코드가 URL-safe하게 인코딩한다).
#   3) 둘 다 없으면 SQLite(fresh clone 기본값)로 폴백한다.
# docs/db-migration-roadmap.md, docs/ENV_AND_SECRETS.md, README.md "환경변수/Secret" 절 참고.
def _build_database_url() -> str:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        return database_url

    db_host = os.getenv("DB_HOST", "").strip()
    if db_host:
        db_port = os.getenv("DB_PORT", "5432").strip()
        db_name = os.getenv("DB_NAME", "ims").strip()
        db_user = urllib.parse.quote_plus(os.getenv("DB_USER", "").strip())
        db_password = urllib.parse.quote_plus(os.getenv("DB_PASSWORD", "").strip())
        return f"postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    return f"sqlite:///{(DATA_DIR / 'app.db').as_posix()}"


DATABASE_URL = _build_database_url()

# 관리자 초기 비밀번호(서버 재기동 시 항상 이 값으로 리셋됨 — app/auth/state.py 참고).
# 비워두면 로컬 개발 편의를 위해 기존 기본값("0000")을 그대로 쓴다. 여러 서버에 배포할
# 때 전부 같은 잘 알려진 기본 비밀번호를 공유하지 않도록, 환경마다 Secret으로 다르게
# 주입할 수 있게 했다.
ADMIN_BOOTSTRAP_PASSWORD = os.getenv("ADMIN_BOOTSTRAP_PASSWORD", "").strip() or "0000"

# 2026-09-18: SSO 연동(4단계) — 로그인 "수단"만 local(비밀번호) <-> sso(OIDC)로
# 바꾼다. 세션 발급/검증(app/auth/state.py의 AdminAuthStore._sessions)은 두 모드가
# 그대로 공유하므로, require_admin이나 admin.py 편집 엔드포인트는 이 스위치와
# 무관하게 전혀 손대지 않는다. 범위를 "로그인 수단 교체"로 좁혔기 때문에
# users/sso_identity 같은 개인별 계정 테이블은 만들지 않는다 — 지금처럼 인증에
# 성공하면 여전히 "admin" 역할 하나만 존재한다.
# docs/db-migration-roadmap.md 4단계, docs/ENV_AND_SECRETS.md, README.md
# "SSO로 전환해서 로그인 검증하기" 절 참고.
AUTH_MODE = os.getenv("AUTH_MODE", "local").strip().lower() or "local"

SSO_ISSUER_URL = os.getenv("SSO_ISSUER_URL", "").strip()
SSO_CLIENT_ID = os.getenv("SSO_CLIENT_ID", "").strip()
SSO_CLIENT_SECRET = os.getenv("SSO_CLIENT_SECRET", "").strip()
SSO_REDIRECT_URI = os.getenv("SSO_REDIRECT_URI", "").strip()

# 브레이크글래스 admin 목록(콤마 구분, 아래 SSO_USER_ID_CLAIM 클레임 값과 대조).
# 실제 로그인 허용 여부는 이제 DB의 allowed_users 테이블(app/auth/access_store.py,
# 관리자 화면 "접근 권한 관리" 탭)이 결정한다 — 이 목록은 그 테이블을 관리자가 잘못
# 건드려도(예: 실수로 admin을 전부 지움) 로그인할 때마다 자동으로 admin 권한이
# 복구되는 최종 안전망이다. 비워두면 브레이크글래스가 없는 것이므로, 최초 배포
# 시 반드시 한 명 이상 채워야 한다(안 그러면 allowed_users가 비어있는 상태에서
# 아무도 로그인할 수 없어 관리자 화면 자체에 못 들어가는 락아웃이 생긴다).
SSO_ADMIN_ALLOWLIST = [
    item.strip() for item in os.getenv("SSO_ADMIN_ALLOWLIST", "").split(",") if item.strip()
]
# allowed_users.sso_id 및 위 브레이크글래스 목록과 대조할 클레임 이름. 표준 OIDC
# 클레임이 아니라 IdP(사내 SSO)마다 다르므로 실제 배포 전 IT팀에 확인 필요 —
# 사번/UPN 등 안정적인 고유 식별자를 쓰는 클레임으로 맞춘다.
SSO_USER_ID_CLAIM = os.getenv("SSO_USER_ID_CLAIM", "").strip() or "email"

# AUTH_MODE=sso에서도 기존 로컬 비밀번호 로그인(/login)을 부트스트랩용으로 같이
# 열어둔다 — 브로커가 SSO_CLIENT_ID를 아직 발급하지 않아 실제 SSO 로그인이
# 불가능한 개발 단계에서, 관리자가 비밀번호로 먼저 들어가 "접근 권한 관리"
# 화면에 SSO 계정들을 등록해둘 수 있게 한다(client_id가 생기면 실제 SSO
# 버튼으로 그 등록이 제대로 작동하는지 검증). 새 인증 경로를 만드는 대신 이미
# 검증된 로컬 로그인을 그대로 재사용한다. 기본값 false — 공유 서버에서 켤
# 거면 ADMIN_BOOTSTRAP_PASSWORD를 반드시 기본값("0000")에서 바꿀 것(안 그러면
# SSO 게이트를 잘 알려진 비밀번호로 그냥 우회할 수 있게 된다).
SSO_ALLOW_LOCAL_LOGIN = os.getenv("SSO_ALLOW_LOCAL_LOGIN", "").strip().lower() == "true"

# OAuth state/nonce를 담는 Starlette SessionMiddleware 서명 키. 이 세션은 로그인
# 리다이렉트가 왕복하는 짧은 시간에만 쓰이므로(로그인 자체의 세션이 아님 —
# 그건 AdminAuthStore가 별도 관리), 로컬 dev에서는 비워두면 프로세스 기동마다
# 임의 값을 생성해도 문제없다. 여러 레플리카로 운영하거나 기동 중 재시작이
# 잦다면(진행 중이던 로그인이 깨질 수 있음) 안정적인 값을 Secret으로 고정한다.
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "").strip() or secrets.token_urlsafe(32)

# 실제 HTTPS 배포에서는 반드시 true로 설정 — 세션 쿠키(OAuth state/nonce)에
# Secure 플래그를 붙여 평문 HTTP로는 전송되지 않게 한다. 로컬 http 개발 환경은
# 기본값(false)을 그대로 둔다(Secure 쿠키는 https가 아니면 브라우저가 아예
# 저장을 거부해 로그인 자체가 깨진다).
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "").strip().lower() == "true"

# 프론트/백엔드가 같은 origin이면(지금까지 전제) 비워둔다 — SSO 콜백이 상대경로
# "/#token=..."로 리다이렉트해도 문제없다. PDEP 등에서 프론트/백엔드 도메인이
# 분리되면(frontend/nginx.conf 주석 참고) 프론트의 실제 도메인을 채워야
# 콜백이 백엔드 자기 자신이 아니라 프론트로 정확히 돌아간다. 예:
# FRONTEND_BASE_URL=https://ims.company.com
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "").strip()

CURRENT_YEAR = int(os.getenv("CURRENT_YEAR", "2026"))

_month_override = os.getenv("CURRENT_MONTH_OVERRIDE", "").strip()
CURRENT_MONTH_OVERRIDE: int | None = int(_month_override) if _month_override else None

_default_cors_origins = "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:8080"
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", _default_cors_origins).split(",")
    if origin.strip()
]
