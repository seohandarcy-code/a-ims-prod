"""legacy make_stage_summary 데이터 부분 이식.

품의/계약/집행 판정은 종합현황 KPI와 동일한 is_review_completed/is_contract_completed 기준으로
재정의되었다. 상세현황이 "단계별 상세 모니터링"만 남기면서 함께 쓰이던 전환 흐름/병목 진단/건별
진단 테이블 데이터 함수(stage_flow_data/make_bottleneck_table/make_stage_detail_table)는
소비처가 사라져 제거했다. 종합현황 "투자 진행 흐름 구분" 퍼널(FUNNEL_MASK_KEYS 이하)은 이 변경과
무관하며 그대로 유지한다.
"""
from __future__ import annotations

import pandas as pd

from app.calc.helpers import is_contract_completed, is_review_completed, safe_divide
from app.data.columns import COL


def make_stage_summary(df: pd.DataFrame) -> dict[str, float]:
    """3단계(심의/계약/집행) 요약 — 종합현황 KPI와 동일한 판정 함수/분모를 사용한다.

    total_count는 "진행 투자계획"(Drop 제외) 기준이다 — 종합현황 executive_kpi의
    progress_count(dashboard.py의 plan_progress_df)와 동일한 정의.
    """
    if df.empty:
        total_count = 0
        review_done_count = 0
        contract_count = 0
        execution_po_sum = 0.0
        executed_sum = 0.0
        contract_backlog_count = 0
        investment_done_count = 0
    else:
        total_count = int(df[COL["plan_type"]].isin(["계획", "계획외"]).sum())
        review_mask = df.apply(is_review_completed, axis=1)
        contract_mask = df.apply(is_contract_completed, axis=1)
        review_done_count = int(review_mask.sum())
        contract_count = int(contract_mask.sum())
        execution_po_sum = float(df[COL["execution_po_amount"]].sum())
        executed_sum = float(df[COL["executed_amount"]].sum())
        contract_backlog_count = int((review_mask & ~contract_mask).sum())
        investment_done_count = int((df[COL["investment_complete"]].astype(str).str.strip() == "완료").sum())

    return {
        "total_count": total_count,
        "review_done_count": review_done_count,
        "review_completion_rate": safe_divide(review_done_count, total_count) * 100,
        "review_pending_count": max(total_count - review_done_count, 0),
        "investment_done_count": investment_done_count,
        "contract_count": contract_count,
        "review_to_contract_rate": safe_divide(contract_count, review_done_count) * 100,
        "execution_po_sum": execution_po_sum,
        "executed_sum": executed_sum,
        "amount_execution_rate": safe_divide(executed_sum, execution_po_sum) * 100,
        "contract_backlog_count": contract_backlog_count,
    }


FUNNEL_MASK_KEYS = (
    "plan", "plan_out", "drop", "progress",
    "leader_review", "center_review", "review_incomplete", "review_done",
    "erp", "irb_path", "contract_pending", "contract_done",
    "settled", "unsettled",
)


def _funnel_masks(df: pd.DataFrame) -> dict[str, pd.Series]:
    """종합진행 퍼널 각 항목의 row-level boolean mask.

    make_progress_funnel의 카운트 산출과, 막대 클릭 시 상세 리스트 필터링(funnel_key_mask)이
    이 함수를 공유한다 — 계약완료⊆심의완료, 정산완료⊆계약완료가 실데이터에서 성립함이
    이미 검증되어 있어(0건 위반), 기존의 카운트 차감 방식과 결과가 동일하다.
    """

    def s(col_key: str) -> pd.Series:
        return df[COL[col_key]].astype(str).str.strip()

    plan_type = s("plan_type")
    plan_mask = plan_type == "계획"
    plan_out_mask = plan_type == "계획외"
    drop_mask = plan_type == "Drop"
    progress_mask = plan_mask | plan_out_mask

    center_path = s("center_need") == "필요"
    center_review_mask = center_path & (s("center_opinion") == "승인")
    leader_review_mask = ~center_path & (s("leader_opinion") == "승인")
    review_done_mask = leader_review_mask | center_review_mask
    review_incomplete_mask = progress_mask & ~review_done_mask

    erp_mask = s("erp_registered") == "등록"
    irb_path_mask = (s("irb_review") == "완료") & (s("it_pms") == "완료") & (s("contract_month_input") != "")
    contract_done_mask = erp_mask | irb_path_mask
    contract_pending_mask = review_done_mask & ~contract_done_mask

    settled_mask = s("investment_complete") == "완료"
    unsettled_mask = contract_done_mask & ~settled_mask

    return {
        "plan": plan_mask,
        "plan_out": plan_out_mask,
        "drop": drop_mask,
        "progress": progress_mask,
        "leader_review": leader_review_mask,
        "center_review": center_review_mask,
        "review_incomplete": review_incomplete_mask,
        "review_done": review_done_mask,
        "erp": erp_mask,
        "irb_path": irb_path_mask,
        "contract_pending": contract_pending_mask,
        "contract_done": contract_done_mask,
        "settled": settled_mask,
        "unsettled": unsettled_mask,
    }


def funnel_key_mask(df: pd.DataFrame, key: str) -> pd.Series:
    """종합진행 퍼널 막대 클릭 → 상세 리스트 필터링용 row mask.

    "total"은 전체 True, "investment_done"은 "settled"와 동일한 항목(체크포인트 표시용 별칭)이다.
    """
    if df.empty:
        return pd.Series(False, index=df.index)
    if key == "total":
        return pd.Series(True, index=df.index)
    if key == "investment_done":
        key = "settled"
    return _funnel_masks(df).get(key, pd.Series(False, index=df.index))


# "종합진행 퍼널" 16개 막대의 단일 소스 — (key, label, kind, group). count가 필요한
# make_progress_funnel과, count 없이 key/label만 필요한 사이드 필터(funnel_filter_options)가 함께 쓴다.
# "investment_done"은 "settled"와 동일 마스크를 쓰는 체크포인트 표시용 별칭이다.
FUNNEL_ITEMS: list[tuple[str, str, str, str]] = [
    ("total", "전체 투자계획", "checkpoint", "plan"),
    ("plan", "계획", "component", "plan"),
    ("plan_out", "계획외", "component", "plan"),
    ("drop", "Drop", "component", "plan"),
    ("progress", "진행 투자계획", "checkpoint", "plan"),
    ("leader_review", "팀장 심의", "component", "review"),
    ("center_review", "센터장 심의", "component", "review"),
    ("review_incomplete", "심의 미완료", "component", "review"),
    ("review_done", "심의 완료", "checkpoint", "review"),
    ("erp", "ERP 등록", "component", "contract"),
    ("irb_path", "IRB-ITPMS 계약", "component", "contract"),
    ("contract_pending", "계약 미완료", "component", "contract"),
    ("contract_done", "계약 완료", "checkpoint", "contract"),
    ("settled", "정산 완료", "component", "settle"),
    ("unsettled", "정산 미완료", "component", "settle"),
    ("investment_done", "투자 완료", "checkpoint", "settle"),
]

_FUNNEL_COUNT_KEY_ALIAS = {"investment_done": "settled"}


def make_progress_funnel(df: pd.DataFrame) -> list[dict]:
    """"종합진행 퍼널"(체크포인트 5 + 구성 클러스터 4) 데이터.

    체크포인트: 전체 투자계획 → 진행 투자계획 → 심의 완료 → 계약 완료 → 투자 완료.
    각 체크포인트 사이에는 그 전환을 구성하는 항목들이 별도 막대로 낀다(계획/계획외/Drop 등).
    """
    if df.empty:
        counts = dict.fromkeys(["total", *FUNNEL_MASK_KEYS], 0)
    else:
        masks = _funnel_masks(df)
        counts = {"total": int(len(df)), **{key: int(mask.sum()) for key, mask in masks.items()}}

    return [
        {
            "key": key,
            "label": label,
            "count": counts[_FUNNEL_COUNT_KEY_ALIAS.get(key, key)],
            "kind": kind,
            "group": group,
        }
        for key, label, kind, group in FUNNEL_ITEMS
    ]


def funnel_filter_options() -> list[dict[str, str]]:
    """사이드바 "투자 진행 흐름 구분" 필터 옵션 — make_progress_funnel과 동일한 key/label(count 제외)."""
    return [{"key": key, "label": label} for key, label, _, _ in FUNNEL_ITEMS]
