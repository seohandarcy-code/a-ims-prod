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

import logging
from pathlib import Path

from authlib.integrations.starlette_client import OAuth

from app.config import SSO_CA_BUNDLE_PATH, SSO_CLIENT_ID, SSO_CLIENT_SECRET, SSO_ISSUER_URL

logger = logging.getLogger(__name__)

# issuer URL만 있으면 브로커 연동을 시도한다 — client_id/secret은 위 설명대로
# 이 issuer가 이미 서비스별로 유일하게 발급된 경우 없어도 된다.
SSO_BROKER_CONFIGURED = bool(SSO_ISSUER_URL)


def _looks_like_pem(path: Path) -> bool:
    """CA 번들 파일이 PEM(텍스트) 형식으로 보이는지 가볍게 확인한다.

    확실한 검증은 아니다 — 실제 유효성은 TLS 핸드셰이크 시점에 ssl 모듈이
    최종 판정한다(Python ssl은 CA 번들로 PEM만 받고 DER 바이너리는 거부함).
    회사에서 받은 인증서가 .crt/.cer 확장자라 DER일 수 있는, 흔히 겪는 실수를
    기동 시점에 조금 더 빨리 알아차리기 위한 보조 장치일 뿐이다.
    """
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return True  # 못 읽으면 판단 보류 — 실제 verify 시도에서 드러나게 둔다
    return "BEGIN CERTIFICATE" in content


oauth = OAuth()

if SSO_BROKER_CONFIGURED:
    client_kwargs: dict = {"scope": "openid email profile"}
    if SSO_CA_BUNDLE_PATH:
        # authlib의 client_kwargs는 discovery/token/userinfo 요청에 쓰이는
        # httpx 클라이언트 생성자에 그대로 전달된다. verify는
        # authlib.integrations.httpx_client.utils.HTTPX_CLIENT_KWARGS에 포함된
        # 공식 지원 키라, 이 세 요청 전부에 내부 CA 신뢰를 한 번에 적용할 수
        # 있는 가장 정확한 주입 지점이다(app/config.py 참고).
        if SSO_CA_BUNDLE_PATH.exists():
            client_kwargs["verify"] = str(SSO_CA_BUNDLE_PATH)
            if not _looks_like_pem(SSO_CA_BUNDLE_PATH):
                logger.warning(
                    "SSO_CA_BUNDLE_PATH(%s)가 PEM 형식이 아닌 것 같습니다"
                    "(파일 안에 '-----BEGIN CERTIFICATE-----'가 없음) — DER/바이너리"
                    " 인증서라면 `openssl x509 -inform der -in <원본> -out <파일>.pem`"
                    "으로 변환하세요. 이대로 두면 실제 SSO 로그인 시도 시 SSL 에러로"
                    " 실패할 수 있습니다.",
                    SSO_CA_BUNDLE_PATH,
                )
        else:
            logger.warning(
                "SSO_CA_BUNDLE_PATH가 설정됐지만 파일을 찾을 수 없습니다: %s", SSO_CA_BUNDLE_PATH
            )
    oauth.register(
        name="sso",
        server_metadata_url=f"{SSO_ISSUER_URL.rstrip('/')}/.well-known/openid-configuration",
        client_id=SSO_CLIENT_ID,
        client_secret=SSO_CLIENT_SECRET,
        client_kwargs=client_kwargs,
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
