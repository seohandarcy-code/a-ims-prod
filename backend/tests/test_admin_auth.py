"""관리자 로그인/로그아웃/비밀번호 변경 API 테스트."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.auth.state import MAX_LOGIN_ATTEMPTS
from app.main import app


def _login(client: TestClient, password: str = "0000") -> str:
    r = client.post("/api/v1/auth/login", json={"username": "admin", "password": password})
    assert r.status_code == 200
    return r.json()["token"]


def test_login_success():
    with TestClient(app) as client:
        r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "0000"})

    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["role"] == "admin"
    assert body["token"]


def test_login_wrong_password():
    with TestClient(app) as client:
        r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})

    assert r.status_code == 401


def test_login_lockout_after_max_attempts():
    with TestClient(app) as client:
        for _ in range(MAX_LOGIN_ATTEMPTS):
            r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
            assert r.status_code == 401

        r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "0000"})

    assert r.status_code == 423


def test_raw_data_requires_auth():
    with TestClient(app) as client:
        r = client.get("/api/v1/admin/raw-data")

    assert r.status_code == 401


def test_change_password_and_relogin():
    with TestClient(app) as client:
        token = _login(client)

        r = client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "0000", "new_password": "newpass"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200

        r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "0000"})
        assert r.status_code == 401

        r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "newpass"})

    assert r.status_code == 200


def test_change_password_wrong_current():
    with TestClient(app) as client:
        token = _login(client)

        r = client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "wrong", "new_password": "newpass"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert r.status_code == 400


def test_logout_invalidates_token():
    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        r = client.post("/api/v1/auth/logout", headers=headers)
        assert r.status_code == 200

        r = client.get("/api/v1/admin/raw-data", headers=headers)

    assert r.status_code == 401
