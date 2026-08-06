"""legacy monthly_progress_table / monthly_compare_table / monthly_po_amount_table /
monthly_contract_table 이식(품의→심의, 계약 판정 기준은 종합현황과 동일하게 재정의됨).
DataFrame 대신 list[dict]를 반환한다.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.calc.helpers import (
    extract_month,
    is_contract_completed,
    is_review_completed,
    money_eok,
    parse_money_list,
    parse_month_list,
)
from app.data.columns import COL


def _records(df: pd.DataFrame) -> list[dict]:
    return df.replace({np.nan: None}).to_dict(orient="records")


def monthly_progress_table(df: pd.DataFrame, current_month: int | None = None) -> pd.DataFrame:
    rows = []
    pred_rows = []

    for _, row in df.iterrows():
        months = parse_month_list(row[COL["progress_month"]])
        amounts = parse_money_list(row[COL["progress_amount"]])

        for month, amount in zip(months, amounts):
            rows.append({"월": month, "기성금액": amount})

        pred_months = parse_month_list(row.get(COL["progress_month_pred"], ""))
        pred_amounts = parse_money_list(row.get(COL["progress_amount_pred"], ""))

        for month, amount in zip(pred_months, pred_amounts):
            pred_rows.append({"월": month, "기성금액_예측": amount})

    progress = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["월", "기성금액"])
    progress_pred = pd.DataFrame(pred_rows) if pred_rows else pd.DataFrame(columns=["월", "기성금액_예측"])

    actual_max_month = current_month if current_month is not None else 12
    max_month = 12 if not progress_pred.empty else actual_max_month
    monthly = pd.DataFrame({"월": list(range(1, max_month + 1))})

    if not progress.empty:
        progress = progress[progress["월"].between(1, actual_max_month)]

    if not progress_pred.empty:
        progress_pred = progress_pred[progress_pred["월"].between(1, 12)]

    monthly = monthly.merge(progress.groupby("월", as_index=False)["기성금액"].sum(), on="월", how="left")
    monthly = monthly.merge(progress_pred.groupby("월", as_index=False)["기성금액_예측"].sum(), on="월", how="left")

    monthly["기성금액"] = monthly["기성금액"].fillna(0)
    monthly["기성금액_예측"] = monthly["기성금액_예측"].fillna(0)
    monthly["누적기성금액"] = monthly["기성금액"].cumsum()
    # 실적 누적선은 다른 "월별 누적" 라인들과 동일하게 기준월 이후는 그리지 않는다(예측 누적선은
    # 성격상 그대로 12월까지 유지).
    monthly.loc[monthly["월"] > actual_max_month, "누적기성금액"] = np.nan
    monthly["누적기성금액_예측"] = monthly["기성금액_예측"].cumsum()

    # 종합현황 "계약 집행" 카드와 동일하게 실행품의금액을 분모로 쓴다.
    base_amount = df[COL["execution_po_amount"]].sum()

    monthly["누적집행률"] = np.where(base_amount > 0, monthly["누적기성금액"] / base_amount * 100, 0)
    monthly["예측누적집행률"] = np.where(base_amount > 0, monthly["누적기성금액_예측"] / base_amount * 100, 0)

    monthly.loc[monthly["월"] > actual_max_month, "누적집행률"] = np.nan
    monthly["월표시"] = monthly["월"].map(lambda x: f"{x}월")

    return monthly


def monthly_progress_records(df: pd.DataFrame, current_month: int) -> list[dict]:
    monthly = monthly_progress_table(df, current_month)
    return _records(monthly)


def monthly_review_amount_table(df: pd.DataFrame, current_month: int) -> pd.DataFrame:
    """심의완료 기준(종합현황 "심의 완료" KPI와 동일) 월별 금액 추이 — 심의완료월=review_month, 금액=투자비."""
    base = pd.DataFrame({"월": list(range(1, 13))})
    review_rows: list[dict] = []

    for _, row in df.iterrows():
        if not is_review_completed(row):
            continue
        month = extract_month(row.get(COL["review_month"], ""))
        if month is not None and 1 <= month <= current_month:
            review_rows.append({"월": month, "심의금액": row[COL["invest_cost"]], "심의건수": 1})

    if review_rows:
        review_monthly = (
            pd.DataFrame(review_rows).groupby("월", as_index=False).agg(심의금액=("심의금액", "sum"), 심의건수=("심의건수", "sum"))
        )
    else:
        review_monthly = pd.DataFrame(columns=["월", "심의금액", "심의건수"])

    monthly = base.merge(review_monthly, on="월", how="left")
    monthly["심의금액"] = monthly["심의금액"].fillna(0)
    monthly["심의건수"] = monthly["심의건수"].fillna(0).astype(int)
    monthly.loc[monthly["월"] > current_month, "심의건수"] = 0
    monthly["누적심의금액"] = monthly["심의금액"].cumsum()
    monthly.loc[monthly["월"] > current_month, "누적심의금액"] = np.nan
    monthly["누적심의금액_억원"] = monthly["누적심의금액"].map(lambda v: np.nan if pd.isna(v) else money_eok(v))
    monthly["전체투자금액_억원"] = money_eok(df[COL["invest_cost"]].sum())
    monthly["월표시"] = monthly["월"].map(lambda x: f"{x}월")

    return monthly


def monthly_contract_amount_table(df: pd.DataFrame, current_month: int) -> pd.DataFrame:
    """계약완료 기준(종합현황 "계약 완료" KPI와 동일) 월별 금액 추이 — 계약완료월=contract_month, 금액=실행품의금액."""
    base = pd.DataFrame({"월": list(range(1, 13))})
    contract_rows: list[dict] = []

    for _, row in df.iterrows():
        if not is_contract_completed(row):
            continue
        month = extract_month(row.get(COL["contract_month"], ""))
        if month is not None and 1 <= month <= current_month:
            contract_rows.append({"월": month, "계약금액": row[COL["execution_po_amount"]], "계약건수": 1})

    if contract_rows:
        contract_monthly = (
            pd.DataFrame(contract_rows)
            .groupby("월", as_index=False)
            .agg(계약금액=("계약금액", "sum"), 계약건수=("계약건수", "sum"))
        )
    else:
        contract_monthly = pd.DataFrame(columns=["월", "계약금액", "계약건수"])

    monthly = base.merge(contract_monthly, on="월", how="left")
    monthly["계약금액"] = monthly["계약금액"].fillna(0)
    monthly["계약건수"] = monthly["계약건수"].fillna(0).astype(int)
    monthly.loc[monthly["월"] > current_month, "계약건수"] = 0
    monthly["누적계약금액"] = monthly["계약금액"].cumsum()
    monthly.loc[monthly["월"] > current_month, "누적계약금액"] = np.nan
    monthly["누적계약금액_억원"] = monthly["누적계약금액"].map(lambda v: np.nan if pd.isna(v) else money_eok(v))
    monthly["월표시"] = monthly["월"].map(lambda x: f"{x}월")

    return monthly


def monthly_contract_amount_records(df: pd.DataFrame, current_month: int) -> list[dict]:
    return _records(monthly_contract_amount_table(df, current_month))


def monthly_contract_table(df: pd.DataFrame, current_month: int) -> pd.DataFrame:
    """계약완료(is_contract_completed) 월별 건수/금액 추이 — 종합현황과 동일 기준
    (계약월=contract_month, 금액=실행품의금액)."""
    base = pd.DataFrame({"월": list(range(1, 13))})
    contract_rows = []

    for _, row in df.iterrows():
        contract_month = extract_month(row.get(COL["contract_month"], ""))
        if (
            is_contract_completed(row)
            and contract_month is not None
            and 1 <= contract_month <= current_month
        ):
            contract_rows.append(
                {"월": contract_month, "계약건수": 1, "계약금액": row[COL["execution_po_amount"]]}
            )

    contract_monthly = (
        pd.DataFrame(contract_rows).groupby("월", as_index=False).agg(계약건수=("계약건수", "sum"), 계약금액=("계약금액", "sum"))
        if contract_rows
        else pd.DataFrame(columns=["월", "계약건수", "계약금액"])
    )

    monthly = base.merge(contract_monthly, on="월", how="left")
    monthly["계약건수"] = monthly["계약건수"].fillna(0).astype(int)
    monthly["계약금액"] = monthly["계약금액"].fillna(0)
    monthly.loc[monthly["월"] > current_month, "계약건수"] = 0
    monthly["누적계약건수"] = monthly["계약건수"].cumsum()
    monthly["누적계약금액"] = monthly["계약금액"].cumsum()
    monthly.loc[monthly["월"] > current_month, "누적계약건수"] = np.nan
    monthly.loc[monthly["월"] > current_month, "누적계약금액"] = np.nan
    monthly["누적계약금액_억원"] = monthly["누적계약금액"].map(lambda v: np.nan if pd.isna(v) else money_eok(v))
    monthly["월표시"] = monthly["월"].map(lambda x: f"{x}월")

    return monthly


def monthly_compare_table(df: pd.DataFrame, current_month: int) -> pd.DataFrame:
    """대시보드 "월별 진행 흐름 구분"의 누적 심의금액/계약금액/집행금액 3종 라인 데이터.

    심의·계약 금액은 종합현황 KPI와 동일 기준(심의완료=투자비, 계약완료=실행품의금액)이고,
    집행금액은 실제 기성처리금액 누적이다.
    """
    review_summary = monthly_review_amount_table(df, current_month)[["월", "월표시", "누적심의금액_억원"]]
    contract_summary = monthly_contract_amount_table(df, current_month)[["월", "누적계약금액_억원"]]
    progress_summary = monthly_progress_table(df, current_month)[["월", "누적기성금액"]]

    monthly = review_summary.merge(contract_summary, on="월", how="left")
    monthly = monthly.merge(progress_summary, on="월", how="left")
    monthly["누적기성금액_억원"] = monthly["누적기성금액"].map(lambda v: np.nan if pd.isna(v) else money_eok(v))
    monthly = monthly.drop(columns=["누적기성금액"])

    return monthly


def monthly_compare_records(df: pd.DataFrame, current_month: int) -> list[dict]:
    return _records(monthly_compare_table(df, current_month))


def monthly_review_amount_records(df: pd.DataFrame, current_month: int) -> list[dict]:
    return _records(monthly_review_amount_table(df, current_month))


def monthly_contract_records(df: pd.DataFrame, current_month: int) -> list[dict]:
    return _records(monthly_contract_table(df, current_month))
