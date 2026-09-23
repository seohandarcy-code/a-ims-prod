"""SSO 로그인 접근 제어 목록(allowed_users) 관리자 CRUD API.

누가 대시보드에 로그인할 수 있는지/누가 admin인지 관리자가 직접 등록·수정·삭제하는
화면("접근 권한 관리" 탭)이 호출한다. AUTH_MODE로 막지 않는다 — require_admin이
이미 게이트이고, local 모드에서도 sso 전환 전에 미리 명단을 준비해두는 건 무해하다
(프론트 탭 자체는 sso 모드에서만 노출됨).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_admin
from app.auth import access_store
from app.auth.access_store import AllowedUserNotFoundError, DuplicateAllowedUserError, LastAdminError
from app.schemas.access import AllowedUserCreateRequest, AllowedUserResponse, AllowedUserUpdateRequest

router = APIRouter(prefix="/api/v1/admin/access-users", tags=["access"], dependencies=[Depends(require_admin)])


def _to_response(user: access_store.AllowedUser) -> AllowedUserResponse:
    return AllowedUserResponse(sso_id=user.sso_id, name=user.name, team=user.team, is_admin=user.is_admin)


@router.get("", response_model=list[AllowedUserResponse])
def list_access_users() -> list[AllowedUserResponse]:
    return [_to_response(u) for u in access_store.list_all()]


@router.post("", response_model=AllowedUserResponse)
def create_access_user(payload: AllowedUserCreateRequest) -> AllowedUserResponse:
    try:
        user = access_store.create(payload.sso_id, payload.name, payload.team, payload.is_admin)
    except DuplicateAllowedUserError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _to_response(user)


@router.patch("/{sso_id}", response_model=AllowedUserResponse)
def update_access_user(sso_id: str, payload: AllowedUserUpdateRequest) -> AllowedUserResponse:
    try:
        user = access_store.update(sso_id, payload.name, payload.team, payload.is_admin)
    except AllowedUserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except LastAdminError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _to_response(user)


@router.delete("/{sso_id}")
def delete_access_user(sso_id: str) -> dict[str, str]:
    try:
        access_store.delete(sso_id)
    except AllowedUserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except LastAdminError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return {"status": "ok"}
