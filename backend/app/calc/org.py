"""legacy org_execution_table / org_po_completion_table / org_contract_registration_table
이식(품의→심의, 계약/집행 판정 기준은 종합현황과 동일하게 재정의됨). DataFrame 대신 list[dict]를 반환한다.
"""
from __future__ import annotations

import pandas as pd

from app.calc.helpers import is_contract_completed, is_review_completed, safe_divide, unique_sorted
from app.data.columns import COL, PJT_TOTAL_LABEL

PART_KEY_SEP = "::"


def org_execution_table(selected_df: pd.DataFrame, total_df: pd.DataFrame | None = None) -> list[dict]:
    """조직별 집행 현황 — 종합현황 "계약 집행" 카드와 동일하게 실행품의금액을 분모로 쓴다."""
    rows: list[dict] = []

    if total_df is not None and not total_df.empty:
        execution_po_sum = float(total_df[COL["execution_po_amount"]].sum())
        executed_sum = float(total_df[COL["executed_amount"]].sum())
        rows.append(
            {
                "org": PJT_TOTAL_LABEL,
                "count": len(total_df),
                "invest_cost": float(total_df[COL["invest_cost"]].sum()),
                "execution_po_amount": execution_po_sum,
                "executed_amount": executed_sum,
                "unexecuted_amount": max(execution_po_sum - executed_sum, 0),
                "execution_rate": safe_divide(executed_sum, execution_po_sum) * 100,
            }
        )

    if not selected_df.empty:
        grouped = selected_df.groupby(COL["org"], as_index=False).agg(
            count=(COL["no"], "count"),
            invest_cost=(COL["invest_cost"], "sum"),
            execution_po_amount=(COL["execution_po_amount"], "sum"),
            executed_amount=(COL["executed_amount"], "sum"),
        )
        grouped = grouped.sort_values(COL["org"])

        for _, r in grouped.iterrows():
            unexecuted = max(float(r["execution_po_amount"]) - float(r["executed_amount"]), 0)
            rows.append(
                {
                    "org": str(r[COL["org"]]),
                    "count": int(r["count"]),
                    "invest_cost": float(r["invest_cost"]),
                    "execution_po_amount": float(r["execution_po_amount"]),
                    "executed_amount": float(r["executed_amount"]),
                    "unexecuted_amount": unexecuted,
                    "execution_rate": safe_divide(r["executed_amount"], r["execution_po_amount"]) * 100,
                }
            )

    return rows


def org_review_completion_table(selected_df: pd.DataFrame, total_df: pd.DataFrame | None = None) -> list[dict]:
    """조직별 심의완료 현황 — 종합현황 "심의 완료" KPI와 동일하게 is_review_completed 기준."""

    def make_row(source_df: pd.DataFrame, label: str) -> dict:
        completed = int(source_df.apply(is_review_completed, axis=1).sum()) if not source_df.empty else 0
        total = len(source_df)
        incomplete = max(total - completed, 0)
        return {"org": label, "completed": completed, "incomplete": incomplete, "total": completed + incomplete}

    rows: list[dict] = []

    if total_df is not None and not total_df.empty:
        rows.append(make_row(total_df, PJT_TOTAL_LABEL))

    if not selected_df.empty:
        for org_name, group_df in sorted(selected_df.groupby(COL["org"]), key=lambda item: str(item[0])):
            rows.append(make_row(group_df, str(org_name)))

    return rows


def org_contract_registration_table(selected_df: pd.DataFrame, total_df: pd.DataFrame | None = None) -> list[dict]:
    """조직별 계약완료 현황 — 종합현황 "계약 완료" KPI와 동일하게 is_contract_completed 기준."""

    def make_row(source_df: pd.DataFrame, label: str) -> dict:
        registered = int(source_df.apply(is_contract_completed, axis=1).sum()) if not source_df.empty else 0
        total = len(source_df)
        unregistered = max(total - registered, 0)
        return {"org": label, "registered": registered, "unregistered": unregistered, "total": registered + unregistered}

    rows: list[dict] = []

    if total_df is not None and not total_df.empty:
        rows.append(make_row(total_df, PJT_TOTAL_LABEL))

    if not selected_df.empty:
        for org_name, group_df in sorted(selected_df.groupby(COL["org"]), key=lambda item: str(item[0])):
            rows.append(make_row(group_df, str(org_name)))

    return rows


def build_org_tree(df: pd.DataFrame) -> list[dict]:
    """팀 → PJT → 파트 3단계 계층을 데이터에서 그대로 도출한다.

    정적 매핑표(예: DATA_CHANGES.md의 PJT-파트 매핑)는 실데이터와 어긋날 수 있어 쓰지 않는다
    (검토 라운드에서 문서 표와 실측값이 실제로 다른 것이 확인됨). 파트 노드의 key는
    `f"{PJT}{PART_KEY_SEP}{파트}"` 복합키로, PJT 간 동명 파트가 생겨도 안전하게 구분된다.
    """
    tree: list[dict] = []
    if df.empty or COL["team"] not in df.columns or COL["part"] not in df.columns:
        return tree

    for team in unique_sorted(df[COL["team"]]):
        team_df = df[df[COL["team"]] == team]
        pjt_nodes: list[dict] = []

        for pjt in unique_sorted(team_df[COL["org"]]):
            pjt_df = team_df[team_df[COL["org"]] == pjt]
            part_nodes = [
                {"level": "part", "key": f"{pjt}{PART_KEY_SEP}{part}", "label": part}
                for part in unique_sorted(pjt_df[COL["part"]])
            ]
            pjt_nodes.append({"level": "pjt", "key": pjt, "label": pjt, "children": part_nodes})

        tree.append({"level": "team", "key": team, "label": team, "children": pjt_nodes})

    return tree


def flat_part_options(org_tree: list[dict]) -> list[str]:
    """org_tree의 파트 리프 key만 평탄화한 목록(하위호환용 flat 필드)."""
    return [
        part["key"]
        for team in org_tree
        for pjt in team["children"]
        for part in pjt["children"]
    ]


def filter_by_selected_org(df: pd.DataFrame, selected_org: str) -> pd.DataFrame:
    """대시보드/상세현황의 단일선택 drill-down(selected_org)을 스코핑한다.

    PJT_TOTAL_LABEL이면 전체, "PJT::파트" 복합키면 (PJT, 파트) 쌍으로, 그 외에는
    기존처럼 PJT 단순 일치로 매칭한다.
    """
    if selected_org == PJT_TOTAL_LABEL:
        return df

    if PART_KEY_SEP in selected_org:
        pjt, _, part = selected_org.partition(PART_KEY_SEP)
        return df[(df[COL["org"]] == pjt) & (df[COL["part"]] == part)]

    return df[df[COL["org"]] == selected_org]
