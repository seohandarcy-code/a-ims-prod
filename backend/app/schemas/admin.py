"""관리자 원본 데이터 조회/편집 API 요청·응답 모델."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class RowColumn(BaseModel):
    key: str
    label: str
    type: Literal["text", "money", "month", "date", "month_list", "money_list", "status"] = "text"
    placeholder: str | None = None
    deletable: bool = False


class RawDataResponse(BaseModel):
    columns: list[RowColumn]
    rows: list[dict[str, str]]
    has_backup: bool


class RowEditRequest(BaseModel):
    fields: dict[str, str]


class RowResponse(BaseModel):
    row: dict[str, str]


class AddColumnRequest(BaseModel):
    name: str
    type: Literal["text", "money", "date"] = "text"
