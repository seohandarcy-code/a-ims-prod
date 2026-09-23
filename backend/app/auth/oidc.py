"""OIDC 클라이언트 등록 — AUTH_MODE=sso일 때만 실제로 쓰인다.

authlib의 Starlette 연동(OAuth)이 SSO_ISSUER_URL의
`.well-known/openid-configuration`을 자동으로 디스커버리해 인가/토큰/JWKS
엔드포인트를 알아낸다. 등록 자체는 가볍고 네트워크 호출이 없으므로
AUTH_MODE=local일 때도 그냥 만들어 둬도 안전하다(실제 인가 코드 교환이
일어날 때만 네트워크를 탄다).

SSO_CLIENT_ID/SSO_CLIENT_SECRET은 비어 있을 수 있다 — 일부 사내 SSO Broker는
범용 멀티테넌트 OIDC(하나의 issuer에 여러 client_id 등록)가 아니라, 사용자가
브로커 포털에 자기 AD 계정으로 로그인한 상태에서 "서비스 URL"을 등록하면 그
서비스 전용의 고유한 issuer(entry) 주소를 개별 발급해준다 — 그 고유 URL 자체가
클라이언트 식별자 역할을 해서 별도 client_id/secret이 없다. authlib은 이 경우도
지원한다(`OAuth.register(client_id='', ...)`가 공식 예시): client_secret이
비어 있으면 token_endpoint_auth_method가 자동으로 "none"이 되고, client_id가
비어 있으면 ID 토큰의 aud 클레임 검증도 건너뛴다(authlib/oidc/core/claims.py의
validate_aud). 로컬 Keycloak처럼 진짜 멀티테넌트 realm은 client_id 없는 요청을
거부하므로, 이 경로는 실제 그런 방식의 브로커에서만 검증 가능하다.
"""
from __future__ import annotations

from authlib.integrations.starlette_client import OAuth

from app.config import SSO_CLIENT_ID, SSO_CLIENT_SECRET, SSO_ISSUER_URL

# issuer URL만 있으면 브로커 연동을 시도한다 — client_id/secret은 위 설명대로
# 이 issuer가 이미 서비스별로 유일하게 발급된 경우 없어도 된다.
SSO_BROKER_CONFIGURED = bool(SSO_ISSUER_URL)

oauth = OAuth()

if SSO_BROKER_CONFIGURED:
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
