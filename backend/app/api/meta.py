from __future__ import annotations

from fastapi import APIRouter, Depends

from app.calc.helpers import unique_sorted
from app.calc.org import build_org_tree, flat_part_options
from app.calc.stage import funnel_filter_options
from app.data.columns import COL, PJT_TOTAL_LABEL
from app.data.store import DataStore, get_store
from app.schemas.models import FilterOptions, MetaResponse

router = APIRouter(prefix="/api/v1", tags=["meta"])


@router.get("/meta", response_model=MetaResponse)
def get_meta(store: DataStore = Depends(get_store)) -> MetaResponse:
    df = store.get_df()
    org_tree = build_org_tree(df)

    filter_options = FilterOptions(
        org=unique_sorted(df[COL["org"]]),
        leader_opinion=unique_sorted(df[COL["leader_opinion"]]),
        center_need=unique_sorted(df[COL["center_need"]]),
        team=unique_sorted(df[COL["team"]]),
        part=flat_part_options(org_tree),
    )

    return MetaResponse(
        current_month=store.get_current_month(),
        current_label=store.get_current_label(),
        team_name="A-Infra기술팀",
        dashboard_title="Investment Management Dashboard '26",
        filter_options=filter_options,
        org_options=[PJT_TOTAL_LABEL] + filter_options.org,
        org_tree=org_tree,
        flow_stage_options=funnel_filter_options(),
    )
