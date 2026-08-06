"""관리자 로그인/로그아웃/비밀번호 변경 API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_admin
from app.auth.state import (
    AccountLockedError,
    InvalidCredentialsError,
    InvalidCurrentPasswordError,
    get_auth_store,
)
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    StatusResponse,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
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
    try:
        get_auth_store().change_password(token, payload.current_password, payload.new_password)
    except InvalidCurrentPasswordError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return StatusResponse(status="ok")
