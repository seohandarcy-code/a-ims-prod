"""SSO 로그인 접근 제어 목록(allowed_users) CRUD.

app/data/store.py의 DataStore(pandas DataFrame 캐시 + 백업/버전 관리)와는 성격이
달라서 거기 얹지 않고, app/db/engine.py의 engine을 직접 써서 얇은 함수로 둔다 —
투자 데이터가 아니라 "누가 로그인할 수 있는지/누가 admin인지"만 관리하는 별도
관심사다.

SSO_ADMIN_ALLOWLIST(브레이크글래스)로 들어오는 계정은 upsert_bootstrap_admin()으로
로그인할 때마다 is_admin=True를 보장받는다 — allowed_users 테이블을 잘못 건드려도
(예: 실수로 admin을 전부 지움) 환경변수에 등록된 계정은 항상 복구된다.
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.engine import engine
from app.db.models import allowed_users


@dataclass
class AllowedUser:
    sso_id: str
    name: str
    team: str
    is_admin: bool


class AllowedUserNotFoundError(RuntimeError):
    pass


class DuplicateAllowedUserError(RuntimeError):
    pass


class LastAdminError(RuntimeError):
    pass


def _row_to_user(row) -> AllowedUser:  # noqa: ANN001
    return AllowedUser(sso_id=row.sso_id, name=row.name, team=row.team, is_admin=bool(row.is_admin))


def get_by_sso_id(sso_id: str) -> AllowedUser | None:
    with engine.begin() as conn:
        row = conn.execute(select(allowed_users).where(allowed_users.c.sso_id == sso_id)).first()
    return _row_to_user(row) if row is not None else None


def list_all() -> list[AllowedUser]:
    with engine.begin() as conn:
        rows = conn.execute(select(allowed_users).order_by(allowed_users.c.sso_id)).fetchall()
    return [_row_to_user(row) for row in rows]


def create(sso_id: str, name: str, team: str, is_admin: bool) -> AllowedUser:
    now = _dt.datetime.now(_dt.timezone.utc).isoformat()
    try:
        with engine.begin() as conn:
            conn.execute(
                allowed_users.insert().values(
                    sso_id=sso_id, name=name, team=team, is_admin=is_admin, created_at=now
                )
            )
    except IntegrityError as exc:
        raise DuplicateAllowedUserError(f"이미 등록된 계정입니다: {sso_id}") from exc
    return AllowedUser(sso_id=sso_id, name=name, team=team, is_admin=is_admin)


def update(sso_id: str, name: str, team: str, is_admin: bool) -> AllowedUser:
    with engine.begin() as conn:
        existing = conn.execute(select(allowed_users).where(allowed_users.c.sso_id == sso_id)).first()
        if existing is None:
            raise AllowedUserNotFoundError(f"등록되지 않은 계정입니다: {sso_id}")

        if bool(existing.is_admin) and not is_admin:
            _assert_not_last_admin_locked(conn, exclude_sso_id=sso_id)

        conn.execute(
            allowed_users.update()
            .where(allowed_users.c.sso_id == sso_id)
            .values(name=name, team=team, is_admin=is_admin)
        )
    return AllowedUser(sso_id=sso_id, name=name, team=team, is_admin=is_admin)


def delete(sso_id: str) -> None:
    with engine.begin() as conn:
        existing = conn.execute(select(allowed_users).where(allowed_users.c.sso_id == sso_id)).first()
        if existing is None:
            raise AllowedUserNotFoundError(f"등록되지 않은 계정입니다: {sso_id}")

        if bool(existing.is_admin):
            _assert_not_last_admin_locked(conn, exclude_sso_id=sso_id)

        conn.execute(allowed_users.delete().where(allowed_users.c.sso_id == sso_id))


def _assert_not_last_admin_locked(conn, exclude_sso_id: str) -> None:  # noqa: ANN001
    """exclude_sso_id를 제외하고도 admin이 최소 1명 남는지 확인한다.

    호출 시점에 이미 exclude_sso_id가 admin이라고 가정(호출부에서 확인 후 부름).
    """
    remaining_admins = conn.execute(
        select(allowed_users.c.sso_id).where(
            allowed_users.c.is_admin.is_(True),
            allowed_users.c.sso_id != exclude_sso_id,
        )
    ).first()
    if remaining_admins is None:
        raise LastAdminError("마지막 남은 관리자는 삭제하거나 강등할 수 없습니다.")


def upsert_bootstrap_admin(sso_id: str, default_name: str) -> None:
    """SSO_ADMIN_ALLOWLIST(브레이크글래스) 계정 전용 — 로그인마다 호출된다.

    행이 없으면 admin으로 새로 만들고, 있으면 is_admin=True만 보장한다(이름/팀은
    이미 있으면 건드리지 않는다 — 관리자가 화면에서 고친 값을 덮어쓰지 않기 위함).
    """
    now = _dt.datetime.now(_dt.timezone.utc).isoformat()
    with engine.begin() as conn:
        existing = conn.execute(select(allowed_users).where(allowed_users.c.sso_id == sso_id)).first()
        if existing is None:
            conn.execute(
                allowed_users.insert().values(
                    sso_id=sso_id, name=default_name, team="", is_admin=True, created_at=now
                )
            )
        elif not bool(existing.is_admin):
            conn.execute(
                allowed_users.update().where(allowed_users.c.sso_id == sso_id).values(is_admin=True)
            )
