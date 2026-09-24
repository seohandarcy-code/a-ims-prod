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
    monkeypatch.setattr("app.api.auth.SSO_BROKER_CONFIGURED", True)
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
    monkeypatch.setattr("app.api.auth.SSO_BROKER_CONFIGURED", True)
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
    monkeypatch.setattr("app.api.auth.SSO_BROKER_CONFIGURED", True)
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
    monkeypatch.setattr("app.api.auth.SSO_BROKER_CONFIGURED", True)
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
    monkeypatch.setattr("app.api.auth.SSO_BROKER_CONFIGURED", True)

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
    monkeypatch.setattr("app.api.auth.SSO_BROKER_CONFIGURED", True)

    mock_sso = AsyncMock()
    mock_sso.authorize_redirect.return_value = RedirectResponse("http://idp.example/authorize")
    mock_sso.authorize_access_token.side_effect = OAuthError("access_denied")
    monkeypatch.setattr("app.auth.oidc.oauth.sso", mock_sso, raising=False)

    with TestClient(app) as client:
        login_res = client.get("/api/v1/auth/sso/login", follow_redirects=False)
        assert login_res.status_code == 307

        callback_res = client.get("/api/v1/auth/sso/callback", follow_redirects=False)

    assert callback_res.status_code == 401


def test_sso_login_silent_network_failure_redirects_with_error_reason(monkeypatch: pytest.MonkeyPatch):
    """authorize_redirect가 OAuthError가 아닌 일반 예외(브로커 discovery 조회
    실패 등)를 던지면, silent=1일 때 500으로 죽는 대신 "조용한 재인증 실패"와
    같은 경로로 안전하게 넘어가야 한다 — 실제로 겪은 버그(SSO_ISSUER_URL만
    있고 client_id/secret이 없는 브로커에서, 페이지 로드 시 자동으로 도는
    silent 시도가 discovery 조회 실패로 크래시해 로그인 게이트 화면조차
    못 봤다). sso_error=broker_unreachable을 같이 실어서 프론트가 "단순히
    로그인 안 됨"과 구분해 에러 배너를 보여줄 수 있게 한다."""
    monkeypatch.setattr("app.api.auth.AUTH_MODE", "sso")
    monkeypatch.setattr("app.api.auth.SSO_BROKER_CONFIGURED", True)

    mock_sso = AsyncMock()
    mock_sso.authorize_redirect.side_effect = RuntimeError("discovery unreachable")
    monkeypatch.setattr("app.auth.oidc.oauth.sso", mock_sso, raising=False)

    with TestClient(app) as client:
        r = client.get("/api/v1/auth/sso/login?silent=1", follow_redirects=False)

    assert r.status_code == 307
    assert r.headers["location"] == "/#sso_required=1&sso_error=broker_unreachable"


def test_sso_login_non_silent_network_failure_redirects_with_error_reason(monkeypatch: pytest.MonkeyPatch):
    """같은 상황이지만 사용자가 버튼을 직접 눌러 시도한 경우(non-silent)에는
    raw JSON 에러 대신 프론트로 리다이렉트해서 게이트 화면 안에 에러 배너로
    보여줄 수 있게 한다(이 엔드포인트는 브라우저 navigation 전용이라 JSON
    바디를 읽을 소비자가 없다)."""
    monkeypatch.setattr("app.api.auth.AUTH_MODE", "sso")
    monkeypatch.setattr("app.api.auth.SSO_BROKER_CONFIGURED", True)

    mock_sso = AsyncMock()
    mock_sso.authorize_redirect.side_effect = RuntimeError("discovery unreachable")
    monkeypatch.setattr("app.auth.oidc.oauth.sso", mock_sso, raising=False)

    with TestClient(app) as client:
        r = client.get("/api/v1/auth/sso/login", follow_redirects=False)

    assert r.status_code == 307
    assert r.headers["location"] == "/#sso_error=broker_unreachable"


def test_sso_callback_non_oauth_failure_redirects_with_error_reason_when_silent(monkeypatch: pytest.MonkeyPatch):
    """authorize_access_token이 OAuthError가 아닌 일반 예외(토큰/JWKS 엔드포인트
    네트워크 실패 등)를 던져도 silent이면 크래시 대신 sso_required=1로 넘어가되,
    sso_error=broker_unreachable도 같이 실어 보낸다."""
    monkeypatch.setattr("app.api.auth.AUTH_MODE", "sso")
    monkeypatch.setattr("app.api.auth.SSO_BROKER_CONFIGURED", True)

    mock_sso = AsyncMock()
    mock_sso.authorize_redirect.return_value = RedirectResponse("http://idp.example/authorize")
    mock_sso.authorize_access_token.side_effect = RuntimeError("token endpoint unreachable")
    monkeypatch.setattr("app.auth.oidc.oauth.sso", mock_sso, raising=False)

    with TestClient(app) as client:
        login_res = client.get("/api/v1/auth/sso/login?silent=1", follow_redirects=False)
        assert login_res.status_code == 307

        callback_res = client.get("/api/v1/auth/sso/callback", follow_redirects=False)

    assert callback_res.status_code == 307
    assert callback_res.headers["location"] == "/#sso_required=1&sso_error=broker_unreachable"


def test_sso_callback_non_oauth_failure_redirects_with_error_reason_when_not_silent(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr("app.api.auth.AUTH_MODE", "sso")
    monkeypatch.setattr("app.api.auth.SSO_BROKER_CONFIGURED", True)

    mock_sso = AsyncMock()
    mock_sso.authorize_redirect.return_value = RedirectResponse("http://idp.example/authorize")
    mock_sso.authorize_access_token.side_effect = RuntimeError("token endpoint unreachable")
    monkeypatch.setattr("app.auth.oidc.oauth.sso", mock_sso, raising=False)

    with TestClient(app) as client:
        login_res = client.get("/api/v1/auth/sso/login", follow_redirects=False)
        assert login_res.status_code == 307

        callback_res = client.get("/api/v1/auth/sso/callback", follow_redirects=False)

    assert callback_res.status_code == 307
    assert callback_res.headers["location"] == "/#sso_error=broker_unreachable"


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
    monkeypatch.setattr("app.api.auth.SSO_BROKER_CONFIGURED", False)

    with TestClient(app) as client:
        r = client.get("/api/v1/auth/mode")

    assert r.status_code == 200
    assert r.json() == {
        "auth_mode": "sso",
        "sso_allow_local_login": True,
        "sso_broker_configured": False,
    }


def test_sso_login_returns_503_when_broker_not_configured(monkeypatch: pytest.MonkeyPatch):
    """SSO_ISSUER_URL/CLIENT_ID/SECRET 중 하나라도 비어있으면 oauth.sso가 아예
    등록되지 않는다 — 이때 /sso/login을 호출하면 AttributeError로 죽는 대신
    깨끗한 503을 줘야 한다(SSO_ALLOW_LOCAL_LOGIN 부트스트랩 중 실제로 겪은 버그 —
    App.vue가 첫 로드에 조용한 재인증을 시도하다 여기서 크래시했었다)."""
    monkeypatch.setattr("app.api.auth.AUTH_MODE", "sso")
    monkeypatch.setattr("app.api.auth.SSO_BROKER_CONFIGURED", False)

    with TestClient(app) as client:
        r = client.get("/api/v1/auth/sso/login", follow_redirects=False)

    assert r.status_code == 503


def test_sso_callback_returns_503_when_broker_not_configured(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("app.api.auth.AUTH_MODE", "sso")
    monkeypatch.setattr("app.api.auth.SSO_BROKER_CONFIGURED", False)

    with TestClient(app) as client:
        r = client.get("/api/v1/auth/sso/callback", follow_redirects=False)

    assert r.status_code == 503
