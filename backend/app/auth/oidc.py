"""OIDC 클라이언트 등록 — AUTH_MODE=sso일 때만 실제로 쓰인다.

authlib의 Starlette 연동(OAuth)이 SSO_ISSUER_URL의
`.well-known/openid-configuration`을 자동으로 디스커버리해 인가/토큰/JWKS
엔드포인트를 알아낸다. 등록 자체는 가볍고 네트워크 호출이 없으므로
AUTH_MODE=local일 때도 그냥 만들어 둬도 안전하다(실제 인가 코드 교환이
일어날 때만 네트워크를 탄다).
"""
from __future__ import annotations

from authlib.integrations.starlette_client import OAuth

from app.config import SSO_CLIENT_ID, SSO_CLIENT_SECRET, SSO_ISSUER_URL

oauth = OAuth()

if SSO_ISSUER_URL and SSO_CLIENT_ID and SSO_CLIENT_SECRET:
    oauth.register(
        name="sso",
        server_metadata_url=f"{SSO_ISSUER_URL.rstrip('/')}/.well-known/openid-configuration",
        client_id=SSO_CLIENT_ID,
        client_secret=SSO_CLIENT_SECRET,
        client_kwargs={"scope": "openid email profile"},
    )


def is_allowed_by_claims(claims: dict, allowlist: list[str], claim_name: str) -> bool:
    """SSO 인증에 성공한 사용자에게 실제로 admin 세션을 내줄지 판정한다.

    allowlist가 비어 있으면(로컬 검증 기본값) SSO 인증에 성공한 누구나 허용한다.
    채워져 있으면 claims[claim_name] 값이 그 목록에 있어야만 허용한다 — 순수
    함수라 실제 Keycloak 없이도 단위 테스트 가능하다(backend/tests/test_sso.py).
    """
    if not allowlist:
        return True
    return str(claims.get(claim_name, "")) in allowlist
