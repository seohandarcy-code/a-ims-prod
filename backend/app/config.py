from __future__ import annotations

import os
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

CURRENT_YEAR = int(os.getenv("CURRENT_YEAR", "2026"))

_month_override = os.getenv("CURRENT_MONTH_OVERRIDE", "").strip()
CURRENT_MONTH_OVERRIDE: int | None = int(_month_override) if _month_override else None

_default_cors_origins = "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:8080"
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", _default_cors_origins).split(",")
    if origin.strip()
]
