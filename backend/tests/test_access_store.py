"""allowed_users CRUD + 마지막 admin 보호 + 브레이크글래스 upsert를 검증한다."""
from __future__ import annotations

import pytest

from app.auth import access_store


def test_create_and_get():
    access_store.create("u1@example.com", "User One", "TeamA", is_admin=False)
    user = access_store.get_by_sso_id("u1@example.com")

    assert user is not None
    assert user.name == "User One"
    assert user.team == "TeamA"
    assert user.is_admin is False


def test_get_missing_returns_none():
    assert access_store.get_by_sso_id("nobody@example.com") is None


def test_create_duplicate_raises():
    access_store.create("u1@example.com", "User One", "TeamA", is_admin=False)

    with pytest.raises(access_store.DuplicateAllowedUserError):
        access_store.create("u1@example.com", "Dup", "TeamB", is_admin=False)


def test_list_all_sorted():
    access_store.create("b@example.com", "B", "", is_admin=False)
    access_store.create("a@example.com", "A", "", is_admin=False)

    users = access_store.list_all()

    assert [u.sso_id for u in users] == ["a@example.com", "b@example.com"]


def test_update_existing():
    access_store.create("u1@example.com", "User One", "TeamA", is_admin=False)

    updated = access_store.update("u1@example.com", "User One Renamed", "TeamB", is_admin=True)

    assert updated.name == "User One Renamed"
    assert updated.team == "TeamB"
    assert updated.is_admin is True


def test_update_missing_raises():
    with pytest.raises(access_store.AllowedUserNotFoundError):
        access_store.update("nobody@example.com", "X", "", is_admin=False)


def test_delete_existing():
    access_store.create("u1@example.com", "User One", "TeamA", is_admin=False)

    access_store.delete("u1@example.com")

    assert access_store.get_by_sso_id("u1@example.com") is None


def test_delete_missing_raises():
    with pytest.raises(access_store.AllowedUserNotFoundError):
        access_store.delete("nobody@example.com")


def test_cannot_delete_last_admin():
    access_store.create("admin1@example.com", "Admin One", "", is_admin=True)

    with pytest.raises(access_store.LastAdminError):
        access_store.delete("admin1@example.com")

    assert access_store.get_by_sso_id("admin1@example.com") is not None


def test_cannot_demote_last_admin():
    access_store.create("admin1@example.com", "Admin One", "", is_admin=True)

    with pytest.raises(access_store.LastAdminError):
        access_store.update("admin1@example.com", "Admin One", "", is_admin=False)


def test_can_delete_admin_when_another_admin_remains():
    access_store.create("admin1@example.com", "Admin One", "", is_admin=True)
    access_store.create("admin2@example.com", "Admin Two", "", is_admin=True)

    access_store.delete("admin1@example.com")

    assert access_store.get_by_sso_id("admin1@example.com") is None
    assert access_store.get_by_sso_id("admin2@example.com") is not None


def test_bootstrap_admin_creates_when_missing():
    access_store.upsert_bootstrap_admin("boot@example.com", default_name="Boot Admin")

    user = access_store.get_by_sso_id("boot@example.com")
    assert user is not None
    assert user.is_admin is True
    assert user.name == "Boot Admin"


def test_bootstrap_admin_restores_admin_without_touching_name_team():
    access_store.create("boot@example.com", "Custom Name", "Custom Team", is_admin=False)

    access_store.upsert_bootstrap_admin("boot@example.com", default_name="Ignored")

    user = access_store.get_by_sso_id("boot@example.com")
    assert user.is_admin is True
    assert user.name == "Custom Name"
    assert user.team == "Custom Team"


def test_bootstrap_admin_noop_when_already_admin():
    access_store.create("boot@example.com", "Boot Admin", "TeamX", is_admin=True)

    access_store.upsert_bootstrap_admin("boot@example.com", default_name="Ignored")

    user = access_store.get_by_sso_id("boot@example.com")
    assert user.name == "Boot Admin"
    assert user.team == "TeamX"
