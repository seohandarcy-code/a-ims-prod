"""테스트 간 상태 격리.

admin_auth_store/data_store는 모듈 스코프 싱글턴이라 테스트끼리 상태가 새는
것을 막기 위해 매 테스트 전후로 초기화한다. DB는 테스트 세션 전체가 공유하는
임시 SQLite 파일을 쓰고, 매 테스트 전후로 관련 테이블을 모두 비운다 —
실제 개발 DB(backend/data/app.db)는 테스트가 절대 건드리지 않는다.

DATABASE_URL이 이미 환경에 설정돼 있으면(예: 로컬 PostgreSQL 검증) 그 값을
그대로 존중한다 — 즉
    DATABASE_URL=postgresql+psycopg://ims_dev:ims_dev_local_pw@127.0.0.1:5432/ims_dev_test pytest tests/
로 실행하면 같은 테스트 스위트가 SQLite 대신 PostgreSQL을 대상으로 그대로
돌아간다(2단계 로컬 검증용). 아무것도 지정하지 않은 평소 `pytest tests/`는
지금처럼 격리된 임시 SQLite 파일을 자동으로 쓴다.

DATABASE_URL은 app 모듈이 임포트되는 시점(app/config.py가 import 시 환경변수를
읽는다)보다 먼저 설정해야 하므로, 이 파일에서 app 관련 import보다 앞서
최상단에서 설정한다.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

if "DATABASE_URL" not in os.environ:
    _TEST_DB_PATH = Path(tempfile.gettempdir()) / "a_ims_prod_test.db"
    for _suffix in ("", "-wal", "-shm"):
        Path(f"{_TEST_DB_PATH}{_suffix}").unlink(missing_ok=True)
    os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH.as_posix()}"

import pytest  # noqa: E402

from app.auth.state import DEFAULT_PASSWORD, admin_auth_store  # noqa: E402
from app.data.store import data_store  # noqa: E402
from app.db.engine import engine  # noqa: E402
from app.db.models import (  # noqa: E402
    backup_snapshot,
    custom_column_defs,
    custom_column_values,
    investment_rows,
    metadata,
)


def _reset_db() -> None:
    metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(custom_column_values.delete())
        conn.execute(custom_column_defs.delete())
        conn.execute(backup_snapshot.delete())
        conn.execute(investment_rows.delete())


@pytest.fixture(autouse=True)
def _reset_admin_state():
    _reset_db()

    with admin_auth_store._lock:
        admin_auth_store._password = DEFAULT_PASSWORD
        admin_auth_store._sessions.clear()
        admin_auth_store._fail_count = 0
        admin_auth_store._locked_until = 0.0

    data_store._raw_df = None
    data_store._df = None
    data_store._current_month = None
    data_store._current_label = None
    data_store._ready = False
    data_store._custom_column_types = {}

    yield

    _reset_db()
