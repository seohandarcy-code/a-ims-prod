"""legacy show_detail_section의 데이터 가공 부분 이식(신호등/금액 억원 변환/예산전용 마이너스 표기).

검색(DETAIL_SEARCH_COLUMNS)은 데이터 규모가 작아(수백 행) 프론트에서 클라이언트 사이드로 처리한다.
"""
from __future__ import annotations

import pandas as pd

from app.calc.helpers import extract_month, is_review_completed, money_eok
from app.data.columns import COL

# 상세 테이블에 노출할 컬럼(키, 라벨, 타입) — legacy DETAIL_TABLE_COLUMNS/DETAIL_COLUMN_CONFIGS 이식
DETAIL_COLUMNS: list[dict] = [
    {"key": "no", "label": "NO", "type": "number"},
    {"key": "signal", "label": "신호등", "type": "text"},
    {"key": "org", "label": "PJT", "type": "text"},
    {"key": "part", "label": "파트", "type": "text"},
    {"key": "owner", "label": "담당자", "type": "text"},
    {"key": "wbs", "label": "WBS_Code", "type": "text"},
    {"key": "title", "label": "투자명", "type": "text"},
    {"key": "plan_type", "label": "계획구분", "type": "text"},
    {"key": "leader_plan_month", "label": "팀장심의예정", "type": "text"},
    {"key": "leader_opinion", "label": "팀장심의", "type": "text"},
    {"key": "center_opinion", "label": "센터장심의", "type": "text"},
    {"key": "erp_registered", "label": "ERP등록", "type": "text"},
    {"key": "irb_review", "label": "IRB심의", "type": "text"},
    {"key": "it_pms", "label": "IT-PMS", "type": "text"},
    {"key": "contract_complete_flag", "label": "계약완료구분", "type": "text"},
    {"key": "contract_month_input", "label": "계약월_입력", "type": "text"},
    {"key": "planned_cost", "label": "투자비(연초계획)", "type": "money"},
    {"key": "increase", "label": "증액", "type": "money"},
    {"key": "transfer", "label": "예산전용", "type": "money"},
    {"key": "invest_cost", "label": "투자비", "type": "money"},
    {"key": "contract_amount_input", "label": "계약금액", "type": "money"},
    {"key": "execution_po_amount", "label": "실행품의금액", "type": "money"},
    {"key": "executed_amount", "label": "집행금액", "type": "money"},
    {"key": "execution_rate", "label": "집행률", "type": "progress"},
    {"key": "investment_complete", "label": "투자완료", "type": "text"},
]

DETAIL_SEARCH_KEYS = [
    "title",
    "wbs",
    "owner",
    "org",
    "part",
    "plan_type",
    "leader_opinion",
    "erp_registered",
    "irb_review",
    "it_pms",
    "contract_complete_flag",
    "investment_complete",
]


def _signal(row: pd.Series, current_month: int) -> str:
    # "종합현황"의 "심의 완료" KPI 카드와 동일 기준(is_review_completed)으로 초록을 판정한다.
    if is_review_completed(row):
        return "🟢"

    planned_month = extract_month(row.get(COL["leader_plan_month"], ""))
    if planned_month is not None and planned_month < current_month:
        return "🟡"

    return "⚪"


def build_detail_rows(df: pd.DataFrame, current_month: int) -> list[dict]:
    if df.empty:
        return []

    ordered = df.sort_values(COL["no"])
    rows: list[dict] = []

    for _, row in ordered.iterrows():
        transfer_eok = money_eok(row[COL["transfer"]])
        transfer_display = 0.0 if transfer_eok == 0 else -abs(transfer_eok)

        rows.append(
            {
                "no": int(row[COL["no"]]),
                "signal": _signal(row, current_month),
                "org": row[COL["org"]],
                "part": row[COL["part"]],
                "owner": row[COL["owner"]],
                "wbs": row[COL["wbs"]],
                "title": row[COL["title"]],
                "plan_type": row[COL["plan_type"]],
                "leader_plan_month": row[COL["leader_plan_month"]],
                "leader_opinion": row[COL["leader_opinion"]],
                "center_opinion": row[COL["center_opinion"]],
                "erp_registered": row[COL["erp_registered"]] or "미등록",
                "irb_review": row[COL["irb_review"]] or "미완료",
                "it_pms": row[COL["it_pms"]] or "미완료",
                "contract_complete_flag": row[COL["contract_complete_flag"]] or "미완료",
                "contract_month_input": row[COL["contract_month_input"]],
                "planned_cost": money_eok(row[COL["planned_cost"]]),
                "increase": money_eok(row[COL["increase"]]),
                "transfer": transfer_display,
                "invest_cost": money_eok(row[COL["invest_cost"]]),
                "contract_amount_input": money_eok(row[COL["contract_amount_input"]]),
                "execution_po_amount": money_eok(row[COL["execution_po_amount"]]),
                "executed_amount": money_eok(row[COL["executed_amount"]]),
                "execution_rate": round(float(row["집행률"]), 1),
                "investment_complete": row[COL["investment_complete"]] or "미완료",
            }
        )

    return rows
