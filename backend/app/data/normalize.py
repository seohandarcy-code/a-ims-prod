"""legacy normalize_data / infer_current_month 이식."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from app.calc.helpers import clean_money_series, extract_month, parse_month_list
from app.config import CURRENT_MONTH_OVERRIDE, CURRENT_YEAR
from app.data.columns import COL, MONEY_COLS


class MissingColumnsError(RuntimeError):
    def __init__(self, missing_cols: list[str]):
        self.missing_cols = missing_cols
        super().__init__(f"필수 컬럼이 누락되었습니다: {', '.join(missing_cols)}")


def normalize_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    required_cols = list(COL.values())
    missing_cols = [c for c in required_cols if c not in df.columns]

    if missing_cols:
        raise MissingColumnsError(missing_cols)

    df[COL["no"]] = pd.to_numeric(df[COL["no"]], errors="coerce").fillna(0).astype(int)

    for c in MONEY_COLS:
        df[c] = clean_money_series(df[c])

    text_cols = [c for c in df.columns if c not in MONEY_COLS and c != COL["no"]]

    for c in text_cols:
        df[c] = df[c].where(df[c].notna(), "").astype(str).str.strip()

    df["담당자변경"] = np.where(
        df[COL["owner_before"]].astype(str).str.strip()
        == df[COL["owner"]].astype(str).str.strip(),
        "변경없음",
        "변경",
    )

    df["투자명변경"] = np.where(
        df[COL["title_before"]].astype(str).str.strip()
        == df[COL["title"]].astype(str).str.strip(),
        "변경없음",
        "변경",
    )

    # 분모를 기본품의금액이 아니라 실행품의금액으로 쓴다 — 종합현황 KPI "투자 집행율"과
    # 같은 기준으로 통일해, 상세리스트 집행률과 KPI 집행율이 같은 건에 대해 다르게 보이지
    # 않게 한다(2026-08-11 오너 요청).
    df["집행률"] = np.where(
        df[COL["execution_po_amount"]] > 0,
        df[COL["executed_amount"]] / df[COL["execution_po_amount"]] * 100,
        0,
    )

    df["품의율"] = np.where(
        df[COL["invest_cost"]] > 0,
        df[COL["po_amount"]] / df[COL["invest_cost"]] * 100,
        0,
    )

    df["미집행금액"] = (
        df[COL["po_amount"]] - df[COL["executed_amount"]]
    ).clip(lower=0)

    df["심의예정월_숫자"] = df[COL["leader_plan_month"]].map(extract_month)
    df["심의진행월_숫자"] = df[COL["review_month"]].map(extract_month)

    return df


def infer_current_month(df: pd.DataFrame) -> int:
    if CURRENT_MONTH_OVERRIDE is not None and 1 <= CURRENT_MONTH_OVERRIDE <= 12:
        return CURRENT_MONTH_OVERRIDE

    months: list[int] = []

    if COL["progress_month"] in df.columns:
        for value in df[COL["progress_month"]]:
            months.extend(parse_month_list(value))

    if COL["review_month"] in df.columns:
        for value in df[COL["review_month"]]:
            month = extract_month(value)

            if month is not None:
                months.append(month)

    if COL["leader_date"] in df.columns:
        for value in df[COL["leader_date"]]:
            month = extract_month(value)

            if month is not None:
                months.append(month)

    months = [m for m in months if 1 <= m <= 12]

    if months:
        return max(months)

    return datetime.now(ZoneInfo("Asia/Seoul")).month
