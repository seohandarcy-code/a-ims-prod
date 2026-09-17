"""legacy/web_new5_transfer_minus_detail.py의 COL 매핑 설정 영역 이식."""
from __future__ import annotations

COL = {
    "no": "NO",
    "team": "팀",
    "org": "PJT",
    "part": "파트",
    "owner_before": "담당자(변경전)",
    "owner": "담당자",
    "wbs": "WBS_Code",
    "title_before": "투자명(변경전)",
    "title": "투자명",
    "plan_out": "계획_외",
    "plan_type": "계획구분",
    "leader_plan_month": "팀장심의예정",
    "leader_date": "팀장심의일자",
    "review_month": "심의진행_월",
    "leader_opinion": "팀장심의_의견",
    "center_need": "센터장_심의필요",
    "center_opinion": "센터장_심의의견",
    "planned_cost": "투자비(계획)",
    "invest_cost": "투자비",
    "increase": "증액",
    "transfer": "예산전용",
    "po_done": "기본품의완료",
    "contract_done": "계약등록",
    "contract_month": "계약_월",
    "po_amount": "기본품의금액",
    "progress_stage": "기성단계",
    "progress_month": "기성_월",
    "progress_amount": "기성_금액",
    "progress_month_pred": "기성_월_예측",
    "progress_amount_pred": "기성_금액_예측",
    "executed_amount": "기성처리금액_합계",
    "erp_registered": "ERP등록",
    "irb_review": "IRB심의",
    "it_pms": "IT-PMS",
    "contract_month_input": "계약월_입력",
    "contract_amount_input": "계약금액_입력",
    "contract_complete_flag": "계약완료구분",
    "execution_po_amount": "실행품의금액",
    "investment_complete": "투자완료",
}

MONEY_COLS = [
    COL["planned_cost"],
    COL["invest_cost"],
    COL["increase"],
    COL["transfer"],
    COL["po_amount"],
    COL["executed_amount"],
    COL["execution_po_amount"],
    COL["contract_amount_input"],
]

MONTH_LABELS = [f"{i}월" for i in range(1, 13)]

# 관리자 편집 폼의 필드 타입/안내 문구 — 단일 소스로 여기서만 관리한다.
FIELD_TYPES: dict[str, str] = {
    COL["team"]: "status",
    COL["org"]: "status",
    COL["part"]: "status",
    COL["plan_out"]: "status",
    COL["plan_type"]: "status",
    COL["leader_plan_month"]: "month",
    COL["leader_date"]: "date",
    COL["review_month"]: "month",
    COL["leader_opinion"]: "status",
    COL["center_need"]: "status",
    COL["planned_cost"]: "money",
    COL["invest_cost"]: "money",
    COL["increase"]: "money",
    COL["transfer"]: "money",
    COL["po_done"]: "status",
    COL["contract_done"]: "status",
    COL["contract_month"]: "month",
    COL["po_amount"]: "money",
    COL["progress_month"]: "month_list",
    COL["progress_amount"]: "money_list",
    COL["progress_month_pred"]: "month_list",
    COL["progress_amount_pred"]: "money_list",
    COL["executed_amount"]: "money",
}

FIELD_PLACEHOLDERS: dict[str, str] = {
    COL["team"]: "기존 값에서 선택하거나 입력",
    COL["org"]: "기존 값에서 선택하거나 입력",
    COL["part"]: "기존 값에서 선택하거나 입력",
    COL["plan_out"]: "Y 또는 N",
    COL["plan_type"]: "기존 값에서 선택하거나 입력",
    COL["leader_plan_month"]: "예: 1월",
    COL["leader_date"]: "예: 2026-01-15",
    COL["review_month"]: "예: 1월",
    COL["leader_opinion"]: "기존 값에서 선택하거나 입력",
    COL["center_need"]: "예: 필요 / 불필요",
    COL["planned_cost"]: "숫자만 입력 (예: 550000000)",
    COL["invest_cost"]: "숫자만 입력 (예: 480000000)",
    COL["increase"]: "숫자만 입력 (없으면 0)",
    COL["transfer"]: "숫자만 입력 (없으면 0)",
    COL["po_done"]: "완료 / 미완료",
    COL["contract_done"]: "등록 / 미등록",
    COL["contract_month"]: "예: 1월",
    COL["po_amount"]: "숫자만 입력 (예: 434329602)",
    COL["progress_month"]: "슬래시로 구분 (예: 11월/12월)",
    COL["progress_amount"]: "슬래시로 구분, 월 개수와 동일 (예: 162873600/162873600)",
    COL["progress_month_pred"]: "슬래시로 구분 (예: 11월/12월)",
    COL["progress_amount_pred"]: "슬래시로 구분, 월 개수와 동일 (예: 162873600/162873600)",
    COL["executed_amount"]: "숫자만 입력 (예: 108582400)",
}

# 기성_월/기성_금액, 기성_월_예측/기성_금액_예측 — 슬래시 구분 개수가 서로 일치해야 하는 쌍.
PROGRESS_PAIRS: list[tuple[str, str]] = [
    (COL["progress_month"], COL["progress_amount"]),
    (COL["progress_month_pred"], COL["progress_amount_pred"]),
]

# 조직 트리(팀/PJT/파트) 단일선택 drill-down의 "전체" sentinel.
#
# 2026-09-17 이전에는 이 값이 실제 팀명과 우연히 똑같아야만 "전체 보기"가 동작했다
# (팀이 1개뿐이라 들키지 않았을 뿐, 팀명이 바뀌거나 두 번째 팀이 생기면 즉시 깨지는
# 구조였다). 이제는 `filter_by_selected_org()`가 `팀` 컬럼 값을 직접 매칭하는 분기를
# 따로 가지고 있으므로(app/calc/org.py), 이 상수는 실제 팀/PJT/파트 어떤 값과도 절대
# 겹치지 않는 순수 "필터 없음" 센티널이기만 하면 된다 — 실제 조직명 형태(예: "OO팀",
# "OO_PJT")를 흉내 내지 말 것.
PJT_TOTAL_LABEL = "전체"

SIDEBAR_FILTER_KEYS = ["org", "plan_type", "po_done", "leader_opinion", "center_need"]


def resolve_col(column_key_or_name: str) -> str:
    return COL.get(column_key_or_name, column_key_or_name)


# 한글 헤더 -> COL 키. app/db/* 가 DB 컬럼명(COL 키)과 raw_df 컬럼명(한글 헤더)
# 사이를 오갈 때 쓴다.
HEADER_TO_KEY: dict[str, str] = {header: key for key, header in COL.items()}
