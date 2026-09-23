"""admin/user 2단계 role과 require_admin/require_viewer 게이트를 검증한다.

conftest.py가 AUTH_MODE를 항상 "local"로 강제하므로, sso 모드 동작을 보려면
이 파일 안에서 개별적으로 app.api.deps.AUTH_MODE(모듈 레벨 이름)를 monkeypatch한다
— app.config.AUTH_MODE를 바꿔도 이미 from-import된 이름에는 반영되지 않는다.

/sso/login·/sso/callback의 silent 재인증 흐름은 app.auth.oidc.oauth.sso(실제
Keycloak이 설정되지 않으면 존재하지 않는 속성)를 AsyncMock으로 대체해 검증한다 —
실제 리다이렉트/콜백은 로컬 Keycloak을 띄운 브라우저 테스트로 확인한다(README.md
"SSO로 전환해서 로그인 검증하기" 참고).
"""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from starlette.responses import RedirectResponse

from app.auth import access_store
from app.auth.state import admin_auth_store
from app.main import app


def test_require_admin_rejects_user_role_session():
    token, _ = admin_auth_store.issue_session("user")

    with TestClient(app) as client:
        r = client.get("/api/v1/admin/raw-data", headers={"Authorization": f"Bearer {token}"})

    assert r.status_code == 403


def test_require_admin_accepts_admin_role_session():
    token, _ = admin_auth_store.issue_session("admin")

    with TestClient(app) as client:
        r = client.get("/api/v1/admin/raw-data", headers={"Authorization": f"Bearer {token}"})

    assert r.status_code == 200


def test_dashboard_public_in_local_mode():
    with TestClient(app) as client:
        r = client.get("/api/v1/meta")

    assert r.status_code == 200


def test_require_viewer_enforced_in_sso_mode(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("app.api.deps.AUTH_MODE", "sso")

    with TestClient(app) as client:
        r = client.get("/api/v1/meta")
        assert r.status_code == 401

        token, _ = admin_auth_store.issue_session("user")
        r = client.get("/api/v1/meta", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200


def test_sso_callback_assigns_admin_role_via_breakglass_allowlist(monkeypatch: pytest.MonkeyPatch):
    """SSO_ADMIN_ALLOWLIST에 매칭되면 allowed_users에 미리 등록돼 있지 않아도
    로그인할 때마다 admin으로 자동 등록/복구된다(브레이크글래스)."""
    monkeypatch.setattr("app.api.auth.AUTH_MODE", "sso")
    monkeypatch.setattr("app.api.auth.SSO_ADMIN_ALLOWLIST", ["ims.admin@example.local"])
    monkeypatch.setattr("app.api.auth.SSO_USER_ID_CLAIM", "email")

    mock_sso = AsyncMock()
    mock_sso.authorize_access_token.return_value = {"userinfo": {"email": "ims.admin@example.local"}}
    monkeypatch.setattr("app.auth.oidc.oauth.sso", mock_sso, raising=False)

    with TestClient(app) as client:
        r = client.get("/api/v1/auth/sso/callback", follow_redirects=False)

    assert r.status_code == 307
    assert "role=admin" in r.headers["location"]
    assert access_store.get_by_sso_id("ims.admin@example.local").is_admin is True


def test_sso_callback_redirects_to_frontend_base_url_when_set(monkeypatch: pytest.MonkeyPatch):
    """프론트/백엔드가 다른 도메인이면 FRONTEND_BASE_URL을 채워 콜백이 백엔드
    자기 자신이 아니라 프론트의 실제 도메인으로 돌아가게 한다."""
    monkeypatch.setattr("app.api.auth.AUTH_MODE", "sso")
    monkeypatch.setattr("app.api.auth.SSO_ADMIN_ALLOWLIST", ["ims.admin@example.local"])
    monkeypatch.setattr("app.api.auth.SSO_USER_ID_CLAIM", "email")
    monkeypatch.setattr("app.api.auth.FRONTEND_BASE_URL", "https://ims.example.com")

    mock_sso = AsyncMock()
    mock_sso.authorize_access_token.return_value = {"userinfo": {"email": "ims.admin@example.local"}}
    monkeypatch.setattr("app.auth.oidc.oauth.sso", mock_sso, raising=False)

    with TestClient(app) as client:
        r = client.get("/api/v1/auth/sso/callback", follow_redirects=False)

    assert r.status_code == 307
    assert r.headers["location"].startswith("https://ims.example.com/#token=")


def test_sso_callback_assigns_user_role_for_registered_non_admin(monkeypatch: pytest.MonkeyPatch):
    access_store.create("someone-else@example.com", "Someone Else", "TeamX", is_admin=False)

    monkeypatch.setattr("app.api.auth.AUTH_MODE", "sso")
    monkeypatch.setattr("app.api.auth.SSO_ADMIN_ALLOWLIST", ["ims.admin@example.local"])
    monkeypatch.setattr("app.api.auth.SSO_USER_ID_CLAIM", "email")

    mock_sso = AsyncMock()
    mock_sso.authorize_access_token.return_value = {"userinfo": {"email": "someone-else@example.com"}}
    monkeypatch.setattr("app.auth.oidc.oauth.sso", mock_sso, raising=False)

    with TestClient(app) as client:
        r = client.get("/api/v1/auth/sso/callback", follow_redirects=False)

    assert r.status_code == 307
    assert "role=user" in r.headers["location"]


def test_sso_callback_rejects_unregistered_account(monkeypatch: pytest.MonkeyPatch):
    """allowed_users에 없고 브레이크글래스 목록에도 없으면, IdP 인증에 성공해도
    로그인(세션 발급) 자체가 거부된다 — access_denied로 리다이렉트."""
    monkeypatch.setattr("app.api.auth.AUTH_MODE", "sso")
    monkeypatch.setattr("app.api.auth.SSO_ADMIN_ALLOWLIST", ["ims.admin@example.local"])
    monkeypatch.setattr("app.api.auth.SSO_USER_ID_CLAIM", "email")

    mock_sso = AsyncMock()
    mock_sso.authorize_access_token.return_value = {"userinfo": {"email": "unregistered@example.com"}}
    monkeypatch.setattr("app.auth.oidc.oauth.sso", mock_sso, raising=False)

    with TestClient(app) as client:
        r = client.get("/api/v1/auth/sso/callback", follow_redirects=False)

    assert r.status_code == 307
    assert r.headers["location"] == "/#access_denied=1"


def test_sso_callback_silent_failure_redirects_to_sso_required(monkeypatch: pytest.MonkeyPatch):
    from authlib.integrations.base_client import OAuthError

    monkeypatch.setattr("app.api.auth.AUTH_MODE", "sso")

    mock_sso = AsyncMock()
    mock_sso.authorize_redirect.return_value = RedirectResponse("http://idp.example/authorize")
    mock_sso.authorize_access_token.side_effect = OAuthError("login_required")
    monkeypatch.setattr("app.auth.oidc.oauth.sso", mock_sso, raising=False)

    with TestClient(app) as client:
        login_res = client.get("/api/v1/auth/sso/login?silent=1", follow_redirects=False)
        assert login_res.status_code == 307

        callback_res = client.get("/api/v1/auth/sso/callback", follow_redirects=False)

    assert callback_res.status_code == 307
    assert callback_res.headers["location"] == "/#sso_required=1"


def test_sso_callback_non_silent_failure_returns_401(monkeypatch: pytest.MonkeyPatch):
    from authlib.integrations.base_client import OAuthError

    monkeypatch.setattr("app.api.auth.AUTH_MODE", "sso")

    mock_sso = AsyncMock()
    mock_sso.authorize_redirect.return_value = RedirectResponse("http://idp.example/authorize")
    mock_sso.authorize_access_token.side_effect = OAuthError("access_denied")
    monkeypatch.setattr("app.auth.oidc.oauth.sso", mock_sso, raising=False)

    with TestClient(app) as client:
        login_res = client.get("/api/v1/auth/sso/login", follow_redirects=False)
        assert login_res.status_code == 307

        callback_res = client.get("/api/v1/auth/sso/callback", follow_redirects=False)

    assert callback_res.status_code == 401


def test_local_login_blocked_in_sso_mode_by_default(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("app.api.auth.AUTH_MODE", "sso")

    with TestClient(app) as client:
        r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "0000"})

    assert r.status_code == 400


def test_local_login_allowed_in_sso_mode_with_flag(monkeypatch: pytest.MonkeyPatch):
    """브로커 client_id 발급 전, SSO_ALLOW_LOCAL_LOGIN=true면 기존 로컬 로그인으로
    부트스트랩할 수 있어야 한다 — 그 세션으로 require_viewer/require_admin이 걸린
    엔드포인트에도 정상 접근돼야 한다."""
    monkeypatch.setattr("app.api.auth.AUTH_MODE", "sso")
    monkeypatch.setattr("app.api.auth.SSO_ALLOW_LOCAL_LOGIN", True)
    monkeypatch.setattr("app.api.deps.AUTH_MODE", "sso")

    with TestClient(app) as client:
        r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "0000"})
        assert r.status_code == 200
        body = r.json()
        assert body["role"] == "admin"
        headers = {"Authorization": f"Bearer {body['token']}"}

        r = client.get("/api/v1/meta", headers=headers)
        assert r.status_code == 200

        r = client.get("/api/v1/admin/raw-data", headers=headers)
        assert r.status_code == 200


def test_auth_mode_endpoint_reports_local_login_flag(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("app.api.auth.AUTH_MODE", "sso")
    monkeypatch.setattr("app.api.auth.SSO_ALLOW_LOCAL_LOGIN", True)

    with TestClient(app) as client:
        r = client.get("/api/v1/auth/mode")

    assert r.status_code == 200
    assert r.json() == {"auth_mode": "sso", "sso_allow_local_login": True}
