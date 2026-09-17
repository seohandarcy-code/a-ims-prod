"""app/calc/org.py의 조직 트리/필터가 팀명에 관계없이 동작하는지 검증한다.

2026-09-17 이전에는 filter_by_selected_org()가 "전체" 센티널(PJT_TOTAL_LABEL)과
실제 팀명이 우연히 같을 때만 팀 단위 선택이 동작했다(팀이 1개뿐이라 안 들켰을 뿐).
여기서는 서로 다른 이름의 팀 2개가 섞인 가상의 데이터로, 각 팀을 선택했을 때
그 팀의 행만 반환되는지 확인한다 — 실제 raw 데이터에 새 팀이 들어와도 자동으로
동작해야 한다는 요구사항의 회귀 방지 테스트.
"""
from __future__ import annotations

import pandas as pd

from app.calc.org import PJT_TOTAL_LABEL, build_org_tree, filter_by_selected_org
from app.data.columns import COL


def _make_multi_team_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            COL["team"]: ["인프라AX/PI기술팀", "인프라AX/PI기술팀", "가상팀B"],
            COL["org"]: ["시스템_PJT", "자동화_PJT", "다른_PJT"],
            COL["part"]: ["인프라시스템개발", "위험작업자동화", "다른파트"],
        }
    )


def test_filter_by_selected_org_total_label_returns_everything():
    df = _make_multi_team_df()
    result = filter_by_selected_org(df, PJT_TOTAL_LABEL)
    assert len(result) == len(df)


def test_filter_by_selected_org_matches_any_team_by_name():
    df = _make_multi_team_df()

    team_a = filter_by_selected_org(df, "인프라AX/PI기술팀")
    assert set(team_a[COL["team"]]) == {"인프라AX/PI기술팀"}
    assert len(team_a) == 2

    team_b = filter_by_selected_org(df, "가상팀B")
    assert set(team_b[COL["team"]]) == {"가상팀B"}
    assert len(team_b) == 1


def test_filter_by_selected_org_still_matches_pjt_and_part():
    df = _make_multi_team_df()

    pjt_only = filter_by_selected_org(df, "시스템_PJT")
    assert len(pjt_only) == 1

    part_only = filter_by_selected_org(df, "다른_PJT::다른파트")
    assert len(part_only) == 1


def test_build_org_tree_creates_one_node_per_distinct_team():
    df = _make_multi_team_df()
    tree = build_org_tree(df)

    assert {node["key"] for node in tree} == {"인프라AX/PI기술팀", "가상팀B"}
