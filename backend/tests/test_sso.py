"""SSO 클레임 허용 목록 판정(app/auth/oidc.py.is_allowed_by_claims)을 검증한다.

실제 Keycloak 없이도 동작을 확인할 수 있도록 순수 함수로 분리되어 있다 —
실제 리다이렉트/콜백 흐름은 로컬 Keycloak을 띄운 브라우저 테스트로 확인한다
(README.md "SSO로 전환해서 로그인 검증하기" 참고).
"""
from __future__ import annotations

from app.auth.oidc import is_allowed_by_claims


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
