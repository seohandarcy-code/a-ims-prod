"""로그인/비밀번호 변경 API 요청·응답 모델."""
from __future__ import annotations

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    token_type: str
    expires_in: int
    role: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class StatusResponse(BaseModel):
    status: str
