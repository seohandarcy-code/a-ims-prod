"""DB 상태 -> 기존과 동일한 한글 헤더 wide DataFrame / .dat 파일로 재구성.

fetch_raw_dataframe()이 이 모듈의 핵심이다 — DataStore가 매 로드마다 이 함수로
raw_df를 재구성하므로, app/data/normalize.py 이후 계층(calc/*, api/*)은
데이터가 파일에서 오는지 DB에서 오는지 전혀 모른다.

export_to_dat()은 이 raw_df를 실제 .dat로 저장한다 — 운영 DB 백업 스냅샷을
만들거나(향후 K8s CronJob이 호출할 자리), 로컬 개발 환경을 그 스냅샷으로
재시딩할 때(backend/scripts/reseed_from_dat.py) 쓰는 입력을 만든다.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import select

from app.data.columns import COL
from app.data.writer import atomic_write_dat, atomic_write_json
from app.db.engine import engine
from app.db.models import custom_column_defs, custom_column_values, investment_rows


def fetch_raw_dataframe() -> tuple[pd.DataFrame, dict[str, str]]:
    """DB의 investment_rows + custom_column_* 을 raw_df(한글 헤더)와 커스텀 타입 dict로 복원한다."""
    with engine.connect() as conn:
        core_rows = list(conn.execute(select(investment_rows)).mappings())
        defs = list(conn.execute(select(custom_column_defs)).mappings())
        values = list(conn.execute(select(custom_column_values)).mappings())

    custom_types = {d["key"]: d["col_type"] for d in defs}

    custom_by_row: dict[int, dict[str, str]] = {}
    for v in values:
        custom_by_row.setdefault(v["row_no"], {})[v["column_key"]] = v["value"]

    records: list[dict[str, str]] = []
    for row in sorted(core_rows, key=lambda r: r["no"]):
        record = {COL[key]: ("" if row[key] is None else str(row[key])) for key in COL if key != "no"}
        record[COL["no"]] = str(row["no"])
        record.update(custom_by_row.get(row["no"], {}))
        for key in custom_types:
            record.setdefault(key, "")
        records.append(record)

    columns = list(COL.values()) + list(custom_types.keys())
    raw_df = pd.DataFrame(records, columns=columns)
    return raw_df, custom_types


def export_to_dat(dest_path: str | Path, types_path: str | Path | None = None) -> None:
    """현재 DB 상태를 .dat(+선택적으로 커스텀 컬럼 타입 sidecar json)로 저장한다."""
    raw_df, custom_types = fetch_raw_dataframe()
    atomic_write_dat(raw_df, dest_path)
    if types_path is not None:
        atomic_write_json(custom_types, types_path)
