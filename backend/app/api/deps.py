"""legacy apply_filters(사이드바 공통 필터)와 조직 버튼 필터 이식."""
from __future__ import annotations

import pandas as pd
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.state import get_auth_store
from app.calc.stage import funnel_key_mask
from app.data.columns import COL
from app.data.store import DataStore, get_store

CommonFilterDep = get_store

_bearer_scheme = HTTPBearer(auto_error=False)


def require_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> str:
    """Authorization: Bearer <token> 헤더를 검증하고 토큰을 반환한다."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="인증이 필요합니다.")

    token = credentials.credentials
    if not get_auth_store().is_valid(token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="세션이 유효하지 않습니다.")

    return token


def apply_common_filters(
    df: pd.DataFrame,
    org: list[str] | None,
    leader_opinion: list[str] | None,
    center_need: list[str] | None,
    team: list[str] | None = None,
    part: list[str] | None = None,
    flow_stage: list[str] | None = None,
) -> pd.DataFrame:
    filtered = df

    filter_map = {
        COL["org"]: org,
        COL["leader_opinion"]: leader_opinion,
        COL["center_need"]: center_need,
        COL["team"]: team,
    }

    for column, selected in filter_map.items():
        if selected is None:
            continue
        filtered = filtered[filtered[column].isin(selected)]

    if part is not None:
        # 파트는 "PJT::파트" 복합키로 전달된다 — PJT 간 동명 파트가 생겨도
        # (PJT, 파트) 쌍으로 걸러야 안전하므로 단순 isin이 아니라 쌍 매칭을 쓴다.
        allowed_pairs = {tuple(key.split("::", 1)) for key in part if "::" in key}
        filtered = filtered[
            filtered.apply(
                lambda row: (row[COL["org"]], row[COL["part"]]) in allowed_pairs,
                axis=1,
            )
        ]

    if flow_stage:
        # "투자 진행 흐름 구분"의 16개 항목 중 선택된 것들을 OR로 합친다(종합현황 퍼널과 동일 기준).
        mask = pd.Series(False, index=filtered.index)
        for key in flow_stage:
            mask = mask | funnel_key_mask(filtered, key)
        filtered = filtered[mask]

    return filtered


class CommonFilters:
    """사이드바 필터 쿼리 파라미터 (조직 5종 + 팀/파트 계층 2종 + 투자 진행 흐름 구분)."""

    def __init__(
        self,
        org: list[str] | None = Query(default=None),
        leader_opinion: list[str] | None = Query(default=None),
        center_need: list[str] | None = Query(default=None),
        team: list[str] | None = Query(default=None),
        part: list[str] | None = Query(default=None),
        flow_stage: list[str] | None = Query(default=None),
    ) -> None:
        self.org = org
        self.leader_opinion = leader_opinion
        self.center_need = center_need
        self.team = team
        self.part = part
        self.flow_stage = flow_stage

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        return apply_common_filters(
            df,
            self.org,
            self.leader_opinion,
            self.center_need,
            self.team,
            self.part,
            self.flow_stage,
        )
