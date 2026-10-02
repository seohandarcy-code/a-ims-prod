"""SSO 클레임 허용 목록 판정(app/auth/oidc.py.is_allowed_by_claims)을 검증한다.

실제 Keycloak 없이도 동작을 확인할 수 있도록 순수 함수로 분리되어 있다 —
실제 리다이렉트/콜백 흐름은 로컬 Keycloak을 띄운 브라우저 테스트로 확인한다
(README.md "SSO로 전환해서 로그인 검증하기" 참고).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from app.auth.oidc import (
    _looks_like_pem,
    build_broker_authorize_url,
    is_allowed_by_claims,
    verify_broker_id_token,
)


def test_empty_allowlist_allows_any_authenticated_claims():
    claims = {"email": "someone@example.com"}
    assert is_allowed_by_claims(claims, [], "email") is True


def test_allowlist_allows_matching_claim_value():
    claims = {"email": "ims.admin@example.local"}
    assert is_allowed_by_claims(claims, ["ims.admin@example.local"], "email") is True


def test_allowlist_rejects_non_matching_claim_value():
    claims = {"email": "someone-else@example.com"}
    assert is_allowed_by_claims(claims, ["ims.admin@example.local"], "email") is False


def test_allowlist_rejects_missing_claim():
    claims = {"preferred_username": "ims.admin"}
    assert is_allowed_by_claims(claims, ["ims.admin@example.local"], "email") is False


def test_allowlist_checks_configured_claim_name_not_just_email():
    claims = {"preferred_username": "ims.admin", "email": "someone-else@example.com"}
    assert is_allowed_by_claims(claims, ["ims.admin"], "preferred_username") is True


def test_looks_like_pem_true_for_pem_content(tmp_path: Path):
    p = tmp_path / "ca.pem"
    p.write_text("-----BEGIN CERTIFICATE-----\nMIIB...\n-----END CERTIFICATE-----\n")
    assert _looks_like_pem(p) is True


def test_looks_like_pem_false_for_binary_der(tmp_path: Path):
    p = tmp_path / "ca.crt"
    p.write_bytes(bytes([0x30, 0x82, 0x01, 0x0A, 0x02, 0x82, 0x01, 0x01]))
    assert _looks_like_pem(p) is False


def test_looks_like_pem_true_when_file_unreadable(tmp_path: Path):
    missing = tmp_path / "does-not-exist.pem"
    assert _looks_like_pem(missing) is True


def test_build_broker_authorize_url_minimal_params(monkeypatch: pytest.MonkeyPatch):
    """레퍼런스(build_sso_url)의 브로커 분기와 동일 — client_id/redirect_uri만,
    response_type/response_mode/nonce/scope는 붙이지 않는다(검증된 조합이 아님)."""
    monkeypatch.setattr("app.auth.oidc.SSO_ISSUER_URL", "https://broker.example.local")
    monkeypatch.setattr("app.auth.oidc.SSO_CLIENT_ID", "svc79")

    url = build_broker_authorize_url("https://app.example.local/api/v1/auth/sso/callback")

    assert url == (
        "https://broker.example.local/oidc/form-authorize?"
        "client_id=svc79&redirect_uri=https%3A%2F%2Fapp.example.local%2Fapi%2Fv1%2Fauth%2Fsso%2Fcallback"
    )


def test_build_broker_authorize_url_strips_trailing_slash(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("app.auth.oidc.SSO_ISSUER_URL", "https://broker.example.local/")
    monkeypatch.setattr("app.auth.oidc.SSO_CLIENT_ID", "svc79")

    url = build_broker_authorize_url("https://app.example.local/callback")

    assert url.startswith("https://broker.example.local/oidc/form-authorize?")
    assert "//oidc" not in url.split("?", 1)[0].replace("https://", "")


def _make_rsa_jwk_pair(kid: str = "test-key-1"):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk_dict = json.loads(RSAAlgorithm.to_jwk(private_key.public_key()))
    jwk_dict["kid"] = kid
    jwk_dict["use"] = "sig"
    jwk_dict["alg"] = "RS256"
    return private_key, jwk_dict


class _FakeJwksResponse:
    def __init__(self, jwks: dict):
        self._jwks = jwks

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._jwks


def test_verify_broker_id_token_success(monkeypatch: pytest.MonkeyPatch):
    private_key, jwk_dict = _make_rsa_jwk_pair()
    token = pyjwt.encode(
        {"loginid": "svc79user", "exp": int(time.time()) + 300},
        private_key,
        algorithm="RS256",
        headers={"kid": jwk_dict["kid"]},
    )

    monkeypatch.setattr("app.auth.oidc.SSO_ISSUER_URL", "https://broker.example.local")
    monkeypatch.setattr("app.auth.oidc.SSO_CA_BUNDLE_PATH", None)
    monkeypatch.setattr(
        "app.auth.oidc.httpx.get",
        lambda *a, **kw: _FakeJwksResponse({"keys": [jwk_dict]}),
    )

    claims = verify_broker_id_token(token)

    assert claims["loginid"] == "svc79user"


def test_verify_broker_id_token_picks_key_by_kid_among_multiple(monkeypatch: pytest.MonkeyPatch):
    """레퍼런스는 keys[0]을 그냥 쓰지만, 우리는 kid로 정확한 키를 골라야 한다
    (여러 키가 섞여 있을 때 레퍼런스보다 안전한 부분)."""
    other_private_key, other_jwk = _make_rsa_jwk_pair(kid="other-key")
    private_key, jwk_dict = _make_rsa_jwk_pair(kid="real-key")
    token = pyjwt.encode(
        {"loginid": "svc79user", "exp": int(time.time()) + 300},
        private_key,
        algorithm="RS256",
        headers={"kid": "real-key"},
    )

    monkeypatch.setattr("app.auth.oidc.SSO_ISSUER_URL", "https://broker.example.local")
    monkeypatch.setattr("app.auth.oidc.SSO_CA_BUNDLE_PATH", None)
    monkeypatch.setattr(
        "app.auth.oidc.httpx.get",
        lambda *a, **kw: _FakeJwksResponse({"keys": [other_jwk, jwk_dict]}),
    )

    claims = verify_broker_id_token(token)

    assert claims["loginid"] == "svc79user"


def test_verify_broker_id_token_rejects_expired_token(monkeypatch: pytest.MonkeyPatch):
    private_key, jwk_dict = _make_rsa_jwk_pair()
    token = pyjwt.encode(
        {"loginid": "svc79user", "exp": int(time.time()) - 10},
        private_key,
        algorithm="RS256",
        headers={"kid": jwk_dict["kid"]},
    )

    monkeypatch.setattr("app.auth.oidc.SSO_ISSUER_URL", "https://broker.example.local")
    monkeypatch.setattr("app.auth.oidc.SSO_CA_BUNDLE_PATH", None)
    monkeypatch.setattr(
        "app.auth.oidc.httpx.get",
        lambda *a, **kw: _FakeJwksResponse({"keys": [jwk_dict]}),
    )

    with pytest.raises(pyjwt.ExpiredSignatureError):
        verify_broker_id_token(token)


def test_verify_broker_id_token_rejects_wrong_signature(monkeypatch: pytest.MonkeyPatch):
    """다른 키로 서명된 토큰이면(위조/다른 브로커 토큰 등) 거부돼야 한다."""
    _real_private_key, jwk_dict = _make_rsa_jwk_pair(kid="real-key")
    wrong_private_key, _ = _make_rsa_jwk_pair(kid="real-key")
    # jwk_dict(공개키)는 real_private_key와 쌍이지만, 토큰은 다른 키(wrong_private_key)로
    # 서명해서 "같은 kid인데 서명이 안 맞는" 상황을 재현한다.
    token = pyjwt.encode(
        {"loginid": "svc79user", "exp": int(time.time()) + 300},
        wrong_private_key,
        algorithm="RS256",
        headers={"kid": "real-key"},
    )

    monkeypatch.setattr("app.auth.oidc.SSO_ISSUER_URL", "https://broker.example.local")
    monkeypatch.setattr("app.auth.oidc.SSO_CA_BUNDLE_PATH", None)
    monkeypatch.setattr(
        "app.auth.oidc.httpx.get",
        lambda *a, **kw: _FakeJwksResponse({"keys": [jwk_dict]}),
    )

    with pytest.raises(pyjwt.InvalidSignatureError):
        verify_broker_id_token(token)
