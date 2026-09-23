from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import require_viewer
from app.calc.helpers import unique_sorted
from app.calc.org import build_org_tree, flat_part_options
from app.calc.stage import funnel_filter_options
from app.config import AUTH_MODE
from app.data.columns import COL, PJT_TOTAL_LABEL
from app.data.store import DataStore, get_store
from app.schemas.models import FilterOptions, MetaResponse

router = APIRouter(prefix="/api/v1", tags=["meta"])


@router.get("/meta", response_model=MetaResponse)
def get_meta(
    store: DataStore = Depends(get_store),
    _viewer: str | None = Depends(require_viewer),
) -> MetaResponse:
    df = store.get_df()
    org_tree = build_org_tree(df)

    filter_options = FilterOptions(
        org=unique_sorted(df[COL["org"]]),
        leader_opinion=unique_sorted(df[COL["leader_opinion"]]),
        center_need=unique_sorted(df[COL["center_need"]]),
        team=unique_sorted(df[COL["team"]]),
        part=flat_part_options(org_tree),
    )

    # 팀명을 하드코딩하지 않고 데이터에서 도출한다 — 팀이 1개면 그 이름을 그대로 쓰고,
    # 나중에 팀명이 또 바뀌거나(값만 바뀜) 팀이 여러 개로 늘어나도 코드 수정 없이
    # 자동으로 반영된다.
    team_names = filter_options.team
    if len(team_names) == 1:
        team_name = team_names[0]
    elif team_names:
        team_name = ", ".join(team_names)
    else:
        team_name = PJT_TOTAL_LABEL

    return MetaResponse(
        current_month=store.get_current_month(),
        current_label=store.get_current_label(),
        team_name=team_name,
        dashboard_title="Investment Management Dashboard '26",
        filter_options=filter_options,
        org_options=[PJT_TOTAL_LABEL] + filter_options.org,
        org_tree=org_tree,
        flow_stage_options=funnel_filter_options(),
        auth_mode=AUTH_MODE,
    )
