"""SSO 로그인 접근 제어 목록(allowed_users) 관리 API 요청·응답 모델."""
from __future__ import annotations

from pydantic import BaseModel


class AllowedUserResponse(BaseModel):
    sso_id: str
    name: str
    team: str
    is_admin: bool


class AllowedUserCreateRequest(BaseModel):
    sso_id: str
    name: str
    team: str = ""
    is_admin: bool = False


class AllowedUserUpdateRequest(BaseModel):
    name: str
    team: str = ""
    is_admin: bool
