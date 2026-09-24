"""관리자 로그인/로그아웃/비밀번호 변경 API.

AUTH_MODE=local(기본값)에서는 지금까지와 100% 동일하게 동작한다. AUTH_MODE=sso일
때는 기본적으로 /login·/change-password 대신 /sso/login·/sso/callback으로
로그인한다 — 다만 SSO_ALLOW_LOCAL_LOGIN=true면 /login·/change-password도 같이
열려서(브로커 client_id 발급 전 부트스트랩용, app/config.py 참고) 두 경로가
공존할 수 있다. 어느 쪽이든 최종적으로 AdminAuthStore가 세션을 발급하므로
require_admin/admin.py는 이 스위치를 전혀 모른다.

sso 모드에서는 IdP 인증에 성공해도 app/auth/access_store.py의 allowed_users
테이블에 등록돼 있지 않으면 로그인(세션 발급) 자체가 거부된다 — "SSO 인증 성공 =
로그인 성공"이 아니라 관리자가 직접 등록한 사람만 들어올 수 있다. 등록 여부에 따라
role(admin/user)도 함께 정해진다. SSO_ADMIN_ALLOWLIST는 브레이크글래스 — 거기
등록된 계정은 allowed_users에 없어도(또는 실수로 지워져도) 로그인할 때마다
admin으로 자동 복구된다.
"""
from __future__ import annotations

import logging
import urllib.parse

from authlib.integrations.base_client import OAuthError
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse

from app.api.deps import require_admin
from app.auth import access_store
from app.auth.oidc import SSO_BROKER_CONFIGURED, is_allowed_by_claims, oauth
from app.auth.state import (
    AccountLockedError,
    InvalidCredentialsError,
    InvalidCurrentPasswordError,
    get_auth_store,
)
from app.config import (
    AUTH_MODE,
    FRONTEND_BASE_URL,
    SSO_ADMIN_ALLOWLIST,
    SSO_ALLOW_LOCAL_LOGIN,
    SSO_REDIRECT_URI,
    SSO_USER_ID_CLAIM,
)
from app.schemas.auth import (
    AuthModeResponse,
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    StatusResponse,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
logger = logging.getLogger(__name__)


def _require_auth_mode(expected: str) -> None:
    if AUTH_MODE != expected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"현재 인증 모드({AUTH_MODE})에서는 사용할 수 없습니다.",
        )


def _require_local_login_allowed() -> None:
    """/login·/change-password 게이트. local 모드는 지금까지처럼 항상 허용하고,
    sso 모드는 SSO_ALLOW_LOCAL_LOGIN이 켜져 있을 때만 허용한다(브로커
    SSO_CLIENT_ID 발급 전, 관리자가 비밀번호로 먼저 들어가 접근 권한을
    등록해둘 수 있게 하는 부트스트랩용 — app/config.py 참고)."""
    if AUTH_MODE == "local":
        return
    if AUTH_MODE == "sso" and SSO_ALLOW_LOCAL_LOGIN:
        return
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"현재 인증 모드({AUTH_MODE})에서는 사용할 수 없습니다.",
    )


@router.get("/mode", response_model=AuthModeResponse)
def get_auth_mode() -> AuthModeResponse:
    """완전 공개 엔드포인트 — 프론트가 로그인 여부를 판단하기 이전에 지금이 로그인
    게이트가 필요한 모드인지부터 알아야 하는 닭-달걀 문제를 푼다(/meta는 sso 모드에서
    require_viewer로 막혀 있어 로그인 전에는 못 부른다)."""
    return AuthModeResponse(
        auth_mode=AUTH_MODE,
        sso_allow_local_login=SSO_ALLOW_LOCAL_LOGIN,
        sso_broker_configured=SSO_BROKER_CONFIGURED,
    )


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    _require_local_login_allowed()

    try:
        token, expires_in = get_auth_store().login(payload.username, payload.password)
    except AccountLockedError as exc:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(exc)) from exc
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    return LoginResponse(token=token, token_type="bearer", expires_in=expires_in, role="admin")


@router.post("/logout", response_model=StatusResponse)
def logout(token: str = Depends(require_admin)) -> StatusResponse:
    get_auth_store().logout(token)
    return StatusResponse(status="ok")


@router.post("/change-password", response_model=StatusResponse)
def change_password(
    payload: ChangePasswordRequest,
    token: str = Depends(require_admin),
) -> StatusResponse:
    _require_local_login_allowed()

    try:
        get_auth_store().change_password(token, payload.current_password, payload.new_password)
    except InvalidCurrentPasswordError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return StatusResponse(status="ok")


@router.get("/sso/login")
async def sso_login(request: Request, silent: bool = Query(default=False)) -> RedirectResponse:
    """silent=1이면 prompt=none으로 IdP에 "조용한" 재인증을 요청한다 — 사내 다른
    페이지에서 이미 로그인돼 있어 IdP 세션이 살아있으면 로그인 폼 없이 곧바로 콜백으로
    돌아오고, 세션이 없으면 login_required류 오류로 돌아온다(콜백에서 처리).
    request.session(SessionMiddleware, OAuth state/nonce와 같은 저장소)에
    이번 시도가 silent였는지 남겨둬서, 콜백이 실패 시 자동 재시도 없이 수동 게이트
    화면으로 안내할지 판단할 수 있게 한다.
    """
    _require_auth_mode("sso")
    if not SSO_BROKER_CONFIGURED:
        # oauth.sso가 아예 등록 안 돼 있어(SSO_ISSUER_URL/CLIENT_ID/SECRET 중
        # 하나라도 비어있음) 호출하면 AttributeError로 죽는다 — 깨끗한 에러로
        # 대체한다. SSO_ALLOW_LOCAL_LOGIN=true인 동안 프론트가 이 경로를 아예
        # 안 타도록 막아주지만(App.vue), 방어적으로 여기서도 막는다.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SSO 브로커가 아직 설정되지 않았습니다(SSO_ISSUER_URL/SSO_CLIENT_ID/SSO_CLIENT_SECRET 필요).",
        )
    request.session["sso_silent_attempt"] = silent
    kwargs = {"prompt": "none"} if silent else {}
    try:
        return await oauth.sso.authorize_redirect(request, SSO_REDIRECT_URI, **kwargs)
    except Exception as exc:
        # 리다이렉트 URL을 만들기 전에 authlib이 SSO_ISSUER_URL의
        # .well-known/openid-configuration을 우리 백엔드가 직접 실시간으로
        # fetch한다 — 브로커에 도달 못하거나(DNS/네트워크/타임아웃) 비정상
        # 응답이면 여기서 예외가 그대로 터진다. silent=1은 App.vue가 페이지
        # 로드 시 자동으로 거는 시도라, 여기서 그냥 죽으면 사용자가 로그인
        # 게이트 화면조차 못 본다(실제로 겪은 버그) — 크래시 대신 이미 있는
        # "조용한 재인증 실패" 경로로 안전하게 넘어간다.
        logger.warning("SSO 로그인 시작 실패(silent=%s): %s: %s", silent, type(exc).__name__, exc)
        reason = "broker_unreachable"
        if silent:
            return RedirectResponse(f"{FRONTEND_BASE_URL}/#sso_required=1&sso_error={reason}")
        # 이 엔드포인트는 브라우저 navigation 전용이라 JSON 에러 바디를 읽을
        # 소비자가 없다 — 게이트 화면 안에서 에러 배너로 보여줄 수 있도록
        # 프론트로 리다이렉트한다(raw 502 JSON을 그대로 보여주는 대신).
        return RedirectResponse(f"{FRONTEND_BASE_URL}/#sso_error={reason}")


@router.get("/sso/callback")
async def sso_callback(request: Request) -> RedirectResponse:
    _require_auth_mode("sso")
    if not SSO_BROKER_CONFIGURED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SSO 브로커가 아직 설정되지 않았습니다(SSO_ISSUER_URL/SSO_CLIENT_ID/SSO_CLIENT_SECRET 필요).",
        )

    was_silent = request.session.pop("sso_silent_attempt", False)

    try:
        token = await oauth.sso.authorize_access_token(request)
    except OAuthError as exc:
        logger.warning("SSO 콜백 실패(silent=%s): %s", was_silent, exc)
        if was_silent:
            # 조용한 재인증 실패(IdP 세션 없음) — 프론트는 이걸 보고 수동 로그인
            # 게이트를 띄운다. 여기서 자동으로 다시 시도하면 무한 리다이렉트 루프가 된다.
            return RedirectResponse(f"{FRONTEND_BASE_URL}/#sso_required=1")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="SSO 로그인에 실패했습니다.")
    except Exception as exc:
        # OAuthError가 아닌 실패(토큰/JWKS 엔드포인트 네트워크 오류 등) — IdP가
        # 로그인을 "거부"한 게 아니라 브로커에 도달조차 못한 경우라 구분해서
        # 프론트에 알려준다(/sso/login의 authorize_redirect 예외 처리와 같은 원칙).
        logger.warning("SSO 콜백 중 브로커 통신 실패(silent=%s): %s: %s", was_silent, type(exc).__name__, exc)
        reason = "broker_unreachable"
        if was_silent:
            return RedirectResponse(f"{FRONTEND_BASE_URL}/#sso_required=1&sso_error={reason}")
        return RedirectResponse(f"{FRONTEND_BASE_URL}/#sso_error={reason}")

    claims = token.get("userinfo") or {}
    sso_id = str(claims.get(SSO_USER_ID_CLAIM, "")).strip()

    if not sso_id:
        # 실제 브로커가 SSO_USER_ID_CLAIM과 다른 이름으로 클레임을 보내는 경우
        # 여기 걸린다 — 클레임 값(개인정보)은 안 찍고 키 목록만 남겨서, 값 노출
        # 없이 실제 클레임 이름을 확인해 SSO_USER_ID_CLAIM을 맞출 수 있게 한다.
        logger.warning(
            "SSO_USER_ID_CLAIM(%r)에 해당하는 클레임을 찾지 못함 — 실제로 받은 클레임 키: %s",
            SSO_USER_ID_CLAIM,
            list(claims.keys()),
        )

    # 브레이크글래스: SSO_ADMIN_ALLOWLIST에 매칭되면 allowed_users에 없어도(또는
    # 실수로 지워졌어도) 로그인할 때마다 admin으로 자동 등록/복구된다.
    if sso_id and is_allowed_by_claims(claims, SSO_ADMIN_ALLOWLIST, SSO_USER_ID_CLAIM):
        access_store.upsert_bootstrap_admin(sso_id, default_name=str(claims.get("name") or sso_id))

    user = access_store.get_by_sso_id(sso_id) if sso_id else None
    if user is None:
        # IdP 인증에는 성공했지만 관리자가 등록하지 않은 계정 — 로그인 자체를
        # 거부한다(예전엔 여기서 최소 "user" 세션을 내줬으나, 사내 SSO를 직접
        # 관리하지 않는 배포 환경에서는 "인증 성공 = 접근 허용"이 아니어야 한다).
        # sso_id는 로그인 시도 본인의 식별자이자 관리자가 접근 권한 관리 화면에
        # 그대로 등록해줘야 하는 값이라 로그에 남긴다(클레임 값 전체가 아님).
        logger.warning("등록되지 않은 계정의 로그인 시도: sso_id=%s", sso_id)
        return RedirectResponse(f"{FRONTEND_BASE_URL}/#access_denied=1")

    role = "admin" if user.is_admin else "user"
    session_token, expires_in = get_auth_store().issue_session(role)
    logger.info("SSO 로그인 성공: sso_id=%s role=%s", sso_id, role)

    # 프론트/백엔드가 같은 origin이면(지금까지 전제) FRONTEND_BASE_URL이 비어있어
    # 상대 경로 "/#..."로 리다이렉트한다(README "PostgreSQL로 전환해서 개발하기"
    # 절과 동일한 원칙). 도메인이 분리된 배포는 FRONTEND_BASE_URL을 채워 프론트의
    # 실제 도메인으로 리다이렉트한다(app/config.py 참고). 토큰은 쿼리스트링이 아니라
    # URL 프래그먼트(#)에 실어 보낸다 — 프래그먼트는 브라우저가 서버로 전송하지
    # 않으므로 접근 로그/리퍼러에 남지 않는다.
    name_q = urllib.parse.quote_plus(user.name)
    team_q = urllib.parse.quote_plus(user.team)
    return RedirectResponse(
        f"{FRONTEND_BASE_URL}/#token={session_token}&expires_in={expires_in}&role={role}&name={name_q}&team={team_q}"
    )
