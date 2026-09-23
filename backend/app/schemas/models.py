"""API 응답 모델.

계산 결과(테이블/차트 데이터)는 legacy 계산 함수의 산출물을 그대로 dict/list로
전달한다 - 편집 기능이 붙기 전까지는 스키마가 자주 바뀔 수 있어, 지금 모든
중첩 구조를 엄격한 Pydantic 모델로 못박기보다는 상위 엔벨로프만 타입을 주고
프론트 TS 인터페이스가 실질적인 계약 역할을 하도록 한다.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class FilterOptions(BaseModel):
    org: list[str]
    leader_opinion: list[str]
    center_need: list[str]
    team: list[str]
    part: list[str]


class MetaResponse(BaseModel):
    current_month: int
    current_label: str
    team_name: str
    dashboard_title: str
    filter_options: FilterOptions
    org_options: list[str]
    # 팀 → PJT → 파트 3단계 트리. 노드 형태: {level, key, label, children}.
    # org_options/filter_options는 하위호환을 위해 그대로 유지한다.
    org_tree: list[dict[str, Any]]
    # 사이드바 "투자 진행 흐름 구분" 필터 옵션 — 종합현황 퍼널과 동일한 key/label 16개(count 제외).
    flow_stage_options: list[dict[str, Any]]
    # "local"(아이디/비밀번호) 또는 "sso"(OIDC 리다이렉트) — 프론트가 로그인 UI를 분기하는 근거.
    auth_mode: str


class DashboardResponse(BaseModel):
    selected_org: str
    org_options: list[str]
    executive_kpi: dict[str, Any]
    progress_funnel: list[dict[str, Any]]
    monthly_flow: list[dict[str, Any]]
    detail_columns: list[dict[str, Any]]
    detail_search_keys: list[str]
    detail_rows: list[dict[str, Any]]


class StatusDetailResponse(BaseModel):
    review_monitoring: dict[str, Any]
    contract_monitoring: dict[str, Any]
    execution_monitoring: dict[str, Any]
