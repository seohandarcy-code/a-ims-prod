"""테스트 간 상태 격리.

admin_auth_store/data_store는 모듈 스코프 싱글턴이라 테스트끼리 상태가
새는 것을 막기 위해 매 테스트 전후로 초기화한다. REV_FILE은 실제 개발
데이터 폴더 안에 생기므로 테스트가 끝나면 반드시 지운다.
"""
from __future__ import annotations

import pytest

from app.auth.state import admin_auth_store
from app.config import (
    CUSTOM_COLUMN_TYPES_BACKUP_FILE,
    CUSTOM_COLUMN_TYPES_FILE,
    REV_BACKUP_FILE,
    REV_FILE,
)
from app.data.store import data_store


def _clear_data_files() -> None:
    REV_FILE.unlink(missing_ok=True)
    REV_BACKUP_FILE.unlink(missing_ok=True)
    CUSTOM_COLUMN_TYPES_FILE.unlink(missing_ok=True)
    CUSTOM_COLUMN_TYPES_BACKUP_FILE.unlink(missing_ok=True)


@pytest.fixture(autouse=True)
def _reset_admin_state():
    _clear_data_files()

    with admin_auth_store._lock:
        admin_auth_store._password = "0000"
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

    _clear_data_files()
