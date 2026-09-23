"""/api/v1/admin/access-users CRUD 엔드포인트 테스트(local 모드, admin 세션 전제)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def _login(client: TestClient) -> str:
    r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "0000"})
    assert r.status_code == 200
    return r.json()["token"]


def test_requires_admin_auth():
    with TestClient(app) as client:
        r = client.get("/api/v1/admin/access-users")

    assert r.status_code == 401


def test_create_list_update_delete_flow():
    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        r = client.post(
            "/api/v1/admin/access-users",
            json={"sso_id": "u1@example.com", "name": "User One", "team": "TeamA", "is_admin": False},
            headers=headers,
        )
        assert r.status_code == 200
        assert r.json() == {"sso_id": "u1@example.com", "name": "User One", "team": "TeamA", "is_admin": False}

        r = client.get("/api/v1/admin/access-users", headers=headers)
        assert r.status_code == 200
        assert [u["sso_id"] for u in r.json()] == ["u1@example.com"]

        r = client.patch(
            "/api/v1/admin/access-users/u1@example.com",
            json={"name": "User One Renamed", "team": "TeamB", "is_admin": False},
            headers=headers,
        )
        assert r.status_code == 200
        assert r.json()["name"] == "User One Renamed"
        assert r.json()["is_admin"] is False

        r = client.delete("/api/v1/admin/access-users/u1@example.com", headers=headers)
        assert r.status_code == 200

        r = client.get("/api/v1/admin/access-users", headers=headers)
        assert r.json() == []


def test_create_duplicate_returns_409():
    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        payload = {"sso_id": "u1@example.com", "name": "User One", "team": "", "is_admin": False}
        r = client.post("/api/v1/admin/access-users", json=payload, headers=headers)
        assert r.status_code == 200

        r = client.post("/api/v1/admin/access-users", json=payload, headers=headers)
        assert r.status_code == 409


def test_delete_last_admin_returns_409():
    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        r = client.post(
            "/api/v1/admin/access-users",
            json={"sso_id": "admin1@example.com", "name": "Admin One", "team": "", "is_admin": True},
            headers=headers,
        )
        assert r.status_code == 200

        r = client.delete("/api/v1/admin/access-users/admin1@example.com", headers=headers)
        assert r.status_code == 409


def test_update_missing_returns_404():
    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        r = client.patch(
            "/api/v1/admin/access-users/nobody@example.com",
            json={"name": "X", "team": "", "is_admin": False},
            headers=headers,
        )
        assert r.status_code == 404
