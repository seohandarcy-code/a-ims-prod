"""legacy show_status_monthly_tab(투자 진행 상세현황 탭) 이식.

이 탭은 종합현황 탭에서 선택한 조직(selected_org)까지 반영된 동일한
스코프의 데이터(org_filtered_df)를 그대로 이어받아 사용한다(legacy main()에서
show_dashboard_tab의 반환값을 show_status_monthly_tab에 전달하던 것과 동일한 흐름).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import CommonFilters
from app.calc.monthly import (
    monthly_contract_records,
    monthly_progress_records,
    monthly_review_amount_records,
)
from app.calc.org import (
    filter_by_selected_org,
    org_contract_registration_table,
    org_execution_table,
    org_review_completion_table,
)
from app.calc.stage import make_stage_summary
from app.data.columns import PJT_TOTAL_LABEL
from app.data.store import DataStore, get_store
from app.schemas.models import StatusDetailResponse

router = APIRouter(prefix="/api/v1", tags=["status-detail"])


@router.get("/status-detail", response_model=StatusDetailResponse)
def get_status_detail(
    filters: CommonFilters = Depends(),
    selected_org: str = Query(default=PJT_TOTAL_LABEL),
    store: DataStore = Depends(get_store),
) -> StatusDetailResponse:
    all_df = store.get_df()
    current_month = store.get_current_month()

    sidebar_filtered_df = filters.apply(all_df)

    scoped_df = filter_by_selected_org(sidebar_filtered_df, selected_org)

    summary = make_stage_summary(scoped_df)

    review_monitoring = {
        "summary": summary,
        "org_table": org_review_completion_table(selected_df=scoped_df, total_df=None),
        "monthly_table": monthly_review_amount_records(scoped_df, current_month) if not scoped_df.empty else [],
    }

    contract_monitoring = {
        "summary": summary,
        "org_table": org_contract_registration_table(selected_df=scoped_df, total_df=None),
        "monthly_table": monthly_contract_records(scoped_df, current_month) if not scoped_df.empty else [],
    }

    execution_monitoring = {
        "summary": summary,
        "org_table": org_execution_table(selected_df=scoped_df, total_df=None),
        "monthly_table": monthly_progress_records(scoped_df, current_month) if not scoped_df.empty else [],
    }

    return StatusDetailResponse(
        review_monitoring=review_monitoring,
        contract_monitoring=contract_monitoring,
        execution_monitoring=execution_monitoring,
    )
