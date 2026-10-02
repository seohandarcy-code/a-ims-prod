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

import json
import logging
from pathlib import Path
from urllib.parse import urlencode

import httpx
import jwt
from authlib.integrations.starlette_client import OAuth
from jwt.algorithms import RSAAlgorithm

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


# --- SSO_FLOW_MODE=implicit_form_post(기본값) 전용 — 실제 사내 브로커 연동 ---
#
# 이 브로커는 discovery(.well-known/openid-configuration) 자체를 지원하지
# 않는다(여러 경로 조합으로 확인함 — 전부 404, /oidc/jwks만 직접 존재). 브로커가
# 제공한 파이썬 레퍼런스 예시(build_sso_url/extract_claims)를 보면 Authorization
# Code Flow가 아니라 /oidc/form-authorize로 인가 요청을 보내면 /sso/callback에
# id_token을 그대로 POST(form_post)로 돌려주고(토큰 교환 엔드포인트 없음),
# /oidc/jwks로 서명을 직접 검증하는 구조다. 아래 두 함수는 그 레퍼런스와 최대한
# 동일하게 맞췄다 — 이 브로커에서 실제로 검증된 유일한 조합이라, 추측으로
# response_type/response_mode/nonce/scope 같은 "이론상 표준" 파라미터를
# 추가하지 않는다(나중에 브로커 없이 ADFS에 직접 붙어야 하면 그때 보강).
#
# 레퍼런스와 다른 점 하나 — JWKS 조회 시 verify=False(TLS 검증 비활성화)를
# 쓰지 않는다. 이미 만들어둔 SSO_CA_BUNDLE_PATH 기반 신뢰를 그대로 재사용한다.


def build_broker_authorize_url(redirect_uri: str) -> str:
    """브로커 인가 URL을 조립한다 — discovery 없이 직접 만든다.

    client_id/redirect_uri 외에 다른 파라미터는 붙이지 않는다(레퍼런스
    build_sso_url의 브로커 분기와 동일 — 이 브로커가 실제로 받는 유일한 조합).
    """
    params = urlencode({"client_id": SSO_CLIENT_ID, "redirect_uri": redirect_uri})
    return f"{SSO_ISSUER_URL.rstrip('/')}/oidc/form-authorize?{params}"


def verify_broker_id_token(id_token: str) -> dict:
    """{SSO_ISSUER_URL}/oidc/jwks로 서명을 검증하고 클레임을 반환한다.

    레퍼런스(extract_claims)와 동일하게 RS256/verify_aud=False로 맞춘다 — 이
    브로커가 실제로 발급하는 aud 값이 client_id와 다를 수 있어 보인다. nonce
    검증은 하지 않는다 — build_broker_authorize_url이 애초에 nonce를 보내지
    않으므로 비교할 대상이 없다(레퍼런스도 동일).

    서명 검증 실패 시 jwt.ExpiredSignatureError/jwt.InvalidTokenError를 그대로
    전파한다 — 호출부(app/api/auth.py)가 이를 "로그인 거부"로 처리한다.
    """
    jwks_url = f"{SSO_ISSUER_URL.rstrip('/')}/oidc/jwks"
    verify = str(SSO_CA_BUNDLE_PATH) if SSO_CA_BUNDLE_PATH else True
    resp = httpx.get(jwks_url, verify=verify, timeout=10.0)
    resp.raise_for_status()
    jwks = resp.json()

    # 레퍼런스는 keys[0]을 그냥 쓰지만, kid가 있으면 매칭해서 더 안전하게 간다
    # (여러 키가 섞여 있어도 안전하고, kid가 없는 토큰/브로커면 첫 키로 폴백한다).
    unverified_header = jwt.get_unverified_header(id_token)
    kid = unverified_header.get("kid")
    key_dict = next((k for k in jwks["keys"] if k.get("kid") == kid), jwks["keys"][0])
    public_key = RSAAlgorithm.from_jwk(json.dumps(key_dict))

    return jwt.decode(
        id_token,
        key=public_key,
        algorithms=["RS256"],
        options={"verify_signature": True, "verify_exp": True, "verify_aud": False},
    )
