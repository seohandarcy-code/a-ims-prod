"""legacy show_dashboard_tab(투자 종합현황 탭) 이식."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import CommonFilters
from app.calc.detail import DETAIL_COLUMNS, DETAIL_SEARCH_KEYS, build_detail_rows
from app.calc.helpers import extract_month, is_contract_completed, is_review_completed, safe_divide, unique_sorted
from app.calc.kpi import calculate_kpi_values
from app.calc.org import filter_by_selected_org
from app.calc.stage import funnel_key_mask, make_progress_funnel
from app.calc.monthly import monthly_compare_records
from app.data.columns import COL, PJT_TOTAL_LABEL
from app.data.store import DataStore, get_store
from app.schemas.models import DashboardResponse

router = APIRouter(prefix="/api/v1", tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    filters: CommonFilters = Depends(),
    selected_org: str = Query(default=PJT_TOTAL_LABEL),
    funnel_key: str | None = Query(default=None),
    month_key: int | None = Query(default=None),
    store: DataStore = Depends(get_store),
) -> DashboardResponse:
    all_df = store.get_df()
    current_month = store.get_current_month()

    sidebar_filtered_df = filters.apply(all_df)

    org_options = [PJT_TOTAL_LABEL] + unique_sorted(all_df[COL["org"]])

    org_filtered_df = filter_by_selected_org(sidebar_filtered_df, selected_org)
    detail_filtered_df = filter_by_selected_org(all_df, selected_org)

    # 종합진행 퍼널 막대를 클릭하면(funnel_key) 상세 리스트만 그 항목 기준으로 한 번 더 좁힌다.
    # KPI 카드는 계속 원래 detail_filtered_df(조직 스코프) 기준으로 계산해야 하므로 별도 변수로 둔다.
    detail_rows_df = detail_filtered_df[funnel_key_mask(detail_filtered_df, funnel_key)] if funnel_key else detail_filtered_df

    # 월별 진행 흐름 그래프를 클릭하면(month_key) 상세 리스트에 보이는 월 관련 컬럼(계약월_입력/팀장심의예정)
    # 중 하나라도 그 달과 일치하는 행만 남긴다. extract_month()로 정확히 해석해 비교하므로
    # "11월"/"12월"이 "1월"에 부분 문자열로 오탐되는 문제가 없다.
    if month_key:
        detail_rows_df = detail_rows_df[
            detail_rows_df[COL["contract_month_input"]].map(lambda v: extract_month(v) == month_key)
            | detail_rows_df[COL["leader_plan_month"]].map(lambda v: extract_month(v) == month_key)
        ]

    # "전체 투자계획"(계획+계획외+Drop)과 "진행 투자계획"(Drop 제외 계획+계획외) KPI 카드용 스코프.
    plan_total_df = detail_filtered_df[detail_filtered_df[COL["plan_type"]].isin(["계획", "계획외", "Drop"])]
    plan_progress_df = detail_filtered_df[detail_filtered_df[COL["plan_type"]].isin(["계획", "계획외"])]

    # "심의 완료"(센터장_심의필요='필요'면 센터장 심의, 아니면 팀장 심의 승인 기준) KPI 카드용 스코프.
    if org_filtered_df.empty:
        review_count = 0
        review_sum = 0.0
    else:
        review_mask = org_filtered_df.apply(is_review_completed, axis=1)
        review_count = int(review_mask.sum())
        review_sum = float(org_filtered_df.loc[review_mask, COL["invest_cost"]].sum())

    # "계약 완료"(ERP등록 또는 IRB심의·IT-PMS 완료+계약월_입력 존재 기준) KPI 카드용 스코프.
    if org_filtered_df.empty:
        contract_done_count = 0
        contract_done_sum = 0.0
    else:
        contract_done_mask = org_filtered_df.apply(is_contract_completed, axis=1)
        contract_done_count = int(contract_done_mask.sum())
        contract_done_sum = float(org_filtered_df.loc[contract_done_mask, COL["execution_po_amount"]].sum())

    # "투자 완료"(투자완료='완료' 기준, 정산액=기성처리금액_합계) KPI 카드용 스코프.
    if org_filtered_df.empty:
        investment_done_count = 0
        investment_done_sum = 0.0
    else:
        investment_done_mask = org_filtered_df[COL["investment_complete"]].astype(str).str.strip() == "완료"
        investment_done_count = int(investment_done_mask.sum())
        investment_done_sum = float(org_filtered_df.loc[investment_done_mask, COL["executed_amount"]].sum())

    # "계약 집행율"(기성처리금액_합계 / 실행품의금액 기준 — 계약완료 건에 한정된 정산 진행률) KPI 카드용 스코프.
    executed_amount_total = float(org_filtered_df[COL["executed_amount"]].sum())
    execution_po_amount_total = float(org_filtered_df[COL["execution_po_amount"]].sum())
    amount_execution_rate = safe_divide(executed_amount_total, execution_po_amount_total) * 100

    executive_kpi = {
        "total_count": int(len(plan_total_df)),
        "invest_sum": float(plan_total_df[COL["invest_cost"]].sum()),
        "progress_count": int(len(plan_progress_df)),
        "progress_sum": float(plan_progress_df[COL["invest_cost"]].sum()),
        "review_count": review_count,
        "review_sum": review_sum,
        "contract_done_count": contract_done_count,
        "contract_done_sum": contract_done_sum,
        "investment_done_count": investment_done_count,
        "investment_done_sum": investment_done_sum,
        "amount_execution_rate": amount_execution_rate,
        "execution_settled_sum": executed_amount_total,
    }

    progress_funnel = make_progress_funnel(org_filtered_df)

    monthly_flow = monthly_compare_records(org_filtered_df, current_month) if not org_filtered_df.empty else []

    return DashboardResponse(
        selected_org=selected_org,
        org_options=org_options,
        executive_kpi=executive_kpi,
        progress_funnel=progress_funnel,
        monthly_flow=monthly_flow,
        detail_columns=DETAIL_COLUMNS,
        detail_search_keys=DETAIL_SEARCH_KEYS,
        detail_rows=build_detail_rows(detail_rows_df),
    )
