"""DB 스키마 준비 + 최초 시딩(.dat -> DB) + 전체 교체.

replace_all_from_dataframe()이 이 모듈의 핵심 공유 함수다 — 최초 시딩
(seed_if_empty), 로컬 개발 재시딩 CLI(backend/scripts/reseed_from_dat.py),
백업 복원(app/data/store.py.restore_backup)이 모두 이 함수 하나를 공유한다.
"동일 코드 경로로 처리"함으로써 세 시나리오가 서로 다르게 동작할 여지를 없앤다.
"""
from __future__ import annotations

import json
import logging

import pandas as pd
from sqlalchemy import delete, func, insert, select

from app.config import BASE_FILE, CUSTOM_COLUMN_TYPES_FILE, REV_FILE
from app.data.columns import COL
from app.data.loader import read_dat
from app.db.engine import engine
from app.db.models import custom_column_defs, custom_column_values, investment_rows, metadata

logger = logging.getLogger(__name__)


def ensure_schema() -> None:
    metadata.create_all(engine)


def is_empty() -> bool:
    with engine.connect() as conn:
        count = conn.execute(select(func.count()).select_from(investment_rows)).scalar_one()
    return count == 0


def replace_all_from_dataframe(raw_df: pd.DataFrame, custom_column_types: dict[str, str] | None = None) -> None:
    """investment_rows/custom_column_*을 raw_df(한글 헤더 wide DataFrame) 내용으로 완전히 교체한다."""
    custom_column_types = custom_column_types or {}
    known_headers = set(COL.values())
    extra_headers = [c for c in raw_df.columns if c not in known_headers]

    core_records: list[dict[str, object]] = []
    custom_records: list[dict[str, object]] = []

    for _, row in raw_df.iterrows():
        no_value = int(pd.to_numeric(row.get(COL["no"], 0), errors="coerce") or 0)
        record: dict[str, object] = {"no": no_value}
        for key, header in COL.items():
            if key == "no":
                continue
            value = row.get(header, "")
            record[key] = "" if pd.isna(value) else str(value)
        core_records.append(record)

        for header in extra_headers:
            value = row.get(header, "")
            custom_records.append(
                {
                    "row_no": no_value,
                    "column_key": header,
                    "value": "" if pd.isna(value) else str(value),
                }
            )

    custom_defs = [
        {"key": header, "col_type": custom_column_types.get(header, "text")} for header in extra_headers
    ]

    with engine.begin() as conn:
        conn.execute(delete(custom_column_values))
        conn.execute(delete(custom_column_defs))
        conn.execute(delete(investment_rows))

        if core_records:
            conn.execute(insert(investment_rows), core_records)
        if custom_defs:
            conn.execute(insert(custom_column_defs), custom_defs)
        if custom_records:
            conn.execute(insert(custom_column_values), custom_records)


def seed_if_empty() -> None:
    """DB가 비어있을 때만 base(또는 data_rev) .dat로부터 최초 1회 시딩한다.

    이미 데이터가 있으면 아무것도 하지 않는다 — 시딩 이후로는 DB가 유일한
    소스이고, 두 번 다시 .dat를 읽지 않는다.
    """
    ensure_schema()

    if not is_empty():
        return

    source = REV_FILE if REV_FILE.exists() else BASE_FILE
    logger.info("DB가 비어있어 %s 로부터 최초 시딩합니다.", source)
    raw_df = read_dat(source)

    custom_types: dict[str, str] = {}
    if CUSTOM_COLUMN_TYPES_FILE.exists():
        with open(CUSTOM_COLUMN_TYPES_FILE, "r", encoding="utf-8-sig") as f:
            custom_types = json.load(f)

    replace_all_from_dataframe(raw_df, custom_types)
    logger.info("최초 시딩 완료: rows=%d", len(raw_df))
