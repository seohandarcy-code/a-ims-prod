"""관리자 전용 원본 데이터 조회/편집/CSV 다운로드 API."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

from app.api.deps import require_admin
from app.data.columns import COL, FIELD_PLACEHOLDERS, FIELD_TYPES
from app.data.store import DataStore, InvalidFieldError, RowNotFoundError, get_store
from app.db.export import fetch_raw_dataframe
from app.schemas.admin import AddColumnRequest, RawDataResponse, RowColumn, RowEditRequest, RowResponse
from app.schemas.auth import StatusResponse

router = APIRouter(prefix="/api/v1/admin", tags=["admin"], dependencies=[Depends(require_admin)])

_CUSTOM_TYPE_PLACEHOLDERS = {
    "money": "숫자만 입력",
    "date": "예: 2026-01-15",
}


def _row_to_dict(row: Any) -> dict[str, str]:
    return {str(k): "" if v is None else str(v) for k, v in row.items()}


@router.get("/raw-data", response_model=RawDataResponse)
def get_raw_data(store: DataStore = Depends(get_store)) -> RawDataResponse:
    raw_df = store.get_raw_df()
    custom_types = store.get_column_types()
    fixed_columns = set(COL.values())

    columns = []
    for col in raw_df.columns:
        col_type = FIELD_TYPES.get(col) or custom_types.get(col, "text")
        placeholder = FIELD_PLACEHOLDERS.get(col) or _CUSTOM_TYPE_PLACEHOLDERS.get(col_type)
        columns.append(
            RowColumn(
                key=col,
                label=col,
                type=col_type,
                placeholder=placeholder,
                deletable=col not in fixed_columns,
            )
        )

    rows = [_row_to_dict(row) for _, row in raw_df.iterrows()]
    return RawDataResponse(columns=columns, rows=rows, has_backup=store.has_backup())


@router.patch("/rows/{no}", response_model=RowResponse)
def edit_row(no: int, payload: RowEditRequest, store: DataStore = Depends(get_store)) -> RowResponse:
    try:
        row = store.edit_row(no, payload.fields)
    except RowNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidFieldError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return RowResponse(row=_row_to_dict(row))


@router.post("/rows", response_model=RowResponse, status_code=status.HTTP_201_CREATED)
def add_row(payload: RowEditRequest, store: DataStore = Depends(get_store)) -> RowResponse:
    try:
        row = store.add_row(payload.fields)
    except InvalidFieldError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return RowResponse(row=_row_to_dict(row))


@router.delete("/rows/{no}", response_model=StatusResponse)
def delete_row(no: int, store: DataStore = Depends(get_store)) -> StatusResponse:
    try:
        store.delete_row(no)
    except RowNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return StatusResponse(status="ok")


@router.post("/rows/restore", response_model=StatusResponse)
def restore_backup(store: DataStore = Depends(get_store)) -> StatusResponse:
    try:
        store.restore_backup()
    except RowNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return StatusResponse(status="ok")


@router.post("/columns", response_model=StatusResponse, status_code=status.HTTP_201_CREATED)
def add_column(payload: AddColumnRequest, store: DataStore = Depends(get_store)) -> StatusResponse:
    try:
        store.add_column(payload.name, payload.type)
    except InvalidFieldError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return StatusResponse(status="ok")


@router.delete("/columns/{key}", response_model=StatusResponse)
def delete_column(key: str, store: DataStore = Depends(get_store)) -> StatusResponse:
    try:
        store.delete_column(key)
    except RowNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidFieldError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return StatusResponse(status="ok")


@router.get("/export/csv")
def export_csv(store: DataStore = Depends(get_store)) -> Response:
    raw_df = store.get_raw_df()
    csv_bytes = raw_df.to_csv(index=False).encode("utf-8-sig")

    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="investment_raw_data.csv"'},
    )


@router.get("/export/dat")
def export_dat() -> Response:
    """운영 DB 상태를 .dat 백업 스냅샷으로 내려받는다.

    로컬 개발 환경에서는 이 파일을 backend/scripts/reseed_from_dat.py로 재시딩해
    운영 DB의 최신 데이터를 그대로 이어받아 개발할 수 있다.
    """
    raw_df, _custom_types = fetch_raw_dataframe()
    dat_bytes = raw_df.to_csv(sep="\t", index=False).encode("utf-8-sig")

    return Response(
        content=dat_bytes,
        media_type="text/tab-separated-values",
        headers={"Content-Disposition": 'attachment; filename="investment_backup.dat"'},
    )


@router.get("/export/column-types")
def export_column_types() -> dict[str, str]:
    """export/dat과 함께 내려받아 재시딩 시 커스텀 컬럼 타입(text/money/date)을 복원한다."""
    _raw_df, custom_types = fetch_raw_dataframe()
    return custom_types
