"""legacy web_new5_transfer_minus_detail.py의 공통 함수 이식."""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from app.config import CURRENT_YEAR
from app.data.columns import COL


def money_eok(value: float | int | None) -> float:
    if value is None or pd.isna(value):
        return 0.0
    return float(value) / 100_000_000


def fmt_eok(value: float | int | None, digit: int = 1) -> str:
    return f"{money_eok(value):,.{digit}f} 억"


def fmt_pct(value: float | int | None, digit: int = 1) -> str:
    if value is None or pd.isna(value):
        return "0.0 %"
    return f"{float(value):,.{digit}f} %"


def safe_divide(numerator: float, denominator: float) -> float:
    if denominator is None or denominator == 0 or pd.isna(denominator):
        return 0.0
    return float(numerator) / float(denominator)


def clean_money_series(series: pd.Series) -> pd.Series:
    cleaned = (
        series.astype(str)
        .str.replace("원", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.strip()
    )
    cleaned = cleaned.replace({"": "0", "nan": "0", "None": "0", "-": "0"})
    return pd.to_numeric(cleaned, errors="coerce").fillna(0)


def extract_month(value) -> int | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None

    if isinstance(value, (int, float)) and not pd.isna(value):
        month = int(value)
        return month if 1 <= month <= 12 else None

    text = str(value).strip()

    if not text:
        return None

    match = re.search(r"(1[0-2]|[1-9])\s*월", text)
    if match:
        return int(match.group(1))

    match = re.search(rf"{CURRENT_YEAR}[-./](1[0-2]|0?[1-9])", text)
    if match:
        return int(match.group(1))

    match = re.search(r"(?:^|[-./])(1[0-2]|0?[1-9])(?:$|[-./])", text)
    if match:
        return int(match.group(1))

    if text.isdigit():
        month = int(text)
        return month if 1 <= month <= 12 else None

    return None


def parse_month_list(value) -> list[int]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []

    text = str(value).strip()

    if not text:
        return []

    month_matches = re.findall(r"(1[0-2]|[1-9])\s*월", text)

    if month_matches:
        return [int(m) for m in month_matches]

    months = []

    for token in re.split(r"[,/|;]+", text):
        month = extract_month(token)

        if month is not None:
            months.append(month)

    return months


def parse_money_list(value) -> list[float]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []

    text = str(value).strip()

    if not text:
        return []

    text = text.replace("원", "").replace(" ", "")

    if any(sep in text for sep in ["/", "|", ";"]):
        tokens = re.split(r"[/|;]+", text)
        amounts = []

        for token in tokens:
            token = token.replace(",", "").strip()

            if not token:
                continue

            try:
                amounts.append(float(token))
            except ValueError:
                continue

        return amounts

    money_patterns = re.findall(r"\d{1,3}(?:,\d{3})+|\d+", text)

    amounts = []

    for token in money_patterns:
        token = token.replace(",", "").strip()

        if not token:
            continue

        try:
            amounts.append(float(token))
        except ValueError:
            continue

    return amounts


def unique_sorted(series: pd.Series) -> list[str]:
    values = [
        str(v).strip()
        for v in series.dropna().unique().tolist()
        if str(v).strip()
    ]

    return sorted(values)


def is_po_completed_value(value) -> bool:
    status = str(value).strip()

    completed = (
        status in ["완료", "Y", "y", "Yes", "YES", "yes", "O", "o", "완료됨", "품의완료"]
        or (
            "완료" in status
            and not any(block in status for block in ["미완료", "미완", "미진행"])
        )
    )

    return completed


def is_contract_registered_value(value) -> bool:
    status = str(value).strip()

    registered = (
        status in ["완료", "Y", "y", "Yes", "YES", "yes", "O", "o", "등록", "계약등록"]
        or (
            "완료" in status
            and not any(block in status for block in ["미완료", "미완", "미진행"])
        )
    )

    return registered


def count_po_completed(df: pd.DataFrame) -> int:
    if df.empty or COL["po_done"] not in df.columns:
        return 0

    return int(df[COL["po_done"]].map(is_po_completed_value).sum())


def count_contract_registered(df: pd.DataFrame) -> int:
    if df.empty or COL["contract_done"] not in df.columns:
        return 0

    return int(df[COL["contract_done"]].map(is_contract_registered_value).sum())


def is_contract_completed(row: pd.Series) -> bool:
    """계약완료 판정: ERP등록 완료 또는 (IRB심의·IT-PMS 완료 + 계약월_입력 존재)."""
    if str(row.get(COL["erp_registered"], "")).strip() == "등록":
        return True

    irb_done = str(row.get(COL["irb_review"], "")).strip() == "완료"
    pms_done = str(row.get(COL["it_pms"], "")).strip() == "완료"
    has_contract_month = bool(str(row.get(COL["contract_month_input"], "")).strip())

    return irb_done and pms_done and has_contract_month


def is_review_completed(row: pd.Series) -> bool:
    """심의완료 판정: 센터장_심의필요='필요'면 센터장 심의 승인, 아니면 팀장 심의 승인 기준."""
    if str(row.get(COL["center_need"], "")).strip() == "필요":
        return str(row.get(COL["center_opinion"], "")).strip() == "승인"
    return str(row.get(COL["leader_opinion"], "")).strip() == "승인"


def make_invest_signal(row: pd.Series, current_month: int, po_done_col: str, plan_month_col: str) -> str:
    if is_po_completed_value(row.get(po_done_col, "")):
        return "🟢"

    planned_month = extract_month(row.get(plan_month_col, ""))

    if planned_month is not None and planned_month < current_month:
        return "🟡"

    return "⚪"
