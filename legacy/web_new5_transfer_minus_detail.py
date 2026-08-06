

from __future__ import annotations

import html
import inspect
import re
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ============================================================
# 1) 설정 영역: 파일명/컬럼명이 바뀌면 이 부분만 우선 수정하세요.
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# DATA_FILE = DATA_DIR / "raw_dt_prediction.dat"
DATA_FILE = DATA_DIR / "raw_new.dat"


CURRENT_YEAR = 2026
CURRENT_MONTH_OVERRIDE: int | None = None

COL = {
    "no": "NO",
    "org": "조직",
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
}

MONEY_COLS = [
    COL["planned_cost"],
    COL["invest_cost"],
    COL["increase"],
    COL["transfer"],
    COL["po_amount"],
    COL["executed_amount"],
]

MONTH_LABELS = [f"{i}월" for i in range(1, 13)]

PJT_ALL_LABEL = "A-infra기술팀"
PJT_TOTAL_LABEL = "A-infra기술팀"

# 색상 기준
# - 조직구분 선택 버튼과 투자 현황 차트의 주요 푸른색은 삼성전자 로고 블루 기준으로 통일합니다.
# - 예상선/기준선은 기존 옅은 푸른색으로 구분합니다.
TAB_SELECTED_BLUE = "#BAE6FD"
SAMSUNG_BLUE = "#1428A0"
LIGHT_BLUE = TAB_SELECTED_BLUE
# 조직별 종합 진행률은 시간 흐름(품의→계약→집행)에 따라
# 옅은 파랑에서 가장 짙은 파랑으로 증가하도록 3단계 색상을 사용합니다.
BLUE_STEP_1 = "#BAE6FD"  # 품의: 시작 단계
BLUE_STEP_2 = "#38BDF8"  # 계약: 중간 단계
BLUE_STEP_3 = "#1428A0"  # 집행: 최종 단계 / 최상위 탭 강조색
EXECUTED_COLOR = SAMSUNG_BLUE
PREDICTED_LINE_COLOR = LIGHT_BLUE
UNEXECUTED_COLOR = "#E2E8F0"


# ============================================================
# 1-1) 운영/유지보수 설정 영역
# - 컬럼명, 필터, KPI, 상세 테이블, 색상/크기 변경은
#   가급적 이 영역만 수정하도록 구성했습니다.
# ============================================================
APP_CONFIG = {
    "team_name": "A-Infra기술팀",
    "dashboard_title": "Investment Management Dashboard '26",
    "page_title": "Investment Management Dashboard '26",
    "page_icon": "📊",
    "layout": "wide",
    "sidebar_state": "collapsed",
    "tab_titles": ["투자 종합현황", "투자 진행 상세현황"],
}

THEME = {
    # 색상 토큰
    "page_bg": "#F8FAFC",
    "card_bg": "#FFFFFF",
    "text_main": "#0F172A",
    "text_muted": "#64748B",
    "text_subtle": "#94A3B8",
    "border": "#E2E8F0",
    "shadow": "0 1px 2px rgba(15, 23, 42, 0.06)",
    "primary": SAMSUNG_BLUE,
    # 상세 리스트 집행률 ProgressColumn 막대색을 짙은 청색으로 통일합니다.
    "tab_selected_accent": SAMSUNG_BLUE,
    "detail_progress_color": SAMSUNG_BLUE,
    "blue_step_1": BLUE_STEP_1,
    "blue_step_2": BLUE_STEP_2,
    "blue_step_3": BLUE_STEP_3,
    "executed": EXECUTED_COLOR,
    "predicted_line": PREDICTED_LINE_COLOR,
    "unexecuted": UNEXECUTED_COLOR,
    # 화면 스케일 토큰
    # 기존 CSS zoom 방식은 Plotly/DataFrame이 실제 컬럼 폭보다 작게 보이는 문제가 있어
    # 기본값은 1.0으로 두고, 본문 최대 폭과 내부 여백으로 100% 화면을 최적화합니다.
    "dashboard_scale": "1.0",
    # 크기 토큰
    # zoom 적용 시 상단이 함께 축소되어 제목이 잘릴 수 있으므로
    # 상단 여백은 넉넉하게 확보합니다.
    "page_padding_top": "4.8rem",
    # 좌우 여백: 현재 버전 대비 양쪽 여백을 다시 절반으로 축소합니다.
    "page_padding_left": "5.55vw",
    "page_padding_right": "5.55vw",
    # 100% 화면에서 너무 넓게 퍼지지 않도록 본문 최대 폭을 둡니다.
    # Plotly와 상세 리스트가 컬럼/본문 폭을 온전히 사용하도록 실제 렌더링 폭 기준으로 설정합니다.
    "content_max_width": "1660px",
    # 네이버 등 대중 포털형 화면처럼 카드 간격은 16~24px 범위로 맞춥니다.
    "column_gap": "1.35rem",
    "row_gap": "0.55rem",
    "section_gap": "0.55rem",
    # 소제목은 대시보드 제목의 절반 크기입니다.
    "small_title_size": "1.5rem",
    "big_title_size": "3.0rem",
    "desc_size": "0.735rem",
    "section_title_size": "1.75rem",
    "chart_subtitle_size": "1.15rem",
    "caption_size": "1.31rem",
    "card_radius": "1rem",
    "dataframe_radius": "0.8rem",
    "metric_label_size": "1.5rem",
    "metric_value_size": "3.0rem",
    "metric_unit_size": "1.5rem",
    # 메트릭 글자 굵기: 기존 label 800, value/unit 900 대비 약 75% 수준으로 조정
    "metric_label_weight": 600,
    "metric_value_weight": 675,
    "metric_unit_weight": 675,
    "metric_card_min_height": "9.4rem",
    "metric_grid_gap": "1.05rem",
    "metric_divider_color": "rgba(71, 85, 105, 0.95)",
    "plot_font_size": 18,
    # 투자종합현황 탭의 4개 주요 차트는 기존 495px의 3/4 수준으로 축소합니다.
    "main_plot_font_size": 14,
    "main_plot_height": 371,
    "plot_height_large": 495,
    "plot_height_medium": 370,
    "plot_height_small": 320,
    # 상세 리스트는 20행까지 보이고, 초과 시 내부 스크롤로 이동합니다.
    "detail_table_height": 735,
    # 두 번째 탭 상태별 막대그래프 두께는 기존 0.70의 3/4 수준입니다.
    "status_bar_width": 0.525,
}

SIDEBAR_FILTERS = [
    {"label": "조직", "column_key": "org"},
    {"label": "계획구분", "column_key": "plan_type"},
    {"label": "품의완료", "column_key": "po_done"},
    {"label": "팀장심의 의견", "column_key": "leader_opinion"},
    {"label": "센터장 심의필요", "column_key": "center_need"},
    # 담당자 필터는 요청에 따라 주석 처리합니다.
    # {"label": "담당자", "column_key": "owner"},
]

KPI_CARDS = [
    {
        "label": "전체 투자건수",
        "metric": "total_count",
        "caption": "26년 팀 투자 계획/계획외/Drop건 합계입니다.",
        "group_divider_after": False,
    },
    {
        "label": "전체 투자금액",
        "metric": "invest_sum",
        "caption": "26년 팀 투자예산입니다.",
        "group_divider_after": True,
    },
    {
        "label": "품의 완료건수",
        "metric": "po_done_count",
        "caption": "기준 월까지 기본품의가 완료된 투자 건 합계입니다.",
        "group_divider_after": False,
    },
    {
        "label": "품의 완료금액",
        "metric": "po_sum",
        "caption": "기준 월까지 기본품의가 완료된 투자금액 합계입니다.",
        "group_divider_after": True,
    },
    {
        "label": "기성처리금액",
        "metric": "executed_sum",
        "caption": "기준 월까지 기성처리완료 금액을 표시합니다.",
        "group_divider_after": False,
    },
    {
        "label": "집행률",
        "metric": "execution_rate",
        "caption": "집행률 = 기성처리금액 / 품의 완료금액 (전체 투자 금액 100% 품의 완료시, 전체 집행률)",
        "group_divider_after": False,
    },
]

DETAIL_SEARCH_COLUMNS = [
    "title",
    "wbs",
    "owner",
    "org",
    "plan_type",
    "po_done",
    "leader_opinion",
    "contract_done",
]

DETAIL_TABLE_COLUMNS = [
    "no",
    "투자 신호등",
    "org",
    "owner",
    "wbs",
    "title",
    "plan_type",
    "leader_plan_month",
    "leader_opinion",
    "center_opinion",
    "po_done",
    "contract_done",
    "contract_month",
    "planned_cost",
    "increase",
    "transfer",
    "invest_cost",
    "po_amount",
    "executed_amount",
    "집행률",
]

DETAIL_SORT_COLUMNS = ["no"]

DETAIL_COLUMN_CONFIGS = {
    "투자 신호등": {
        "type": "text",
        "label": "신호등",
        "help": "🟢 품의완료 / 🟡 팀장심의예정 월 경과 / ⚪ 일반",
    },
    "invest_cost": {"type": "number", "label": "투자비", "format": "%,.1f억"},
    "planned_cost": {"type": "number", "label": "투자비(연초계획)", "format": "%,.1f억"},
    "increase": {"type": "number", "label": "증액", "format": "%,.1f억"},
    "transfer": {"type": "number", "label": "예산전용", "format": "%,.1f억"},
    "leader_opinion": {"type": "text", "label": "팀장심의"},
    "center_opinion": {"type": "text", "label": "센터장심의"},
    "po_done": {"type": "text", "label": "기본품의완료"},
    "contract_done": {"type": "text", "label": "계약등록"},
    "contract_month": {"type": "text", "label": "계약월"},
    "po_amount": {"type": "number", "label": "기본품의금액", "format": "%,.1f억"},
    "executed_amount": {"type": "number", "label": "기성처리금액", "format": "%,.1f억"},
    "집행률": {
        "type": "progress",
        "label": "집행률",
        "min": 0,
        "max": 100,
        "format": "%.1f%%",
        "color": SAMSUNG_BLUE,
    },
}

STATUS_CHARTS = [
    {"title": "계획구분별 건수", "kind": "count_bar", "column_key": "plan_type"},
    {"title": "품의완료 상태", "kind": "count_bar", "column_key": "po_done"},
    {"title": "팀장심의 의견", "kind": "count_bar", "column_key": "leader_opinion"},
    {"title": "계획구분별 투자비 비중", "kind": "amount_pie", "group_key": "plan_type", "amount_key": "invest_cost"},
    {"title": "변경/증감 발생 건수", "kind": "change_bar"},
]

MAIN_LAYOUT = {
    # 100% 화면에서 조직 필터가 너무 좁거나 차트가 과하게 벌어지지 않도록 비율을 보정합니다.
    "execution_columns": [0.62, 1.28, 1.28],
    "investment_detail_columns": [0.62, 1.28, 1.28],
    "monthly_compare_columns": 3,
    "status_columns": 5,
}

# ============================================================
# 2) 화면 설정 / CSS
# ============================================================
st.set_page_config(
    page_title=APP_CONFIG["page_title"],
    page_icon=APP_CONFIG["page_icon"],
    layout=APP_CONFIG["layout"],
    initial_sidebar_state=APP_CONFIG["sidebar_state"],
)

def css_value(name: str) -> str:
    return str(THEME[name])


def render_global_css() -> None:
    """대시보드 전체 UI 스타일입니다.

    색상·크기·간격은 THEME 딕셔너리에서 관리합니다.
    CSS를 직접 찾기보다 THEME 값을 먼저 수정하는 방식으로 운영하세요.
    """
    st.markdown(
        f"""
        <style>
        /*
        Plotly 차트와 Streamlit DataFrame은 부모 컨테이너의 실제 픽셀 폭을 기준으로
        렌더링됩니다. CSS zoom을 사용하면 컬럼은 넓은데 차트/표만 작게 보일 수 있어
        zoom 대신 실제 본문 폭과 컨테이너 100% 규칙으로 맞춥니다.
        */
        :root {{
            --dashboard-scale: {css_value('dashboard_scale')};
            --dashboard-scale-inverse: calc(1 / var(--dashboard-scale));
            --primary-color: {css_value('primary')} !important;
            --st-primary-color: {css_value('primary')} !important;
            accent-color: {css_value('primary')} !important;
        }}

        .main .block-container,
        section[data-testid="stMain"] .block-container,
        div[data-testid="stMainBlockContainer"] {{
            padding-top: {css_value('page_padding_top')} !important;
            /* 고정 헤더/브라우저 렌더링 차이로 상단 글씨가 잘리는 것을 방지합니다. */
            scroll-margin-top: 4rem !important;
            padding-bottom: 2rem !important;
            padding-left: 0 !important;
            padding-right: 0 !important;
            width: min(
                calc(100vw - ({css_value('page_padding_left')} + {css_value('page_padding_right')})),
                {css_value('content_max_width')}
            ) !important;
            max-width: min(
                calc(100vw - ({css_value('page_padding_left')} + {css_value('page_padding_right')})),
                {css_value('content_max_width')}
            ) !important;
            margin-left: auto !important;
            margin-right: auto !important;
        }}

        /* 사이드바는 브라우저 100% 기준으로 자연스럽게 유지합니다. */
        section[data-testid="stSidebar"] > div:first-child {{
            width: 100%;
        }}

        /* 100% 화면 기준 컬럼과 행 간격을 균일하게 보정합니다. */
        .main .block-container div[data-testid="stHorizontalBlock"],
        section[data-testid="stMain"] .block-container div[data-testid="stHorizontalBlock"],
        div[data-testid="stMainBlockContainer"] div[data-testid="stHorizontalBlock"] {{
            gap: {css_value('column_gap')} !important;
            align-items: stretch !important;
        }}

        div[data-testid="stPlotlyChart"],
        div[data-testid="stPlotlyChart"] > div,
        div[data-testid="stPlotlyChart"] iframe,
        div[data-testid="stPlotlyChart"] .js-plotly-plot,
        div[data-testid="stPlotlyChart"] .plot-container,
        div[data-testid="stPlotlyChart"] .svg-container {{
            width: 100% !important;
            max-width: 100% !important;
        }}

        div[data-testid="stPlotlyChart"] {{
            margin-bottom: 0.35rem !important;
        }}

        .dashboard-row-spacer {{
            height: {css_value('row_gap')};
        }}

        .dashboard-section-spacer {{
            height: {css_value('section_gap')};
        }}

        @media (max-width: 1200px) {{
            .main .block-container,
            section[data-testid="stMain"] .block-container,
            div[data-testid="stMainBlockContainer"] {{
                width: calc(100vw - 3.75rem) !important;
                max-width: calc(100vw - 3.75rem) !important;
                padding-left: 0 !important;
                padding-right: 0 !important;
            }}
        }}

        @media (max-width: 760px) {{
            .main .block-container,
            section[data-testid="stMain"] .block-container,
            div[data-testid="stMainBlockContainer"] {{
                width: calc(100vw - 2rem) !important;
                max-width: calc(100vw - 2rem) !important;
                padding-left: 0 !important;
                padding-right: 0 !important;
            }}

            section[data-testid="stSidebar"] > div:first-child {{
                width: 100%;
            }}
        }}

        .small-title {{
            font-size: {css_value('small_title_size')};
            color: {css_value('text_muted')};
            margin-bottom: 0.18rem;
            line-height: 1.12;
        }}

        .big-title {{
            font-size: {css_value('big_title_size')};
            font-weight: 800;
            letter-spacing: -0.04em;
            margin-top: 0;
            margin-bottom: 0.45rem;
            line-height: 1.08;
            color: {css_value('text_main')};
        }}

        .desc {{
            font-size: {css_value('desc_size')};
            color: #475569;
            margin-bottom: 1.45rem;
        }}

        .section-title {{
            font-size: {css_value('section_title_size')};
            font-weight: 750;
            margin-top: 0.45rem;
            margin-bottom: 0.45rem;
            color: {css_value('text_main')};
        }}

        .chart-subtitle {{
            font-size: {css_value('chart_subtitle_size')};
            font-weight: 750;
            margin-top: 0.15rem;
            margin-bottom: 0.4rem;
            color: {css_value('text_main')};
        }}

        .filter-card {{
            background-color: {css_value('card_bg')};
            border: 1px solid {css_value('border')};
            border-radius: {css_value('card_radius')};
            padding: 1rem;
            box-shadow: {css_value('shadow')};
        }}

        div[data-testid="stDataFrame"],
        div[data-testid="stDataFrame"] > div {{
            width: 100% !important;
            max-width: 100% !important;
        }}

        div[data-testid="stDataFrame"] {{
            border: 1px solid {css_value('border')};
            border-radius: {css_value('dataframe_radius')};
        }}

        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(6, minmax(0, 1fr));
            gap: {css_value('metric_grid_gap')};
            align-items: stretch;
            margin-bottom: 0.45rem;
        }}

        .kpi-card {{
            background-color: {css_value('card_bg')};
            border: 1px solid {css_value('border')};
            padding: 1.15rem 1.15rem;
            border-radius: {css_value('card_radius')};
            box-shadow: {css_value('shadow')};
            min-height: {css_value('metric_card_min_height')};
            display: flex;
            flex-direction: column;
            justify-content: center;
            position: relative;
        }}

        .kpi-card.group-divider::after {{
            content: "";
            position: absolute;
            top: 14%;
            right: -0.47rem;
            width: 2px;
            height: 76%;
            background: linear-gradient(
                to bottom,
                rgba(226, 232, 240, 0),
                {css_value('metric_divider_color')},
                rgba(226, 232, 240, 0)
            );
        }}

        .kpi-label {{
            font-size: {css_value('metric_label_size')};
            line-height: 1.25;
            font-weight: {css_value('metric_label_weight')};
            color: #475569;
            margin-bottom: 0.35rem;
            white-space: nowrap;
        }}

        .kpi-value {{
            font-size: {css_value('metric_value_size')};
            line-height: 1.15;
            font-weight: {css_value('metric_value_weight')};
            color: {css_value('text_main')};
            letter-spacing: -0.04em;
            white-space: nowrap;
            display: flex;
            align-items: baseline;
            gap: 0.2em;
        }}

        .kpi-unit {{
            font-size: {css_value('metric_unit_size')};
            line-height: 1;
            font-weight: {css_value('metric_unit_weight')};
            letter-spacing: -0.02em;
        }}

        .kpi-caption-grid {{
            display: grid;
            grid-template-columns: repeat(6, minmax(0, 1fr));
            gap: {css_value('metric_grid_gap')};
            align-items: start;
            margin-top: -0.1rem;
            margin-bottom: 0.45rem;
        }}

        .kpi-caption-outside {{
            font-size: {css_value('desc_size')};
            line-height: 1.35;
            color: {css_value('text_muted')};
            padding: 0 0.25rem;
            word-break: keep-all;
        }}

        @media (max-width: 1200px) {{
            .kpi-grid,
            .kpi-caption-grid {{
                grid-template-columns: repeat(3, minmax(0, 1fr));
            }}

            .kpi-card.group-divider::after {{
                display: none;
            }}
        }}

        @media (max-width: 760px) {{
            .kpi-grid,
            .kpi-caption-grid {{
                grid-template-columns: repeat(1, minmax(0, 1fr));
            }}
        }}

        div[data-testid="stButton"] > button[kind="primary"] {{
            background-color: {css_value('primary')} !important;
            border-color: {css_value('primary')} !important;
            color: #FFFFFF !important;
            font-weight: 750 !important;
        }}

        div[data-testid="stButton"] > button[kind="primary"]:hover {{
            background-color: {css_value('primary')} !important;
            border-color: {css_value('primary')} !important;
            color: #FFFFFF !important;
            filter: brightness(0.97);
        }}

        div[data-testid="stButton"] > button[kind="primary"] * {{
            color: #FFFFFF !important;
        }}

        div[data-testid="stCaptionContainer"] {{
            font-size: {css_value('caption_size')} !important;
        }}

        /* 행 구분선 주변 여백을 줄여 탭 내 세로 간격을 압축합니다. */
        div[data-testid="stDivider"] {{
            margin-top: 0.35rem !important;
            margin-bottom: 0.35rem !important;
        }}

        div[data-testid="stDivider"] > div {{
            margin-top: 0.35rem !important;
            margin-bottom: 0.35rem !important;
        }}

        button[data-baseweb="tab"] {{
            border-radius: 0.75rem 0.75rem 0 0 !important;
            transition: all 0.15s ease-in-out;
            background-color: transparent !important;
        }}

        button[data-baseweb="tab"] p {{
            color: {css_value('text_subtle')} !important;
            font-weight: 650 !important;
        }}

        /* 탭 자체를 파란 배경으로 칠하지 않고, 선택 시 하단 강조선만 짙은 푸른색으로 변경합니다. */
        button[data-baseweb="tab"][aria-selected="true"] {{
            background-color: transparent !important;
            border-bottom-color: {css_value('blue_step_3')} !important;
        }}

        button[data-baseweb="tab"][aria-selected="true"] p {{
            color: {css_value('text_main')} !important;
            font-weight: 750 !important;
        }}

        div[data-baseweb="tab-highlight"] {{
            background-color: {css_value('blue_step_3')} !important;
        }}

        div[data-baseweb="tab-border"] {{
            background-color: {css_value('border')} !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


render_global_css()



# ============================================================
# 3) 공통 함수
# ============================================================
def money_eok(value: float | int | None) -> float:
    if value is None or pd.isna(value):
        return 0.0
    return float(value) / 100_000_000


def fmt_eok(value: float | int | None, digit: int = 1) -> str:
    return f"{money_eok(value):,.{digit}f} 억"


def fmt_pct(value: float | int | None, digit: int = 1) -> str:
    if value is None or pd.isna(value):
        return "0.0 %"
    return f"{float(value):,.{digit}f} %"


def safe_divide(numerator: float, denominator: float) -> float:
    if denominator is None or denominator == 0 or pd.isna(denominator):
        return 0.0
    return float(numerator) / float(denominator)


def clean_money_series(series: pd.Series) -> pd.Series:
    cleaned = (
        series.astype(str)
        .str.replace("원", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.strip()
    )
    cleaned = cleaned.replace({"": "0", "nan": "0", "None": "0", "-": "0"})
    return pd.to_numeric(cleaned, errors="coerce").fillna(0)


def detect_delimiter(path: str | Path, encoding: str) -> str:
    with open(path, "r", encoding=encoding, errors="ignore") as f:
        first_line = f.readline()

    candidates = ["\t", "|", ";"]
    counts = {sep: first_line.count(sep) for sep in candidates}
    best_sep = max(counts, key=counts.get)

    return best_sep if counts[best_sep] > 0 else "\t"


@st.cache_data(show_spinner=False)
def read_dat(path: str) -> pd.DataFrame:
    encodings = ["utf-8-sig", "utf-8", "cp949", "euc-kr"]
    last_error: Exception | None = None

    for encoding in encodings:
        try:
            sep = detect_delimiter(path, encoding)

            df = pd.read_csv(
                path,
                sep=sep,
                dtype=str,
                encoding=encoding,
                keep_default_na=False,
                na_values=[],
            )

            df.columns = [str(c).strip() for c in df.columns]
            df = df.loc[:, [c for c in df.columns if c and not c.startswith("Unnamed")]]

            return df

        except Exception as exc:
            last_error = exc
            continue

    raise RuntimeError(f"DAT 파일을 읽지 못했습니다: {path}\n{last_error}")


def extract_month(value) -> int | None:
    if value is None or pd.isna(value):
        return None

    if isinstance(value, (int, float)) and not pd.isna(value):
        month = int(value)
        return month if 1 <= month <= 12 else None

    text = str(value).strip()

    if not text:
        return None

    match = re.search(r"(1[0-2]|[1-9])\s*월", text)
    if match:
        return int(match.group(1))

    match = re.search(rf"{CURRENT_YEAR}[-./](1[0-2]|0?[1-9])", text)
    if match:
        return int(match.group(1))

    match = re.search(r"(?:^|[-./])(1[0-2]|0?[1-9])(?:$|[-./])", text)
    if match:
        return int(match.group(1))

    if text.isdigit():
        month = int(text)
        return month if 1 <= month <= 12 else None

    return None


def parse_month_list(value) -> list[int]:
    if value is None or pd.isna(value):
        return []

    text = str(value).strip()

    if not text:
        return []

    month_matches = re.findall(r"(1[0-2]|[1-9])\s*월", text)

    if month_matches:
        return [int(m) for m in month_matches]

    months = []

    for token in re.split(r"[,/|;]+", text):
        month = extract_month(token)

        if month is not None:
            months.append(month)

    return months


def parse_money_list(value) -> list[float]:
    if value is None or pd.isna(value):
        return []

    text = str(value).strip()

    if not text:
        return []

    text = text.replace("원", "").replace(" ", "")

    if any(sep in text for sep in ["/", "|", ";"]):
        tokens = re.split(r"[/|;]+", text)
        amounts = []

        for token in tokens:
            token = token.replace(",", "").strip()

            if not token:
                continue

            try:
                amounts.append(float(token))
            except ValueError:
                continue

        return amounts

    money_patterns = re.findall(r"\d{1,3}(?:,\d{3})+|\d+", text)

    amounts = []

    for token in money_patterns:
        token = token.replace(",", "").strip()

        if not token:
            continue

        try:
            amounts.append(float(token))
        except ValueError:
            continue

    return amounts


def unique_sorted(series: pd.Series) -> list[str]:
    values = [
        str(v).strip()
        for v in series.dropna().unique().tolist()
        if str(v).strip()
    ]

    return sorted(values)


def is_po_completed_value(value) -> bool:
    status = str(value).strip()

    completed = (
        status in ["완료", "Y", "y", "Yes", "YES", "yes", "O", "o", "완료됨", "품의완료"]
        or (
            "완료" in status
            and not any(block in status for block in ["미완료", "미완", "미진행"])
        )
    )

    return completed


def is_contract_registered_value(value) -> bool:
    status = str(value).strip()

    registered = (
        status in ["완료", "Y", "y", "Yes", "YES", "yes", "O", "o", "등록", "계약등록"]
        or (
            "완료" in status
            and not any(block in status for block in ["미완료", "미완", "미진행"])
        )
    )

    return registered


def count_contract_registered(df: pd.DataFrame) -> int:
    if df.empty or COL["contract_done"] not in df.columns:
        return 0

    return int(df[COL["contract_done"]].map(is_contract_registered_value).sum())


def count_po_completed(df: pd.DataFrame) -> int:
    if df.empty or COL["po_done"] not in df.columns:
        return 0

    return int(df[COL["po_done"]].map(is_po_completed_value).sum())


def make_invest_signal(row: pd.Series, current_month: int) -> str:
    """
    투자 신호등 기준
    - 품의완료가 완료이면 초록색
    - 품의완료가 완료가 아니고, 현재 월 기준 팀장심의예정 월이 지났으면 노란색
    - 그 외는 색깔 없는 신호등
    """
    if is_po_completed_value(row.get(COL["po_done"], "")):
        return "🟢"

    planned_month = extract_month(row.get(COL["leader_plan_month"], ""))

    if planned_month is not None and planned_month < current_month:
        return "🟡"

    return "⚪"


def infer_current_month(df: pd.DataFrame) -> int:
    if CURRENT_MONTH_OVERRIDE is not None:
        if 1 <= CURRENT_MONTH_OVERRIDE <= 12:
            return CURRENT_MONTH_OVERRIDE

        st.warning("CURRENT_MONTH_OVERRIDE는 1~12 사이의 숫자여야 합니다. 자동 추정으로 진행합니다.")

    months: list[int] = []

    if COL["progress_month"] in df.columns:
        for value in df[COL["progress_month"]]:
            months.extend(parse_month_list(value))

    if COL["review_month"] in df.columns:
        for value in df[COL["review_month"]]:
            month = extract_month(value)

            if month is not None:
                months.append(month)

    if COL["leader_date"] in df.columns:
        for value in df[COL["leader_date"]]:
            month = extract_month(value)

            if month is not None:
                months.append(month)

    months = [m for m in months if 1 <= m <= 12]

    if months:
        return max(months)

    return date.today().month


@st.cache_data(show_spinner=False)
def load_current_data() -> tuple[pd.DataFrame, int, str]:
    if not DATA_FILE.exists():
        st.error("DAT 파일을 찾지 못했습니다. app.py와 같은 폴더의 data 폴더에 넣어주세요.")
        st.code(str(DATA_FILE))
        st.stop()

    raw = read_dat(str(DATA_FILE))
    data = normalize_data(raw)
    validate_runtime_config(data)

    current_month = infer_current_month(data)
    current_label = f"{CURRENT_YEAR}년 {current_month}월"

    data["기준월"] = current_label
    data["기준월_숫자"] = current_month

    return data, current_month, current_label


def normalize_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    required_cols = list(COL.values())
    missing_cols = [c for c in required_cols if c not in df.columns]

    if missing_cols:
        st.error("필수 컬럼이 누락되었습니다. 설정 영역의 COL 매핑을 확인하세요.")
        st.code("\n".join(missing_cols))
        st.stop()

    df[COL["no"]] = pd.to_numeric(df[COL["no"]], errors="coerce").fillna(0).astype(int)

    for c in MONEY_COLS:
        df[c] = clean_money_series(df[c])

    text_cols = [c for c in df.columns if c not in MONEY_COLS and c != COL["no"]]

    for c in text_cols:
        df[c] = df[c].where(df[c].notna(), "").astype(str).str.strip()

    df["담당자변경"] = np.where(
        df[COL["owner_before"]].astype(str).str.strip()
        == df[COL["owner"]].astype(str).str.strip(),
        "변경없음",
        "변경",
    )

    df["투자명변경"] = np.where(
        df[COL["title_before"]].astype(str).str.strip()
        == df[COL["title"]].astype(str).str.strip(),
        "변경없음",
        "변경",
    )

    df["집행률"] = np.where(
        df[COL["po_amount"]] > 0,
        df[COL["executed_amount"]] / df[COL["po_amount"]] * 100,
        0,
    )

    df["품의율"] = np.where(
        df[COL["invest_cost"]] > 0,
        df[COL["po_amount"]] / df[COL["invest_cost"]] * 100,
        0,
    )

    df["미집행금액"] = (
        df[COL["po_amount"]] - df[COL["executed_amount"]]
    ).clip(lower=0)

    df["심의예정월_숫자"] = df[COL["leader_plan_month"]].map(extract_month)
    df["심의진행월_숫자"] = df[COL["review_month"]].map(extract_month)

    return df



def resolve_col(column_key_or_name: str) -> str:
    """COL 키 또는 실제 데이터 컬럼명을 실제 컬럼명으로 변환합니다."""
    return COL.get(column_key_or_name, column_key_or_name)


def existing_columns(df: pd.DataFrame, column_keys_or_names: list[str]) -> list[str]:
    """설정에 적힌 컬럼 중 실제 데이터프레임에 존재하는 컬럼만 반환합니다."""
    return [resolve_col(c) for c in column_keys_or_names if resolve_col(c) in df.columns]


def make_streamlit_column_config() -> dict:
    """상세 테이블 컬럼 설정을 DETAIL_COLUMN_CONFIGS에서 생성합니다."""
    configs = {}

    for column_key_or_name, spec in DETAIL_COLUMN_CONFIGS.items():
        column = resolve_col(column_key_or_name)
        column_type = spec.get("type")
        label = spec.get("label", column)

        if column_type == "text":
            configs[column] = st.column_config.TextColumn(
                label,
                help=spec.get("help"),
            )
        elif column_type == "number":
            configs[column] = st.column_config.NumberColumn(
                label,
                format=spec.get("format"),
            )
        elif column_type == "progress":
            progress_kwargs = {
                "min_value": spec.get("min", 0),
                "max_value": spec.get("max", 100),
                "format": spec.get("format", "%.1f%%"),
            }

            # Streamlit 1.58+에서는 ProgressColumn에 color 인자가 있어
            # 상세 리스트 집행률 막대색을 직접 지정할 수 있습니다.
            # 구버전 Streamlit에서는 color 인자를 빼고 CSS/primary 색상 보정에 맡깁니다.
            progress_color = spec.get("color") or THEME.get("detail_progress_color")
            try:
                if progress_color and "color" in inspect.signature(st.column_config.ProgressColumn).parameters:
                    progress_kwargs["color"] = progress_color
            except (TypeError, ValueError):
                pass

            configs[column] = st.column_config.ProgressColumn(
                label,
                **progress_kwargs,
            )

    return configs


def validate_runtime_config(df: pd.DataFrame) -> None:
    """운영 중 설정 오류를 빠르게 발견하기 위한 가벼운 점검입니다."""
    optional_column_keys: list[str] = []

    for spec in SIDEBAR_FILTERS:
        optional_column_keys.append(spec["column_key"])

    optional_column_keys.extend(DETAIL_SEARCH_COLUMNS)
    optional_column_keys.extend(DETAIL_TABLE_COLUMNS)
    optional_column_keys.extend(DETAIL_SORT_COLUMNS)

    for spec in STATUS_CHARTS:
        for key_name in ["column_key", "group_key", "amount_key"]:
            if key_name in spec:
                optional_column_keys.append(spec[key_name])

    missing_optional = sorted(
        {
            resolve_col(column_key)
            for column_key in optional_column_keys
            if resolve_col(column_key) not in df.columns
            and resolve_col(column_key) not in ["투자 신호등", "집행률", "담당자변경", "투자명변경"]
        }
    )

    if missing_optional:
        st.sidebar.warning(
            "설정에는 있으나 데이터에 없는 컬럼이 있습니다: "
            + ", ".join(missing_optional)
        )


def apply_standard_plot_layout(
    fig: go.Figure,
    *,
    height: int | None = None,
    top_margin: int = 45,
) -> go.Figure:
    """차트 공통 높이·여백·폰트 규칙입니다."""
    fig.update_layout(
        autosize=True,
        width=None,
        height=height or THEME["plot_height_small"],
        margin=dict(l=10, r=10, t=top_margin, b=10),
        font=dict(size=THEME["plot_font_size"]),
    )
    return fig


def force_full_width_plot(fig: go.Figure) -> go.Figure:
    """Plotly가 Streamlit 컬럼의 실제 폭을 온전히 쓰도록 공통 보정합니다."""
    fig.update_layout(autosize=True, width=None)
    return fig


def apply_main_chart_layout(fig: go.Figure) -> go.Figure:
    """투자종합현황 탭 4개 주요 차트의 높이와 글자 크기 공통 보정입니다."""
    font_size = THEME["main_plot_font_size"]
    fig.update_layout(
        height=THEME["main_plot_height"],
        font=dict(size=font_size),
        margin=dict(l=14, r=14, t=34, b=14),
        legend=dict(font=dict(size=font_size)),
        xaxis=dict(tickfont=dict(size=font_size), title_font=dict(size=font_size)),
        yaxis=dict(tickfont=dict(size=font_size), title_font=dict(size=font_size)),
        yaxis2=dict(tickfont=dict(size=font_size), title_font=dict(size=font_size)),
    )
    fig.update_traces(textfont=dict(size=font_size), selector=dict(type="bar"))
    fig.update_traces(textfont=dict(size=font_size), selector=dict(type="scatter"))
    return fig


def apply_org_order_to_horizontal_bar(fig: go.Figure, org_order: list[str]) -> go.Figure:
    """조직구분 필터와 동일한 순서로 가로 막대 차트의 Y축을 정렬합니다."""
    fig.update_yaxes(
        categoryorder="array",
        categoryarray=org_order,
        autorange="reversed",
    )
    return fig

def make_filter_state_key(column: str, label: str) -> str:
    """사이드바 버튼 필터의 session_state 키를 안전하게 생성합니다."""
    safe = re.sub(r"[^0-9A-Za-z가-힣_]+", "_", f"{column}_{label}")
    return f"sidebar_button_filter_{safe}"


def show_sidebar_button_multiselect(label: str, options: list[str], state_key: str) -> list[str]:
    """multiselect 대신 버튼형 다중 선택 UI를 표시합니다."""
    st.sidebar.markdown(f"**{label}**")

    if state_key not in st.session_state:
        st.session_state[state_key] = list(options)

    selected = [value for value in st.session_state[state_key] if value in options]
    st.session_state[state_key] = selected

    control_cols = st.sidebar.columns(2)
    with control_cols[0]:
        if st.button("전체", key=f"{state_key}_all", use_container_width=True):
            st.session_state[state_key] = list(options)
            st.rerun()
    with control_cols[1]:
        if st.button("해제", key=f"{state_key}_clear", use_container_width=True):
            st.session_state[state_key] = []
            st.rerun()

    # 사이드바 폭을 고려해 옵션 버튼은 2열로 배치합니다.
    option_cols = st.sidebar.columns(2)
    for idx, option in enumerate(options):
        is_selected = option in selected
        with option_cols[idx % 2]:
            if st.button(
                str(option),
                key=f"{state_key}_{idx}_{option}",
                use_container_width=True,
                type="primary" if is_selected else "secondary",
            ):
                next_selected = set(selected)
                if is_selected:
                    next_selected.discard(option)
                else:
                    next_selected.add(option)

                st.session_state[state_key] = [value for value in options if value in next_selected]
                st.rerun()

    st.sidebar.caption(f"선택 {len(selected):,}/{len(options):,}")
    return selected


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    """사이드바 공통 필터입니다.

    필터 추가/삭제/라벨 변경은 SIDEBAR_FILTERS만 수정하면 됩니다.
    필터 UI는 버튼형 다중 선택 방식입니다.
    """
    filtered = df.copy()

    st.sidebar.markdown("### 공통 필터")

    for filter_spec in SIDEBAR_FILTERS:
        label = filter_spec["label"]
        column = resolve_col(filter_spec["column_key"])

        if column not in filtered.columns:
            st.sidebar.caption(f"필터 제외: '{label}' 컬럼을 찾지 못했습니다.")
            continue

        options = unique_sorted(filtered[column])
        state_key = make_filter_state_key(column, label)
        selected = show_sidebar_button_multiselect(label, options, state_key)

        if selected:
            filtered = filtered[filtered[column].isin(selected)]
        else:
            filtered = filtered.iloc[0:0]

        st.sidebar.markdown("---")

    return filtered

def monthly_progress_table(
    df: pd.DataFrame,
    current_month: int | None = None,
) -> pd.DataFrame:
    rows = []
    pred_rows = []

    for _, row in df.iterrows():
        months = parse_month_list(row[COL["progress_month"]])
        amounts = parse_money_list(row[COL["progress_amount"]])

        for month, amount in zip(months, amounts):
            rows.append(
                {
                    "월": month,
                    "조직": row[COL["org"]],
                    "투자명": row[COL["title"]],
                    "기성금액": amount,
                }
            )

        pred_months = parse_month_list(row.get(COL["progress_month_pred"], ""))
        pred_amounts = parse_money_list(row.get(COL["progress_amount_pred"], ""))

        for month, amount in zip(pred_months, pred_amounts):
            pred_rows.append(
                {
                    "월": month,
                    "조직": row[COL["org"]],
                    "투자명": row[COL["title"]],
                    "기성금액_예측": amount,
                }
            )

    if rows:
        progress = pd.DataFrame(rows)
    else:
        progress = pd.DataFrame(columns=["월", "조직", "투자명", "기성금액"])

    if pred_rows:
        progress_pred = pd.DataFrame(pred_rows)
    else:
        progress_pred = pd.DataFrame(columns=["월", "조직", "투자명", "기성금액_예측"])

    # 실제 집행률은 현재 기준월까지만, 예측 집행률은 12월까지 표시합니다.
    actual_max_month = current_month if current_month is not None else 12
    max_month = 12 if not progress_pred.empty else actual_max_month
    monthly = pd.DataFrame({"월": list(range(1, max_month + 1))})

    if not progress.empty:
        progress = progress[progress["월"].between(1, actual_max_month)]

    if not progress_pred.empty:
        progress_pred = progress_pred[progress_pred["월"].between(1, 12)]

    monthly = monthly.merge(
        progress.groupby("월", as_index=False)["기성금액"].sum(),
        on="월",
        how="left",
    )

    monthly = monthly.merge(
        progress_pred.groupby("월", as_index=False)["기성금액_예측"].sum(),
        on="월",
        how="left",
    )

    monthly["기성금액"] = monthly["기성금액"].fillna(0)
    monthly["기성금액_예측"] = monthly["기성금액_예측"].fillna(0)
    monthly["누적기성금액"] = monthly["기성금액"].cumsum()
    monthly["누적기성금액_예측"] = monthly["기성금액_예측"].cumsum()

    base_amount = df[COL["po_amount"]].sum()

    monthly["누적집행률"] = np.where(
        base_amount > 0,
        monthly["누적기성금액"] / base_amount * 100,
        0,
    )

    monthly["예측누적집행률"] = np.where(
        base_amount > 0,
        monthly["누적기성금액_예측"] / base_amount * 100,
        0,
    )

    monthly.loc[monthly["월"] > actual_max_month, "누적집행률"] = np.nan
    monthly["월표시"] = monthly["월"].map(lambda x: f"{x}월")

    return monthly


def monthly_compare_table(df: pd.DataFrame, current_month: int) -> pd.DataFrame:
    base = pd.DataFrame({"월": list(range(1, current_month + 1))})

    review_df = df.copy()
    review_df = review_df[
        review_df["심의진행월_숫자"].notna()
        & review_df["심의진행월_숫자"].between(1, current_month)
    ].copy()

    if review_df.empty:
        review_summary = pd.DataFrame(
            columns=["월", "심의진행건수", "품의금액", "투자비"]
        )
    else:
        review_df["월"] = review_df["심의진행월_숫자"].astype(int)

        review_summary = (
            review_df
            .groupby("월", as_index=False)
            .agg(
                심의진행건수=(COL["no"], "count"),
                품의금액=(COL["po_amount"], "sum"),
                투자비=(COL["invest_cost"], "sum"),
            )
        )

    progress_summary = monthly_progress_table(df, current_month)[
        [
            "월",
            "기성금액",
            "누적기성금액",
            "누적집행률",
            "기성금액_예측",
            "누적기성금액_예측",
            "예측누적집행률",
        ]
    ].copy()

    contract_summary = monthly_contract_table(df, current_month)[
        [
            "월",
            "계약건수",
            "누적계약건수",
            "품의완료건수",
            "누적품의완료건수",
        ]
    ].copy()

    monthly = base.merge(review_summary, on="월", how="left")
    monthly = monthly.merge(contract_summary, on="월", how="left")
    monthly = monthly.merge(progress_summary, on="월", how="left")

    fill_zero_cols = [
        "심의진행건수",
        "품의금액",
        "투자비",
        "계약건수",
        "누적계약건수",
        "품의완료건수",
        "누적품의완료건수",
        "기성금액",
        "누적기성금액",
        "누적집행률",
        "기성금액_예측",
        "누적기성금액_예측",
        "예측누적집행률",
    ]

    for col in fill_zero_cols:
        if col not in monthly.columns:
            monthly[col] = 0

        monthly[col] = monthly[col].fillna(0)

    monthly["누적품의금액"] = monthly["품의금액"].cumsum()
    monthly["월표시"] = monthly["월"].map(lambda x: f"{x}월")

    monthly["품의금액_억원"] = monthly["품의금액"].map(money_eok)
    monthly["투자비_억원"] = monthly["투자비"].map(money_eok)
    monthly["기성금액_억원"] = monthly["기성금액"].map(money_eok)
    monthly["누적기성금액_억원"] = monthly["누적기성금액"].map(money_eok)
    monthly["기성금액_예측_억원"] = monthly["기성금액_예측"].map(money_eok)
    monthly["누적기성금액_예측_억원"] = monthly["누적기성금액_예측"].map(money_eok)
    monthly["누적품의금액_억원"] = monthly["누적품의금액"].map(
        lambda value: np.nan if pd.isna(value) else money_eok(value)
    )

    return monthly


def make_execution_summary_row(df: pd.DataFrame, label: str) -> pd.DataFrame:
    po_sum = df[COL["po_amount"]].sum()
    executed_sum = df[COL["executed_amount"]].sum()

    row = pd.DataFrame(
        [
            {
                "조직": label,
                "투자건수": len(df),
                "투자비": df[COL["invest_cost"]].sum(),
                "품의금액": po_sum,
                "기성처리금액": executed_sum,
                "미집행금액": max(po_sum - executed_sum, 0),
                "집행률": safe_divide(executed_sum, po_sum) * 100,
            }
        ]
    )

    return row


def org_execution_table(
    selected_df: pd.DataFrame,
    total_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    if selected_df.empty:
        org = pd.DataFrame(
            columns=[
                "조직",
                "투자건수",
                "투자비",
                "품의금액",
                "기성처리금액",
                "미집행금액",
                "집행률",
            ]
        )
    else:
        org = (
            selected_df.groupby(COL["org"], as_index=False)
            .agg(
                투자건수=(COL["no"], "count"),
                투자비=(COL["invest_cost"], "sum"),
                품의금액=(COL["po_amount"], "sum"),
                기성처리금액=(COL["executed_amount"], "sum"),
            )
            .rename(columns={COL["org"]: "조직"})
        )

        org["미집행금액"] = (
            org["품의금액"] - org["기성처리금액"]
        ).clip(lower=0)

        org["집행률"] = np.where(
            org["품의금액"] > 0,
            org["기성처리금액"] / org["품의금액"] * 100,
            0,
        )

        org = org.sort_values("조직", ascending=True)

    if total_df is not None and not total_df.empty:
        total_row = make_execution_summary_row(total_df, PJT_TOTAL_LABEL)
        org = pd.concat([total_row, org], ignore_index=True)

    return org


def count_status_table(df: pd.DataFrame, column: str) -> pd.DataFrame:
    return (
        df[column]
        .value_counts(dropna=False)
        .rename_axis(column)
        .reset_index(name="건수")
    )


def build_org_stacked_bar(org_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            y=org_df["조직"],
            x=org_df["기성처리금액"].map(money_eok),
            name="집행금액",
            orientation="h",
            width=0.70,
            marker_color=THEME["executed"],
            text=[
                f"{money_eok(amount):,.1f} 억, {rate:.1f}%"
                for amount, rate in zip(org_df["기성처리금액"], org_df["집행률"])
            ],
            textposition="inside",
            textfont=dict(size=THEME["plot_font_size"]),
            hovertemplate="조직=%{y}<br>집행금액=%{x:,.1f}억<extra></extra>",
        )
    )

    fig.add_trace(
        go.Bar(
            y=org_df["조직"],
            x=org_df["미집행금액"].map(money_eok),
            name="미집행",
            orientation="h",
            width=0.70,
            marker_color=THEME["unexecuted"],
            text=org_df["미집행금액"].map(
                lambda x: f"미집행 {money_eok(x):,.1f}억" if x > 0 else ""
            ),
            textposition="inside",
            textfont=dict(size=THEME["plot_font_size"]),
            hovertemplate="조직=%{y}<br>미집행=%{x:,.1f}억<extra></extra>",
        )
    )

    fig.update_layout(
        autosize=True,
        width=None,
        barmode="stack",
        height=THEME["plot_height_large"],
        margin=dict(l=18, r=18, t=42, b=18),
        xaxis_title="금액(억 원)",
        yaxis_title=None,
        font=dict(size=THEME["plot_font_size"]),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=THEME["plot_font_size"]),
        ),
        xaxis=dict(
            title_font=dict(size=THEME["plot_font_size"]),
            tickfont=dict(size=THEME["plot_font_size"]),
        ),
        yaxis=dict(
            tickfont=dict(size=THEME["plot_font_size"]),
        ),
    )

    return fig


def build_monthly_line(monthly_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()

    monthly_exec_amount_eok = monthly_df["기성금액"].map(money_eok) if "기성금액" in monthly_df.columns else pd.Series([0] * len(monthly_df))

    # 막대그래프를 가장 먼저 추가해 전체 차트의 배경처럼 보이게 합니다.
    # 라벨은 inside로 두어 꺾은선 값 라벨과 겹치지 않게 합니다.
    fig.add_trace(
        go.Bar(
            x=monthly_df["월표시"],
            y=monthly_exec_amount_eok,
            name="월별 집행금액",
            yaxis="y2",
            marker_color=THEME["unexecuted"],
            opacity=0.72,
            text=monthly_exec_amount_eok.map(lambda x: f"{x:,.1f}억" if pd.notna(x) and x > 0 else ""),
            textposition="inside",
            insidetextanchor="end",
            hovertemplate="월=%{x}<br>월별 집행금액=%{y:,.1f}억<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=monthly_df["월표시"],
            y=monthly_df["누적집행률"],
            mode="lines+markers+text",
            text=monthly_df["누적집행률"].map(
                lambda x: f"{x:.1f}%" if pd.notna(x) and x > 0 else ""
            ),
            # 실제/예상 라벨을 대각선 방향으로 분리해 같은 월에서 겹치지 않게 합니다.
            textposition="bottom center",
            textfont=dict(size=THEME["plot_font_size"]),
            name="실제 누적집행률",
            line=dict(color=THEME["executed"], width=3),
            marker=dict(color=THEME["executed"], size=9),
            hovertemplate="월=%{x}<br>실제 누적집행률=%{y:.1f}%<extra></extra>",
        )
    )

    if "예측누적집행률" in monthly_df.columns:
        fig.add_trace(
            go.Scatter(
                x=monthly_df["월표시"],
                y=monthly_df["예측누적집행률"],
                mode="lines+markers+text",
                text=monthly_df["예측누적집행률"].map(
                    lambda x: f"{x:.1f}%" if pd.notna(x) and x > 0 else ""
                ),
                textposition="top center",
                textfont=dict(size=THEME["plot_font_size"]),
                name="예상 누적집행률",
                line=dict(color=THEME["predicted_line"], dash="dash", width=3),
                marker=dict(color=THEME["predicted_line"], size=9),
                hovertemplate="월=%{x}<br>예상 누적집행률=%{y:.1f}%<extra></extra>",
            )
        )

    y_max = monthly_df[["누적집행률", "예측누적집행률"]].max(numeric_only=True).max()
    if pd.isna(y_max):
        y_max = 0

    fig.update_layout(
        autosize=True,
        width=None,
        height=THEME["plot_height_large"],
        margin=dict(l=18, r=18, t=42, b=18),
        yaxis_title="누적집행률(%)",
        xaxis_title=None,
        yaxis_range=[0, max(100, y_max * 1.18)],
        yaxis2=dict(
            title="집행금액(억 원)",
            overlaying="y",
            side="right",
            range=[0, 200],
            showgrid=False,
            zeroline=False,
            title_font=dict(size=THEME["plot_font_size"]),
            tickfont=dict(size=THEME["plot_font_size"]),
        ),
        font=dict(size=THEME["plot_font_size"]),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=THEME["plot_font_size"]),
        ),
        xaxis=dict(
            tickfont=dict(size=THEME["plot_font_size"]),
        ),
        yaxis=dict(
            title_font=dict(size=THEME["plot_font_size"]),
            tickfont=dict(size=THEME["plot_font_size"]),
        ),
    )

    return fig

def org_po_completion_table(
    selected_df: pd.DataFrame,
    total_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """조직별 품의완료/미완료 건수 요약 테이블입니다."""

    def make_row(source_df: pd.DataFrame, label: str) -> dict:
        completed = count_po_completed(source_df)
        total = len(source_df)
        return {
            "조직": label,
            "완료": completed,
            "미완료": max(total - completed, 0),
        }

    rows: list[dict] = []

    if total_df is not None and not total_df.empty:
        rows.append(make_row(total_df, PJT_TOTAL_LABEL))

    if not selected_df.empty:
        for org_name, group_df in selected_df.groupby(COL["org"]):
            rows.append(make_row(group_df, str(org_name)))

    if not rows:
        return pd.DataFrame(columns=["조직", "완료", "미완료"])

    result = pd.DataFrame(rows)
    result["전체"] = result["완료"] + result["미완료"]
    result = result.sort_values("조직", ascending=True)

    # 전체 행은 항상 맨 위에 표시합니다.
    if total_df is not None and not total_df.empty:
        total_row = result[result["조직"] == PJT_TOTAL_LABEL]
        org_rows = result[result["조직"] != PJT_TOTAL_LABEL].sort_values("조직", ascending=True)
        result = pd.concat([total_row, org_rows], ignore_index=True)

    return result


def build_org_po_completion_bar(po_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            y=po_df["조직"],
            x=po_df["완료"],
            name="완료",
            orientation="h",
            width=0.70,
            marker_color=THEME["executed"],
            text=po_df["완료"].map(lambda x: f"완료 {int(x):,}건" if x > 0 else ""),
            textposition="inside",
            textfont=dict(size=THEME["plot_font_size"]),
            hovertemplate="조직=%{y}<br>완료=%{x:,}건<extra></extra>",
        )
    )

    fig.add_trace(
        go.Bar(
            y=po_df["조직"],
            x=po_df["미완료"],
            name="미완료",
            orientation="h",
            width=0.70,
            marker_color=THEME["unexecuted"],
            text=po_df["미완료"].map(lambda x: f"미완료 {int(x):,}건" if x > 0 else ""),
            textposition="inside",
            textfont=dict(size=THEME["plot_font_size"]),
            hovertemplate="조직=%{y}<br>미완료=%{x:,}건<extra></extra>",
        )
    )

    fig.update_layout(
        autosize=True,
        width=None,
        barmode="stack",
        height=THEME["plot_height_large"],
        margin=dict(l=18, r=18, t=42, b=18),
        xaxis_title="건수",
        yaxis_title=None,
        font=dict(size=THEME["plot_font_size"]),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=THEME["plot_font_size"]),
        ),
        xaxis=dict(
            title_font=dict(size=THEME["plot_font_size"]),
            tickfont=dict(size=THEME["plot_font_size"]),
        ),
        yaxis=dict(
            tickfont=dict(size=THEME["plot_font_size"]),
        ),
    )

    return fig



def monthly_po_amount_table(df: pd.DataFrame, current_month: int) -> pd.DataFrame:
    """월별 품의금액/투자건수와 누적 품의금액을 계산합니다."""
    base = pd.DataFrame({"월": list(range(1, 13))})
    po_rows: list[dict] = []

    for _, row in df.iterrows():
        month = extract_month(row.get(COL["review_month"], ""))
        if month is not None and 1 <= month <= current_month:
            po_rows.append(
                {
                    "월": month,
                    "품의금액": row[COL["po_amount"]],
                    "투자건수": 1,
                }
            )

    if po_rows:
        po_monthly = (
            pd.DataFrame(po_rows)
            .groupby("월", as_index=False)
            .agg(
                품의금액=("품의금액", "sum"),
                투자건수=("투자건수", "sum"),
            )
        )
    else:
        po_monthly = pd.DataFrame(columns=["월", "품의금액", "투자건수"])

    monthly = base.merge(po_monthly, on="월", how="left")
    monthly["품의금액"] = monthly["품의금액"].fillna(0)
    monthly["투자건수"] = monthly["투자건수"].fillna(0).astype(int)
    monthly.loc[monthly["월"] > current_month, "투자건수"] = 0
    monthly["누적품의금액"] = monthly["품의금액"].cumsum()
    monthly.loc[monthly["월"] > current_month, "누적품의금액"] = np.nan
    monthly["누적품의금액_억원"] = monthly["누적품의금액"].map(
        lambda value: np.nan if pd.isna(value) else money_eok(value)
    )
    monthly["전체투자금액_억원"] = money_eok(df[COL["invest_cost"]].sum())
    monthly["월표시"] = monthly["월"].map(lambda x: f"{x}월")

    return monthly


# 이전 수정본에서 잘못 호출된 함수명에 대한 호환용 별칭입니다.
# 실제 로직은 monthly_po_amount_table을 사용합니다.
monthly_no_amount_table = monthly_po_amount_table


def build_monthly_po_amount_line(monthly_po_df: pd.DataFrame) -> go.Figure:
    """월별 투자건수 막대 + 누적 품의금액/전체 투자금액 선 그래프입니다."""
    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=monthly_po_df["월표시"],
            y=monthly_po_df["투자건수"],
            name="월별 투자건수",
            yaxis="y2",
            marker_color=THEME["unexecuted"],
            opacity=0.72,
            text=monthly_po_df["투자건수"].map(lambda x: f"{int(x):,}건" if x > 0 else ""),
            textposition="inside",
            insidetextanchor="end",
            hovertemplate="월=%{x}<br>월별 투자건수=%{y:,}건<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=monthly_po_df["월표시"],
            y=monthly_po_df["누적품의금액_억원"],
            mode="lines+markers+text",
            text=monthly_po_df["누적품의금액_억원"].map(
                lambda x: f"{x:,.1f}억" if pd.notna(x) and x > 0 else ""
            ),
            textposition="bottom center",
            textfont=dict(size=THEME["plot_font_size"]),
            name="누적 품의금액",
            line=dict(color=THEME["executed"], width=3),
            marker=dict(color=THEME["executed"], size=9),
            hovertemplate="월=%{x}<br>누적 품의금액=%{y:,.1f}억<extra></extra>",
        )
    )

    # 전체 투자금액 기준선은 모든 월에 표시하되, 값 라벨은 12월 위치에만 표시합니다.
    total_investment_text = [
        f"{value:,.1f}억" if month == 12 and pd.notna(value) and value > 0 else ""
        for month, value in zip(
            monthly_po_df["월"],
            monthly_po_df["전체투자금액_억원"],
        )
    ]

    fig.add_trace(
        go.Scatter(
            x=monthly_po_df["월표시"],
            y=monthly_po_df["전체투자금액_억원"],
            mode="lines+text",
            text=total_investment_text,
            textposition="top center",
            textfont=dict(size=THEME["plot_font_size"]),
            name="전체 투자금액",
            line=dict(color=THEME["predicted_line"], dash="dash", width=3),
            hovertemplate="월=%{x}<br>전체 투자금액=%{y:,.1f}억<extra></extra>",
        )
    )

    y_max = monthly_po_df[["누적품의금액_억원", "전체투자금액_억원"]].max(numeric_only=True).max()
    if pd.isna(y_max):
        y_max = 0

    fig.update_layout(
        autosize=True,
        width=None,
        height=THEME["plot_height_large"],
        margin=dict(l=18, r=18, t=42, b=18),
        yaxis_title="금액(억 원)",
        xaxis_title=None,
        yaxis_range=[0, max(1, y_max * 1.18)],
        yaxis2=dict(
            title="투자건수(건)",
            overlaying="y",
            side="right",
            range=[0, 50],
            showgrid=False,
            zeroline=False,
            title_font=dict(size=THEME["plot_font_size"]),
            tickfont=dict(size=THEME["plot_font_size"]),
        ),
        font=dict(size=THEME["plot_font_size"]),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=THEME["plot_font_size"]),
        ),
        xaxis=dict(tickfont=dict(size=THEME["plot_font_size"])),
        yaxis=dict(
            title_font=dict(size=THEME["plot_font_size"]),
            tickfont=dict(size=THEME["plot_font_size"]),
        ),
    )

    return fig

def org_contract_registration_table(
    selected_df: pd.DataFrame,
    total_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """조직별 계약등록/미등록 건수 요약 테이블입니다."""

    def make_row(source_df: pd.DataFrame, label: str) -> dict:
        registered = count_contract_registered(source_df)
        total = len(source_df)
        return {
            "조직": label,
            "등록": registered,
            "미등록": max(total - registered, 0),
        }

    rows: list[dict] = []

    if total_df is not None and not total_df.empty:
        rows.append(make_row(total_df, PJT_TOTAL_LABEL))

    if not selected_df.empty:
        for org_name, group_df in selected_df.groupby(COL["org"]):
            rows.append(make_row(group_df, str(org_name)))

    if not rows:
        return pd.DataFrame(columns=["조직", "등록", "미등록"])

    result = pd.DataFrame(rows)
    result["전체"] = result["등록"] + result["미등록"]
    result = result.sort_values("조직", ascending=True)

    if total_df is not None and not total_df.empty:
        total_row = result[result["조직"] == PJT_TOTAL_LABEL]
        org_rows = result[result["조직"] != PJT_TOTAL_LABEL].sort_values("조직", ascending=True)
        result = pd.concat([total_row, org_rows], ignore_index=True)

    return result


def build_org_contract_registration_bar(contract_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            y=contract_df["조직"],
            x=contract_df["등록"],
            name="등록",
            orientation="h",
            width=0.70,
            marker_color=THEME["executed"],
            text=contract_df["등록"].map(lambda x: f"등록 {int(x):,}건" if x > 0 else ""),
            textposition="inside",
            textfont=dict(size=THEME["plot_font_size"]),
            hovertemplate="조직=%{y}<br>등록=%{x:,}건<extra></extra>",
        )
    )

    fig.add_trace(
        go.Bar(
            y=contract_df["조직"],
            x=contract_df["미등록"],
            name="미등록",
            orientation="h",
            width=0.70,
            marker_color=THEME["unexecuted"],
            text=contract_df["미등록"].map(lambda x: f"미등록 {int(x):,}건" if x > 0 else ""),
            textposition="inside",
            textfont=dict(size=THEME["plot_font_size"]),
            hovertemplate="조직=%{y}<br>미등록=%{x:,}건<extra></extra>",
        )
    )

    fig.update_layout(
        autosize=True,
        width=None,
        barmode="stack",
        height=THEME["plot_height_large"],
        margin=dict(l=18, r=18, t=42, b=18),
        xaxis_title="건수",
        yaxis_title=None,
        font=dict(size=THEME["plot_font_size"]),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=THEME["plot_font_size"]),
        ),
        xaxis=dict(
            title_font=dict(size=THEME["plot_font_size"]),
            tickfont=dict(size=THEME["plot_font_size"]),
        ),
        yaxis=dict(
            tickfont=dict(size=THEME["plot_font_size"]),
        ),
    )

    return fig


def monthly_contract_table(df: pd.DataFrame, current_month: int) -> pd.DataFrame:
    base = pd.DataFrame({"월": list(range(1, 13))})
    contract_rows = []
    po_rows = []

    for _, row in df.iterrows():
        contract_month = extract_month(row.get(COL["contract_month"], ""))
        if (
            is_contract_registered_value(row.get(COL["contract_done"], ""))
            and contract_month is not None
            and 1 <= contract_month <= current_month
        ):
            contract_rows.append({"월": contract_month, "계약건수": 1})

        po_month = extract_month(row.get(COL["review_month"], ""))
        if (
            is_po_completed_value(row.get(COL["po_done"], ""))
            and po_month is not None
            and 1 <= po_month <= current_month
        ):
            po_rows.append({"월": po_month, "품의완료건수": 1})

    if contract_rows:
        contract_monthly = (
            pd.DataFrame(contract_rows)
            .groupby("월", as_index=False)["계약건수"]
            .sum()
        )
    else:
        contract_monthly = pd.DataFrame(columns=["월", "계약건수"])

    if po_rows:
        po_monthly = (
            pd.DataFrame(po_rows)
            .groupby("월", as_index=False)["품의완료건수"]
            .sum()
        )
    else:
        po_monthly = pd.DataFrame(columns=["월", "품의완료건수"])

    monthly = base.merge(contract_monthly, on="월", how="left")
    monthly = monthly.merge(po_monthly, on="월", how="left")
    monthly["계약건수"] = monthly["계약건수"].fillna(0).astype(int)
    monthly["품의완료건수"] = monthly["품의완료건수"].fillna(0).astype(int)
    monthly.loc[monthly["월"] > current_month, ["계약건수", "품의완료건수"]] = 0
    monthly["누적계약건수"] = monthly["계약건수"].cumsum()
    monthly["누적품의완료건수"] = monthly["품의완료건수"].cumsum()
    monthly.loc[monthly["월"] > current_month, ["누적계약건수", "누적품의완료건수"]] = np.nan
    monthly["월표시"] = monthly["월"].map(lambda x: f"{x}월")

    return monthly


def build_monthly_contract_line(monthly_contract_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=monthly_contract_df["월표시"],
            y=monthly_contract_df["계약건수"],
            name="월별 계약건수",
            yaxis="y2",
            marker_color=THEME["unexecuted"],
            opacity=0.72,
            text=monthly_contract_df["계약건수"].map(lambda x: f"{int(x):,}건" if x > 0 else ""),
            textposition="inside",
            insidetextanchor="end",
            hovertemplate="월=%{x}<br>월별 계약건수=%{y:,}건<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=monthly_contract_df["월표시"],
            y=monthly_contract_df["누적계약건수"],
            mode="lines+markers+text",
            text=monthly_contract_df["누적계약건수"].map(
                lambda x: f"{int(x):,}건" if pd.notna(x) and x > 0 else ""
            ),
            textposition="bottom center",
            textfont=dict(size=THEME["plot_font_size"]),
            name="누적 계약건수",
            line=dict(color=THEME["executed"], width=3),
            marker=dict(color=THEME["executed"], size=9),
            hovertemplate="월=%{x}<br>누적 계약건수=%{y:,}건<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=monthly_contract_df["월표시"],
            y=monthly_contract_df["누적품의완료건수"],
            mode="lines+markers+text",
            text=monthly_contract_df["누적품의완료건수"].map(
                lambda x: f"{int(x):,}건" if pd.notna(x) and x > 0 else ""
            ),
            textposition="top center",
            textfont=dict(size=THEME["plot_font_size"]),
            name="누적 품의완료건수",
            line=dict(color=THEME["predicted_line"], dash="dash", width=3),
            marker=dict(color=THEME["predicted_line"], size=9),
            hovertemplate="월=%{x}<br>누적 품의완료건수=%{y:,}건<extra></extra>",
        )
    )

    y_max = monthly_contract_df[["누적계약건수", "누적품의완료건수"]].max(numeric_only=True).max()
    if pd.isna(y_max):
        y_max = 0

    monthly_max = monthly_contract_df["계약건수"].max() if "계약건수" in monthly_contract_df.columns else 0
    if pd.isna(monthly_max):
        monthly_max = 0

    fig.update_layout(
        autosize=True,
        width=None,
        height=THEME["plot_height_large"],
        margin=dict(l=18, r=18, t=42, b=18),
        yaxis_title="누적 건수",
        xaxis_title=None,
        yaxis_range=[0, max(1, y_max * 1.18)],
        yaxis2=dict(
            title="월별 계약건수(건)",
            overlaying="y",
            side="right",
            range=[0, max(50, monthly_max * 1.18)],
            showgrid=False,
            zeroline=False,
            title_font=dict(size=THEME["plot_font_size"]),
            tickfont=dict(size=THEME["plot_font_size"]),
        ),
        font=dict(size=THEME["plot_font_size"]),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=THEME["plot_font_size"]),
        ),
        xaxis=dict(
            tickfont=dict(size=THEME["plot_font_size"]),
        ),
        yaxis=dict(
            title_font=dict(size=THEME["plot_font_size"]),
            tickfont=dict(size=THEME["plot_font_size"]),
        ),
    )

    return fig

def calculate_kpi_values(df: pd.DataFrame) -> dict[str, dict[str, str]]:
    """KPI 표시값을 한곳에서 계산합니다.

    반환값은 숫자와 단위를 분리해 단위만 별도 CSS 크기로 제어합니다.
    """
    total_count = len(df)
    po_done_count = count_po_completed(df)
    invest_sum = money_eok(df[COL["invest_cost"]].sum())
    po_sum = money_eok(df[COL["po_amount"]].sum())
    executed_sum = money_eok(df[COL["executed_amount"]].sum())

    po_amount_sum = df[COL["po_amount"]].sum()
    executed_amount_sum = df[COL["executed_amount"]].sum()
    execution_rate = safe_divide(executed_amount_sum, po_amount_sum) * 100

    return {
        "total_count": {"number": f"{total_count:,}", "unit": "건"},
        "po_done_count": {"number": f"{po_done_count:,}", "unit": "건"},
        "invest_sum": {"number": f"{invest_sum:,.1f}", "unit": "억"},
        "po_sum": {"number": f"{po_sum:,.1f}", "unit": "억"},
        "executed_sum": {"number": f"{executed_sum:,.1f}", "unit": "억"},
        "execution_rate": {"number": f"{execution_rate:,.1f}", "unit": "%"},
    }


def show_kpi(df: pd.DataFrame) -> None:
    """KPI 카드 영역입니다.

    KPI 항목 추가/삭제/순서 변경은 KPI_CARDS 설정만 수정하면 됩니다.
    2개씩 구분선은 group_divider_after=True로 제어합니다.
    """
    values = calculate_kpi_values(df)
    kpi_html = "<div class='kpi-grid'>"
    caption_html = "<div class='kpi-caption-grid'>"

    for card in KPI_CARDS:
        label = html.escape(str(card["label"]))
        caption = html.escape(str(card.get("caption", "")))
        metric_value = values.get(card["metric"], {"number": "-", "unit": ""})
        number = html.escape(str(metric_value.get("number", "-")))
        unit = html.escape(str(metric_value.get("unit", "")))
        divider_class = " group-divider" if card.get("group_divider_after") else ""
        kpi_html += (
            f"<div class='kpi-card{divider_class}'>"
            f"<div class='kpi-label'>{label}</div>"
            f"<div class='kpi-value'><span class='kpi-number'>{number}</span> "
            f"<span class='kpi-unit'>{unit}</span></div>"
            "</div>"
        )
        caption_html += f"<div class='kpi-caption-outside'>{caption}</div>"

    kpi_html += "</div>"
    caption_html += "</div>"
    st.markdown(kpi_html + caption_html, unsafe_allow_html=True)

def show_detail_section(df: pd.DataFrame, current_month: int) -> None:
    """상세 리스트 영역입니다.

    표시 컬럼은 DETAIL_TABLE_COLUMNS, 검색 대상은 DETAIL_SEARCH_COLUMNS,
    정렬 기준은 DETAIL_SORT_COLUMNS에서 관리합니다.
    """
    st.markdown(
        "<div class='section-title'>상세 리스트</div>",
        unsafe_allow_html=True,
    )

    search = st.text_input(
        "조직, 담당자, wbs_code, 투자명, 계획구분, 팀장심의, 기본품의완료, 계약등록 내용에 대한 검색이 가능합니다.",
        placeholder="예: 서버, WBS-2026, 김도윤, 시스템_PJT, 계획, 완료",
        key="detail_search_in_dashboard",
    )

    detail = df.copy()
    detail["투자 신호등"] = detail.apply(
        lambda row: make_invest_signal(row, current_month),
        axis=1,
    )

    # 상세 리스트에서는 금액 컬럼을 원 단위 데이터에서 억 원 단위 표시값으로 변환합니다.
    # 예산전용은 화면 표시상 지출/차감 성격이 명확히 보이도록 앞에 마이너스 부호를 붙입니다.
    detail_money_cols = [
        COL["invest_cost"],
        COL["planned_cost"],
        COL["increase"],
        COL["transfer"],
        COL["po_amount"],
        COL["executed_amount"],
    ]
    for money_col in detail_money_cols:
        if money_col not in detail.columns:
            continue

        if money_col == COL["transfer"]:
            detail[money_col] = detail[money_col].map(
                lambda value: 0.0 if money_eok(value) == 0 else -abs(money_eok(value))
            )
        else:
            detail[money_col] = detail[money_col].map(money_eok)

    if search.strip():
        pattern = re.escape(search.strip())
        search_columns = existing_columns(detail, DETAIL_SEARCH_COLUMNS)

        if search_columns:
            mask = pd.Series(False, index=detail.index)
            for column in search_columns:
                mask = mask | detail[column].astype(str).str.contains(
                    pattern,
                    case=False,
                    na=False,
                )
            detail = detail[mask]

    visible_cols = existing_columns(detail, DETAIL_TABLE_COLUMNS)
    sort_cols = existing_columns(detail, DETAIL_SORT_COLUMNS)

    if visible_cols:
        detail = detail[visible_cols]

    if sort_cols:
        detail = detail.sort_values(sort_cols)

    st.dataframe(
        detail,
        use_container_width=True,
        hide_index=True,
        height=THEME["detail_table_height"],
        column_config=make_streamlit_column_config(),
    )

    # CSV 다운로드 기능이 필요하면 아래 주석을 해제하세요.
    # csv = detail.to_csv(index=False).encode("utf-8-sig")
    # st.download_button(
    #     "현재 상세 리스트 CSV 다운로드",
    #     data=csv,
    #     file_name="investment_dashboard_filtered_detail.csv",
    #     mime="text/csv",
    # )

def show_org_button_filter(
    options: list[str],
    current_label: str,
) -> str:
    state_key = f"selected_org_button_{current_label}"

    if state_key not in st.session_state:
        st.session_state[state_key] = options[0]

    if st.session_state[state_key] not in options:
        st.session_state[state_key] = options[0]

    for option in options:
        is_selected = st.session_state[state_key] == option

        if st.button(
            option,
            key=f"org_button_{current_label}_{option}",
            use_container_width=True,
            type="primary" if is_selected else "secondary",
        ):
            st.session_state[state_key] = option
            st.rerun()

    return st.session_state[state_key]



def make_org_integrated_progress_table(df: pd.DataFrame, current_month: int) -> pd.DataFrame:
    """종합현황용 조직별 단계 진행률 테이블입니다.

    종합현황에서는 단계별 상세 차트를 반복하지 않고,
    품의율·계약전환율·금액집행률·관리필요 건수를 한 번에 비교합니다.
    """
    rows: list[dict] = []
    if df.empty:
        return pd.DataFrame(
            columns=[
                "조직", "투자건수", "품의완료율", "계약전환율",
                "집행률", "관리필요", "종합진행점수",
            ]
        )

    for org_name, group in df.groupby(COL["org"], dropna=False):
        summary = make_stage_summary(group, current_month)
        management_need = (
            summary["delayed_po_count"]
            + summary["contract_backlog_count"]
            + summary["execution_backlog_count"]
        )
        # 품의/계약/집행을 동일 가중치로 둔 관리용 종합 점수입니다.
        progress_score = (
            summary["po_completion_rate"] * 0.34
            + summary["contract_conversion_rate"] * 0.33
            + summary["amount_execution_rate"] * 0.33
        )
        rows.append(
            {
                "조직": str(org_name),
                "투자건수": int(summary["total_count"]),
                "품의완료율": summary["po_completion_rate"],
                "계약전환율": summary["contract_conversion_rate"],
                "집행률": summary["amount_execution_rate"],
                "관리필요": int(management_need),
                "종합진행점수": progress_score,
            }
        )

    result = pd.DataFrame(rows)
    return result.sort_values(["관리필요", "종합진행점수", "조직"], ascending=[False, True, True])


def build_org_integrated_progress_chart(org_progress: pd.DataFrame) -> go.Figure:
    if org_progress.empty:
        fig = go.Figure()
        fig.update_layout(height=THEME["plot_height_medium"])
        return fig

    plot_df = org_progress.melt(
        id_vars=["조직"],
        value_vars=["품의완료율", "계약전환율", "집행률"],
        var_name="단계",
        value_name="진행률",
    )
    stage_color_map = {
        "품의완료율": THEME["blue_step_1"],
        "계약전환율": THEME["blue_step_2"],
        "집행률": THEME["blue_step_3"],
    }
    stage_order = ["품의완료율", "계약전환율", "집행률"]

    fig = px.bar(
        plot_df,
        x="조직",
        y="진행률",
        color="단계",
        color_discrete_map=stage_color_map,
        category_orders={"단계": stage_order},
        barmode="group",
        text="진행률",
        title="조직별 종합 진행률",
    )
    fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig.update_layout(
        height=THEME["plot_height_medium"],
        margin=dict(l=18, r=18, t=48, b=18),
        yaxis_title="진행률(%)",
        xaxis_title=None,
        yaxis_range=[0, 115],
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        font=dict(size=THEME["main_plot_font_size"]),
    )
    return fig


def build_monthly_command_center_chart(df: pd.DataFrame, current_month: int) -> go.Figure:
    """종합현황용 월별 핵심 흐름 차트입니다.

    금액은 누적 품의/누적 집행을 같은 축으로 보고,
    계약건수는 보조축 막대로 표시해 단계 흐름만 빠르게 판단합니다.
    """
    monthly = monthly_compare_table(df, current_month)
    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=monthly["월표시"],
            y=monthly["계약건수"],
            name="월별 계약건수",
            yaxis="y2",
            marker_color=THEME["unexecuted"],
            opacity=0.72,
            text=monthly["계약건수"].map(lambda x: f"{int(x):,}건" if pd.notna(x) and x > 0 else ""),
            textposition="inside",
            hovertemplate="월=%{x}<br>계약건수=%{y:,}건<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=monthly["월표시"],
            y=monthly["누적품의금액_억원"],
            mode="lines+markers+text",
            name="누적 품의금액",
            line=dict(color=THEME["executed"], width=3),
            marker=dict(size=8),
            text=monthly["누적품의금액_억원"].map(lambda x: f"{x:,.1f}억" if pd.notna(x) and x > 0 else ""),
            textposition="top center",
            hovertemplate="월=%{x}<br>누적 품의금액=%{y:,.1f}억<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=monthly["월표시"],
            y=monthly["누적기성금액_억원"],
            mode="lines+markers+text",
            name="누적 집행금액",
            line=dict(color=THEME["predicted_line"], width=3, dash="dash"),
            marker=dict(size=8),
            text=monthly["누적기성금액_억원"].map(lambda x: f"{x:,.1f}억" if pd.notna(x) and x > 0 else ""),
            textposition="bottom center",
            hovertemplate="월=%{x}<br>누적 집행금액=%{y:,.1f}억<extra></extra>",
        )
    )

    amount_max = monthly[["누적품의금액_억원", "누적기성금액_억원"]].max(numeric_only=True).max()
    contract_max = monthly["계약건수"].max() if "계약건수" in monthly.columns else 0
    fig.update_layout(
        title="월별 핵심 진행 흐름",
        height=THEME["plot_height_medium"],
        margin=dict(l=18, r=18, t=48, b=18),
        yaxis_title="금액(억 원)",
        yaxis_range=[0, max(1, 0 if pd.isna(amount_max) else amount_max * 1.18)],
        yaxis2=dict(
            title="계약건수(건)", overlaying="y", side="right",
            range=[0, max(5, 0 if pd.isna(contract_max) else contract_max * 1.35)],
            showgrid=False, zeroline=False,
        ),
        xaxis_title=None,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        font=dict(size=THEME["main_plot_font_size"]),
    )
    return fig


def make_priority_action_table(df: pd.DataFrame, current_month: int) -> pd.DataFrame:
    """종합현황 하단에 보여줄 관리 우선순위 리스트입니다."""
    bottleneck = make_bottleneck_table(df, current_month)
    if bottleneck.empty:
        return bottleneck

    priority_map = {"품의 지연": 1, "계약 대기": 2, "집행 대기": 3, "잔여 집행": 4}
    result = bottleneck.copy()
    result["우선순위"] = result["진단단계"].map(priority_map).fillna(9).astype(int)
    result = result.sort_values(["우선순위", "NO"], ascending=[True, True])
    return result[["NO", "조직", "담당자", "투자명", "진단단계", "진단내용", "관리포인트"]]


def render_executive_kpi(
    summary: dict[str, float],
    total_metric_summary: dict[str, float] | None = None,
) -> None:
    """투자 종합현황 상단 KPI입니다.

    전체 투자건수/전체 투자금액은 하단 상세 리스트에 표시되는 로우 기준으로
    계산할 수 있도록 total_metric_summary를 별도로 받습니다.
    나머지 진행률/관리필요 지표는 기존처럼 차트·진단에 쓰는 현재 선택 조건 기준을 유지합니다.
    """
    total_metric_summary = total_metric_summary or summary

    risk_count = (
        summary["delayed_po_count"]
        + summary["contract_backlog_count"]
        + summary["execution_backlog_count"]
    )
    render_mini_kpi_grid(
        [
            {"label": "전체 투자건수", "value": fmt_count(total_metric_summary["total_count"]), "caption": "하단 상세 리스트 기준"},
            {"label": "전체 투자금액", "value": fmt_eok_from_won(total_metric_summary["invest_sum"]), "caption": "하단 상세 리스트 투자비 합계"},
            {"label": "품의완료율", "value": fmt_pct(summary["po_completion_rate"]), "caption": "품의완료 / 전체", "tone": "good" if summary["po_completion_rate"] >= 80 else "warn"},
            {"label": "계약전환율", "value": fmt_pct(summary["contract_conversion_rate"]), "caption": "계약등록 / 품의완료", "tone": "good" if summary["contract_conversion_rate"] >= 80 else "warn"},
            {"label": "금액 집행률", "value": fmt_pct(summary["amount_execution_rate"]), "caption": "기성처리금액 / 품의금액", "tone": "good" if summary["amount_execution_rate"] >= 70 else "warn"},
            {"label": "관리필요 건수", "value": fmt_count(risk_count), "caption": "품의지연+계약대기+집행대기", "tone": "bad" if risk_count > 0 else "good"},
        ],
        columns=6,
    )


def show_dashboard_tab(
    df: pd.DataFrame,
    current_month: int,
    current_label: str,
    detail_base_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """투자 종합현황 탭입니다.

    최적 구성 원칙:
    - 종합현황: 요약, 전환 흐름, 조직별 비교, 관리 우선순위
    - 상세현황: 단계별 원인 분석, 월별 상세, 건별 조치 대상
    """
    st.markdown(
        "<div class='section-title'>투자 종합현황</div>",
        unsafe_allow_html=True,
    )

    org_filter_options = [PJT_ALL_LABEL] + unique_sorted(df[COL["org"]])
    org_filter_col, body_col = st.columns(
        [MAIN_LAYOUT["execution_columns"][0], sum(MAIN_LAYOUT["execution_columns"][1:])],
        gap="medium",
    )

    with org_filter_col:
        st.markdown("<div class='chart-subtitle'>조직 구분</div>", unsafe_allow_html=True)
        selected_org = show_org_button_filter(
            options=org_filter_options,
            current_label=current_label,
        )

    if selected_org == PJT_ALL_LABEL:
        org_filtered_df = df.copy()
    else:
        org_filtered_df = df[df[COL["org"]] == selected_org].copy()

    # 하단 상세 리스트는 web_compare3와 동일하게 원본 로우 기준 데이터(detail_base_df)를 사용합니다.
    # 단, 투자 종합현황의 조직 구분 버튼 선택값은 상세 리스트에도 동일하게 반영합니다.
    detail_source_df = df.copy() if detail_base_df is None else detail_base_df.copy()

    if selected_org == PJT_ALL_LABEL:
        detail_filtered_df = detail_source_df.copy()
    else:
        detail_filtered_df = detail_source_df[
            detail_source_df[COL["org"]] == selected_org
        ].copy()

    if org_filtered_df.empty:
        st.warning("선택한 조직 조건에 해당하는 데이터가 없습니다.")
        return org_filtered_df

    summary = make_stage_summary(org_filtered_df, current_month)
    # 요청사항: 상단 메트릭 중 전체 투자건수/전체 투자금액은
    # 하단 상세 리스트에 실제로 잡히는 투자건 기준으로 계산합니다.
    # Drop 건이 상세 리스트 기준에서 제외되어 있다면 이 합계에도 자동으로 반영되지 않습니다.
    detail_metric_summary = make_stage_summary(detail_filtered_df, current_month)

    with body_col:
        render_executive_kpi(summary, total_metric_summary=detail_metric_summary)

        flow_col, action_col = st.columns([0.95, 1.55], gap="medium")
        with flow_col:
            st.markdown("<div class='chart-subtitle'>전체 진행 퍼널</div>", unsafe_allow_html=True)
            st.plotly_chart(
                force_full_width_plot(build_stage_flow_chart(summary)),
                use_container_width=True,
                config={"responsive": True},
                key="summary_stage_flow_chart",
            )

        with action_col:
            st.markdown("<div class='chart-subtitle'>관리 우선순위</div>", unsafe_allow_html=True)
            priority = make_priority_action_table(org_filtered_df, current_month)
            if priority.empty:
                st.success("현재 기준월에서 우선 조치가 필요한 투자 건이 없습니다.")
            else:
                st.dataframe(
                    priority.head(10),
                    use_container_width=True,
                    hide_index=True,
                    height=260,
                )

        org_chart_col, monthly_chart_col = st.columns(2, gap="medium")
        with org_chart_col:
            org_progress = make_org_integrated_progress_table(org_filtered_df, current_month)
            st.plotly_chart(
                force_full_width_plot(build_org_integrated_progress_chart(org_progress)),
                use_container_width=True,
                config={"responsive": True},
                key="summary_org_integrated_progress_chart",
            )

        with monthly_chart_col:
            st.plotly_chart(
                force_full_width_plot(build_monthly_command_center_chart(org_filtered_df, current_month)),
                use_container_width=True,
                config={"responsive": True},
                key="summary_monthly_command_center_chart",
            )

    st.divider()

    st.markdown(
        "<div class='section-title'>조직별 종합 관리 테이블</div>",
        unsafe_allow_html=True,
    )
    org_progress_display = make_org_integrated_progress_table(org_filtered_df, current_month).copy()
    if not org_progress_display.empty:
        for col in ["품의완료율", "계약전환율", "집행률", "종합진행점수"]:
            org_progress_display[col] = org_progress_display[col].map(fmt_pct)
    st.dataframe(
        org_progress_display,
        use_container_width=True,
        hide_index=True,
        height=260,
    )

    # web_compare3의 투자 종합현황 하단 상세 리스트를 동일한 위치에 추가합니다.
    # 검색, 신호등, 금액 억 원 변환, 집행률 ProgressColumn 설정은 기존 show_detail_section을 재사용합니다.
    st.divider()

    if detail_filtered_df.empty:
        st.warning("선택한 조직 조건에 해당하는 상세 리스트 데이터가 없습니다.")
    else:
        show_detail_section(detail_filtered_df, current_month)

    return org_filtered_df

def show_monthly_compare_tab(
    df: pd.DataFrame,
    current_month: int,
    current_label: str,
) -> None:
    st.markdown(
        f"<div class='section-title'>{current_label}까지 월별 비교</div>",
        unsafe_allow_html=True,
    )

    if df.empty:
        st.warning("월별 비교를 표시할 데이터가 없습니다.")
        return

    monthly = monthly_compare_table(df, current_month)

    c1, c2, c3 = st.columns(MAIN_LAYOUT["monthly_compare_columns"], gap="medium")

    with c1:
        amount_plot = monthly[
            ["월표시", "품의금액_억원", "기성금액_억원"]
        ].copy()

        amount_melt = amount_plot.melt(
            id_vars="월표시",
            value_vars=["품의금액_억원", "기성금액_억원"],
            var_name="구분",
            value_name="금액_억원",
        )

        amount_melt["구분"] = amount_melt["구분"].replace(
            {
                "품의금액_억원": "품의금액",
                "기성금액_억원": "기성금액",
            }
        )

        fig = px.bar(
            amount_melt,
            x="월표시",
            y="금액_억원",
            color="구분",
            barmode="group",
            text="금액_억원",
            title="월별 품의금액 · 기성금액 비교",
        )

        fig.update_traces(
            texttemplate="%{text:,.1f}억",
            textposition="outside",
        )

        fig.update_layout(
            height=THEME["plot_height_medium"],
            margin=dict(l=18, r=18, t=48, b=18),
            xaxis_title=None,
            yaxis_title="금액(억 원)",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
            ),
        )

        st.plotly_chart(force_full_width_plot(fig), use_container_width=True, config={"responsive": True}, key="monthly_compare_amount_chart")

    with c2:
        fig = build_monthly_line(monthly)
        fig.update_layout(
            title="월별 누적 집행률",
            height=THEME["plot_height_medium"],
            margin=dict(l=18, r=18, t=48, b=18),
        )

        st.plotly_chart(force_full_width_plot(fig), use_container_width=True, config={"responsive": True}, key="monthly_compare_execution_chart")

    with c3:
        fig = px.line(
            monthly,
            x="월표시",
            y=["누적품의금액_억원", "누적기성금액_억원"],
            markers=True,
            title="월별 누적 품의금액 · 누적 기성금액",
        )

        fig.update_layout(
            height=THEME["plot_height_medium"],
            margin=dict(l=18, r=18, t=48, b=18),
            xaxis_title=None,
            yaxis_title="금액(억 원)",
            legend_title_text="구분",
        )

        fig.for_each_trace(
            lambda trace: trace.update(
                name={
                    "누적품의금액_억원": "누적품의금액",
                    "누적기성금액_억원": "누적기성금액",
                }.get(trace.name, trace.name)
            )
        )

        st.plotly_chart(force_full_width_plot(fig), use_container_width=True, config={"responsive": True}, key="monthly_compare_cumulative_chart")

    st.markdown(
        "<div class='section-title'>월별 비교 테이블</div>",
        unsafe_allow_html=True,
    )

    display = monthly[
        [
            "월표시",
            "심의진행건수",
            "품의완료건수",
            "계약건수",
            "누적계약건수",
            "투자비",
            "품의금액",
            "기성금액",
            "누적품의금액",
            "누적기성금액",
            "누적집행률",
        ]
    ].copy()

    money_display_cols = [
        "투자비",
        "품의금액",
        "기성금액",
        "누적품의금액",
        "누적기성금액",
    ]

    for col in money_display_cols:
        display[col] = display[col].map(fmt_eok)

    display["누적집행률"] = display["누적집행률"].map(fmt_pct)

    display = display.rename(columns={"월표시": "월"})

    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
    )

def build_status_chart(df: pd.DataFrame, spec: dict) -> go.Figure | None:
    """STATUS_CHARTS 설정을 기반으로 상태 차트를 생성합니다."""
    kind = spec.get("kind")
    title = spec.get("title", "상태 차트")

    if kind == "count_bar":
        column = resolve_col(spec["column_key"])
        if column not in df.columns:
            return None

        chart_df = count_status_table(df, column)
        fig = px.bar(
            chart_df,
            x=column,
            y="건수",
            text="건수",
            title=title,
        )
        fig.update_traces(width=THEME["status_bar_width"])
        fig.update_layout(xaxis_title=None)
        return apply_standard_plot_layout(fig, height=THEME["plot_height_small"])

    if kind == "amount_pie":
        group_col = resolve_col(spec["group_key"])
        amount_col = resolve_col(spec["amount_key"])
        if group_col not in df.columns or amount_col not in df.columns:
            return None

        chart_df = df.groupby(group_col, as_index=False)[amount_col].sum()
        chart_df["금액_억원"] = chart_df[amount_col].map(money_eok)
        fig = px.pie(
            chart_df,
            names=group_col,
            values="금액_억원",
            title=title,
        )
        return apply_standard_plot_layout(fig, height=THEME["plot_height_small"])

    if kind == "change_bar":
        chart_df = pd.DataFrame(
            {
                "구분": [
                    "담당자 변경",
                    "투자명 변경",
                    "증액 발생",
                    "예산전용 발생",
                ],
                "건수": [
                    (df["담당자변경"] == "변경").sum(),
                    (df["투자명변경"] == "변경").sum(),
                    (df[COL["increase"]] > 0).sum(),
                    (df[COL["transfer"]] > 0).sum(),
                ],
            }
        )
        fig = px.bar(
            chart_df,
            x="구분",
            y="건수",
            text="건수",
            title=title,
        )
        fig.update_traces(width=THEME["status_bar_width"])
        fig.update_layout(xaxis_title=None)
        return apply_standard_plot_layout(fig, height=THEME["plot_height_small"])

    return None


def show_status_tab(df: pd.DataFrame, current_label: str) -> None:
    """상태별 현황 탭입니다.

    차트 추가/삭제/순서 변경은 STATUS_CHARTS 설정만 수정하면 됩니다.
    """
    st.markdown(
        f"<div class='section-title'>{current_label} 기준 상태별 현황</div>",
        unsafe_allow_html=True,
    )

    if df.empty:
        st.warning("상태별 현황을 표시할 데이터가 없습니다.")
        return

    column_count = max(1, min(len(STATUS_CHARTS), MAIN_LAYOUT["status_columns"]))
    columns = st.columns(column_count, gap="medium")

    for idx, spec in enumerate(STATUS_CHARTS):
        fig = build_status_chart(df, spec)
        with columns[idx % column_count]:
            if fig is None:
                st.info(f"'{spec.get('title', '차트')}' 표시 컬럼을 찾지 못했습니다.")
            else:
                st.plotly_chart(force_full_width_plot(fig), use_container_width=True, config={"responsive": True}, key=f"status_chart_dynamic_{idx}" if "idx" in locals() else "status_chart_dynamic")

def show_monthly_compare_table_only(
    df: pd.DataFrame,
    current_month: int,
) -> None:
    """투자 진행 상세현황 탭 하단 월별 비교 테이블입니다."""
    monthly = monthly_compare_table(df, current_month)

    display = monthly[
        [
            "월표시",
            "심의진행건수",
            "품의완료건수",
            "계약건수",
            "누적계약건수",
            "투자비",
            "품의금액",
            "기성금액",
            "누적품의금액",
            "누적기성금액",
            "누적집행률",
        ]
    ].copy()

    money_display_cols = [
        "투자비",
        "품의금액",
        "기성금액",
        "누적품의금액",
        "누적기성금액",
    ]

    for col in money_display_cols:
        display[col] = display[col].map(fmt_eok)

    display["누적집행률"] = display["누적집행률"].map(fmt_pct)
    display = display.rename(columns={"월표시": "월"})

    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
    )



def fmt_count(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "0 건"
    return f"{int(value):,} 건"


def fmt_eok_from_won(value: float | int | None) -> str:
    return fmt_eok(value)


def render_mini_kpi_grid(cards: list[dict], *, columns: int = 4) -> None:
    """상세 모니터링용 요약 KPI 카드입니다.

    Streamlit 기본 metric 대신 HTML 카드로 구성해 탭/컬럼 폭 변화에도 UI가 안정적으로 유지됩니다.
    cards: [{"label": str, "value": str, "caption": str, "tone": optional str}]
    """
    if not cards:
        return

    safe_columns = max(1, min(columns, 6))
    html_parts = [
        "<div style='display:grid;"
        f"grid-template-columns:repeat({safe_columns}, minmax(0, 1fr));"
        "gap:0.85rem;margin:0.35rem 0 0.8rem 0;'>"
    ]

    tone_border = {
        "normal": THEME["border"],
        "good": "rgba(20, 40, 160, 0.28)",
        "warn": "rgba(245, 158, 11, 0.45)",
        "bad": "rgba(239, 68, 68, 0.42)",
    }

    for card in cards:
        label = html.escape(str(card.get("label", "")))
        value = html.escape(str(card.get("value", "-")))
        caption = html.escape(str(card.get("caption", "")))
        tone = str(card.get("tone", "normal"))
        border = tone_border.get(tone, THEME["border"])
        html_parts.append(
            "<div style='background:#FFFFFF;"
            f"border:1px solid {border};border-radius:0.9rem;"
            "box-shadow:0 1px 2px rgba(15,23,42,0.06);"
            "padding:0.95rem 1rem;min-height:7.0rem;display:flex;flex-direction:column;justify-content:center;'>"
            f"<div style='font-size:0.95rem;color:{THEME['text_muted']};font-weight:700;margin-bottom:0.35rem;'>{label}</div>"
            f"<div style='font-size:1.85rem;line-height:1.15;color:{THEME['text_main']};font-weight:800;letter-spacing:-0.035em;'>{value}</div>"
            f"<div style='font-size:0.78rem;line-height:1.35;color:{THEME['text_subtle']};margin-top:0.35rem;'>{caption}</div>"
            "</div>"
        )

    html_parts.append("</div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)


def get_actual_progress_amount(row: pd.Series, current_month: int) -> float:
    """현재 기준월까지 발생한 실제 기성 금액을 행 단위로 계산합니다.

    기성처리금액_합계가 이미 정규화되어 있으면 우선 사용하고,
    값이 없을 때는 기성_월/기성_금액 목록에서 기준월까지 금액을 합산합니다.
    """
    executed = row.get(COL["executed_amount"], 0)
    try:
        executed_float = float(executed)
    except (TypeError, ValueError):
        executed_float = 0.0

    if executed_float > 0:
        return executed_float

    months = parse_month_list(row.get(COL["progress_month"], ""))
    amounts = parse_money_list(row.get(COL["progress_amount"], ""))
    total = 0.0
    for month, amount in zip(months, amounts):
        if 1 <= month <= current_month:
            total += amount
    return total


def get_predicted_progress_amount(row: pd.Series) -> float:
    amounts = parse_money_list(row.get(COL["progress_amount_pred"], ""))
    return float(sum(amounts)) if amounts else 0.0


def has_predicted_progress_until(row: pd.Series, current_month: int) -> bool:
    months = parse_month_list(row.get(COL["progress_month_pred"], ""))
    return any(1 <= month <= current_month for month in months)


def make_stage_summary(df: pd.DataFrame, current_month: int) -> dict[str, float]:
    total_count = len(df)
    po_done_count = count_po_completed(df)
    contract_count = count_contract_registered(df)

    actual_progress_amounts = df.apply(
        lambda row: get_actual_progress_amount(row, current_month), axis=1
    ) if not df.empty else pd.Series(dtype=float)
    executed_count = int((actual_progress_amounts > 0).sum()) if not actual_progress_amounts.empty else 0

    invest_sum = float(df[COL["invest_cost"]].sum()) if not df.empty else 0.0
    po_sum = float(df[COL["po_amount"]].sum()) if not df.empty else 0.0
    executed_sum = float(df[COL["executed_amount"]].sum()) if not df.empty else 0.0
    predicted_sum = float(df.apply(get_predicted_progress_amount, axis=1).sum()) if not df.empty else 0.0

    delayed_po_count = int(
        df.apply(
            lambda row: (
                not is_po_completed_value(row.get(COL["po_done"], ""))
                and (extract_month(row.get(COL["leader_plan_month"], "")) or 99) < current_month
            ),
            axis=1,
        ).sum()
    ) if not df.empty else 0

    po_done_mask = df[COL["po_done"]].map(is_po_completed_value) if not df.empty else pd.Series(dtype=bool)
    contract_mask = df[COL["contract_done"]].map(is_contract_registered_value) if not df.empty else pd.Series(dtype=bool)
    contract_backlog_count = int((po_done_mask & ~contract_mask).sum()) if not df.empty else 0

    execution_backlog_count = int(
        df.apply(
            lambda row: (
                is_po_completed_value(row.get(COL["po_done"], ""))
                and get_actual_progress_amount(row, current_month) <= 0
                and (
                    has_predicted_progress_until(row, current_month)
                    or is_contract_registered_value(row.get(COL["contract_done"], ""))
                )
            ),
            axis=1,
        ).sum()
    ) if not df.empty else 0

    return {
        "total_count": total_count,
        "po_done_count": po_done_count,
        "contract_count": contract_count,
        "executed_count": executed_count,
        "invest_sum": invest_sum,
        "po_sum": po_sum,
        "executed_sum": executed_sum,
        "predicted_sum": predicted_sum,
        "po_completion_rate": safe_divide(po_done_count, total_count) * 100,
        "contract_conversion_rate": safe_divide(contract_count, po_done_count) * 100,
        "execution_conversion_rate": safe_divide(executed_count, contract_count) * 100,
        "amount_execution_rate": safe_divide(executed_sum, po_sum) * 100,
        "delayed_po_count": delayed_po_count,
        "contract_backlog_count": contract_backlog_count,
        "execution_backlog_count": execution_backlog_count,
        "unexecuted_amount": max(po_sum - executed_sum, 0),
        "expected_year_end_execution_rate": safe_divide(predicted_sum, po_sum) * 100,
    }


def build_stage_flow_chart(summary: dict[str, float]) -> go.Figure:
    chart_df = pd.DataFrame(
        {
            "단계": ["전체 투자", "품의완료", "계약등록", "집행발생"],
            "건수": [
                summary.get("total_count", 0),
                summary.get("po_done_count", 0),
                summary.get("contract_count", 0),
                summary.get("executed_count", 0),
            ],
        }
    )
    total = max(float(summary.get("total_count", 0)), 1.0)
    chart_df["전체대비"] = chart_df["건수"] / total * 100

    fig = go.Figure(
        go.Bar(
            x=chart_df["전체대비"],
            y=chart_df["단계"],
            orientation="h",
            marker_color=THEME["executed"],
            text=[
                f"{int(count):,}건 · {rate:.1f}%"
                for count, rate in zip(chart_df["건수"], chart_df["전체대비"])
            ],
            textposition="inside",
            hovertemplate="단계=%{y}<br>전체대비=%{x:.1f}%<extra></extra>",
        )
    )
    fig.update_layout(
        height=260,
        margin=dict(l=18, r=18, t=28, b=18),
        xaxis_title="전체 투자건수 대비 비율(%)",
        yaxis_title=None,
        xaxis_range=[0, 100],
        font=dict(size=THEME["main_plot_font_size"]),
        showlegend=False,
    )
    fig.update_yaxes(autorange="reversed")
    return fig


def make_bottleneck_table(df: pd.DataFrame, current_month: int) -> pd.DataFrame:
    rows: list[dict] = []
    if df.empty:
        return pd.DataFrame(columns=["NO", "조직", "담당자", "투자명", "진단단계", "진단내용", "관리포인트"])

    for _, row in df.iterrows():
        no = row.get(COL["no"], "")
        base = {
            "NO": no,
            "조직": row.get(COL["org"], ""),
            "담당자": row.get(COL["owner"], ""),
            "투자명": row.get(COL["title"], ""),
        }

        plan_month = extract_month(row.get(COL["leader_plan_month"], ""))
        po_done = is_po_completed_value(row.get(COL["po_done"], ""))
        contract_done = is_contract_registered_value(row.get(COL["contract_done"], ""))
        actual_amount = get_actual_progress_amount(row, current_month)
        predicted_due = has_predicted_progress_until(row, current_month)
        unexecuted = max(float(row.get(COL["po_amount"], 0)) - float(row.get(COL["executed_amount"], 0)), 0)

        if not po_done and plan_month is not None and plan_month < current_month:
            rows.append(
                {
                    **base,
                    "진단단계": "품의 지연",
                    "진단내용": f"팀장심의예정 {plan_month}월 경과 후 품의 미완료",
                    "관리포인트": "심의 의견/보완 필요사항 확인",
                }
            )
        elif po_done and not contract_done:
            rows.append(
                {
                    **base,
                    "진단단계": "계약 대기",
                    "진단내용": "품의완료 후 계약등록 미완료",
                    "관리포인트": "계약등록 예정월 또는 구매 진행상태 확인",
                }
            )
        elif po_done and actual_amount <= 0 and (contract_done or predicted_due):
            rows.append(
                {
                    **base,
                    "진단단계": "집행 대기",
                    "진단내용": "품의/계약 이후 기준월까지 집행금액 미발생",
                    "관리포인트": "기성단계·검수·세금계산서 처리 상태 확인",
                }
            )
        elif po_done and unexecuted > 0 and actual_amount > 0:
            rows.append(
                {
                    **base,
                    "진단단계": "잔여 집행",
                    "진단내용": f"잔여 집행금액 {fmt_eok_from_won(unexecuted)}",
                    "관리포인트": "잔여 기성단계와 월별 집행예측 점검",
                }
            )

    result = pd.DataFrame(rows)
    if result.empty:
        return pd.DataFrame(columns=["NO", "조직", "담당자", "투자명", "진단단계", "진단내용", "관리포인트"])

    stage_order = pd.CategoricalDtype(
        ["품의 지연", "계약 대기", "집행 대기", "잔여 집행"],
        ordered=True,
    )
    result["진단단계"] = result["진단단계"].astype(stage_order)
    result = result.sort_values(["진단단계", "NO"], ascending=[True, True])
    result["진단단계"] = result["진단단계"].astype(str)
    return result


def render_stage_overview(df: pd.DataFrame, current_month: int) -> None:
    """투자 진행 상세현황 탭의 상단 요약/병목 진단 영역입니다."""
    summary = make_stage_summary(df, current_month)

    render_mini_kpi_grid(
        [
            {
                "label": "품의완료율",
                "value": fmt_pct(summary["po_completion_rate"]),
                "caption": f"{fmt_count(summary['po_done_count'])} / {fmt_count(summary['total_count'])}",
                "tone": "good",
            },
            {
                "label": "품의→계약 전환율",
                "value": fmt_pct(summary["contract_conversion_rate"]),
                "caption": f"계약등록 {fmt_count(summary['contract_count'])}",
                "tone": "normal",
            },
            {
                "label": "계약→집행 발생률",
                "value": fmt_pct(summary["execution_conversion_rate"]),
                "caption": f"집행발생 {fmt_count(summary['executed_count'])}",
                "tone": "normal",
            },
            {
                "label": "금액 기준 집행률",
                "value": fmt_pct(summary["amount_execution_rate"]),
                "caption": f"집행 {fmt_eok_from_won(summary['executed_sum'])} / 품의 {fmt_eok_from_won(summary['po_sum'])}",
                "tone": "good" if summary["amount_execution_rate"] >= 70 else "warn",
            },
            {
                "label": "품의 지연",
                "value": fmt_count(summary["delayed_po_count"]),
                "caption": "팀장심의예정월 경과 후 미완료",
                "tone": "bad" if summary["delayed_po_count"] > 0 else "good",
            },
            {
                "label": "계약 대기",
                "value": fmt_count(summary["contract_backlog_count"]),
                "caption": "품의완료 후 계약등록 전",
                "tone": "warn" if summary["contract_backlog_count"] > 0 else "good",
            },
            {
                "label": "집행 대기",
                "value": fmt_count(summary["execution_backlog_count"]),
                "caption": "품의/계약 후 기준월 집행 미발생",
                "tone": "warn" if summary["execution_backlog_count"] > 0 else "good",
            },
            {
                "label": "잔여 집행금액",
                "value": fmt_eok_from_won(summary["unexecuted_amount"]),
                "caption": "품의금액 - 기성처리금액",
                "tone": "normal",
            },
        ],
        columns=4,
    )

    flow_col, bottleneck_col = st.columns([0.95, 1.55], gap="medium")
    with flow_col:
        st.markdown("<div class='chart-subtitle'>단계별 진행 전환 흐름</div>", unsafe_allow_html=True)
        st.plotly_chart(
            force_full_width_plot(build_stage_flow_chart(summary)),
            use_container_width=True,
            config={"responsive": True},
            key="detail_stage_flow_chart",
        )

    with bottleneck_col:
        st.markdown("<div class='chart-subtitle'>관리 필요 투자 진단</div>", unsafe_allow_html=True)
        bottleneck = make_bottleneck_table(df, current_month)
        if bottleneck.empty:
            st.success("현재 기준월에서 주요 지연/병목으로 분류된 투자 건이 없습니다.")
        else:
            st.dataframe(
                bottleneck.head(12),
                use_container_width=True,
                hide_index=True,
                height=260,
            )


def make_stage_detail_table(df: pd.DataFrame, current_month: int) -> pd.DataFrame:
    """상세 탭용 건별 단계 진단 테이블입니다."""
    rows: list[dict] = []
    for _, row in df.iterrows():
        po_done = is_po_completed_value(row.get(COL["po_done"], ""))
        contract_done = is_contract_registered_value(row.get(COL["contract_done"], ""))
        actual_amount = get_actual_progress_amount(row, current_month)
        po_amount = float(row.get(COL["po_amount"], 0))
        executed_amount = float(row.get(COL["executed_amount"], 0))
        execution_rate = safe_divide(executed_amount, po_amount) * 100
        plan_month = extract_month(row.get(COL["leader_plan_month"], ""))
        contract_month = extract_month(row.get(COL["contract_month"], ""))
        progress_months = parse_month_list(row.get(COL["progress_month"], ""))
        progress_stages = str(row.get(COL["progress_stage"], "")).strip()

        if not po_done and plan_month is not None and plan_month < current_month:
            status = "품의 지연"
        elif po_done and not contract_done:
            status = "계약 대기"
        elif po_done and contract_done and actual_amount <= 0:
            status = "집행 대기"
        elif execution_rate >= 99.9 and po_amount > 0:
            status = "집행 완료"
        elif actual_amount > 0:
            status = "부분 집행"
        else:
            status = "진행 예정"

        rows.append(
            {
                "NO": row.get(COL["no"], ""),
                "조직": row.get(COL["org"], ""),
                "담당자": row.get(COL["owner"], ""),
                "투자명": row.get(COL["title"], ""),
                "현재단계": status,
                "품의완료": "완료" if po_done else "미완료",
                "계약등록": "등록" if contract_done else "미등록",
                "심의예정월": f"{plan_month}월" if plan_month else "-",
                "계약월": f"{contract_month}월" if contract_month else "-",
                "기성월": ", ".join(f"{m}월" for m in progress_months) if progress_months else "-",
                "기성단계": progress_stages if progress_stages else "-",
                "품의금액": fmt_eok_from_won(po_amount),
                "기성처리금액": fmt_eok_from_won(executed_amount),
                "집행률": fmt_pct(execution_rate),
            }
        )

    return pd.DataFrame(rows)

def show_po_detail_monitoring(df: pd.DataFrame, current_month: int, current_label: str) -> None:
    st.markdown(
        f"<div class='section-title'>{current_label}까지 품의 상세 모니터링</div>",
        unsafe_allow_html=True,
    )

    if df.empty:
        st.warning("품의 상세 모니터링을 표시할 데이터가 없습니다.")
        return

    stage_summary = make_stage_summary(df, current_month)
    render_mini_kpi_grid(
        [
            {
                "label": "품의 대상건수",
                "value": fmt_count(stage_summary["total_count"]),
                "caption": "현재 조건의 전체 투자 건",
            },
            {
                "label": "품의완료 건수",
                "value": fmt_count(stage_summary["po_done_count"]),
                "caption": "기본품의완료 기준",
                "tone": "good",
            },
            {
                "label": "품의완료율",
                "value": fmt_pct(stage_summary["po_completion_rate"]),
                "caption": "품의완료 / 전체 투자건수",
                "tone": "good" if stage_summary["po_completion_rate"] >= 80 else "warn",
            },
            {
                "label": "품의 지연건",
                "value": fmt_count(stage_summary["delayed_po_count"]),
                "caption": "예정월 경과 후 미완료",
                "tone": "bad" if stage_summary["delayed_po_count"] > 0 else "good",
            },
            {
                "label": "품의 완료금액",
                "value": fmt_eok_from_won(stage_summary["po_sum"]),
                "caption": "기본품의금액 합계",
            },
            {
                "label": "전체 투자금액",
                "value": fmt_eok_from_won(stage_summary["invest_sum"]),
                "caption": "투자비 합계",
            },
        ],
        columns=3,
    )

    po_status_df = org_po_completion_table(selected_df=df, total_df=None)
    monthly_po_df = monthly_po_amount_table(df, current_month)
    org_chart_order = unique_sorted(df[COL["org"]])

    chart_col1, chart_col2 = st.columns(2, gap="medium")

    with chart_col1:
        st.markdown("<div class='chart-subtitle'>조직별 품의완료 건수</div>", unsafe_allow_html=True)
        st.plotly_chart(
            force_full_width_plot(
                apply_main_chart_layout(
                    apply_org_order_to_horizontal_bar(
                        build_org_po_completion_bar(po_status_df),
                        org_chart_order,
                    )
                )
            ),
            use_container_width=True,
            config={"responsive": True},
            key="po_detail_org_completion_chart",
        )

    with chart_col2:
        st.markdown("<div class='chart-subtitle'>월별 누적 품의금액</div>", unsafe_allow_html=True)
        st.plotly_chart(
            force_full_width_plot(
                apply_main_chart_layout(build_monthly_po_amount_line(monthly_po_df))
            ),
            use_container_width=True,
            config={"responsive": True},
            key="po_detail_monthly_amount_chart",
        )

    st.markdown("<div class='chart-subtitle'>월별 품의 상세 테이블</div>", unsafe_allow_html=True)
    display = monthly_po_df[
        ["월표시", "투자건수", "품의금액", "누적품의금액"]
    ].copy()
    display["품의금액"] = display["품의금액"].map(fmt_eok)
    display["누적품의금액"] = display["누적품의금액"].map(fmt_eok)
    display = display.rename(
        columns={
            "월표시": "월",
            "투자건수": "월별 투자건수",
            "품의금액": "월별 품의금액",
        }
    )
    st.dataframe(display, use_container_width=True, hide_index=True)


def show_contract_detail_monitoring(df: pd.DataFrame, current_month: int, current_label: str) -> None:
    st.markdown(
        f"<div class='section-title'>{current_label}까지 계약 상세 모니터링</div>",
        unsafe_allow_html=True,
    )

    if df.empty:
        st.warning("계약 상세 모니터링을 표시할 데이터가 없습니다.")
        return

    stage_summary = make_stage_summary(df, current_month)
    render_mini_kpi_grid(
        [
            {
                "label": "품의완료 건수",
                "value": fmt_count(stage_summary["po_done_count"]),
                "caption": "계약 전환 대상",
            },
            {
                "label": "계약등록 건수",
                "value": fmt_count(stage_summary["contract_count"]),
                "caption": "계약등록 완료 기준",
                "tone": "good",
            },
            {
                "label": "품의→계약 전환율",
                "value": fmt_pct(stage_summary["contract_conversion_rate"]),
                "caption": "계약등록 / 품의완료",
                "tone": "good" if stage_summary["contract_conversion_rate"] >= 80 else "warn",
            },
            {
                "label": "계약 대기건",
                "value": fmt_count(stage_summary["contract_backlog_count"]),
                "caption": "품의완료 후 계약 미등록",
                "tone": "warn" if stage_summary["contract_backlog_count"] > 0 else "good",
            },
        ],
        columns=4,
    )

    contract_status_df = org_contract_registration_table(selected_df=df, total_df=None)
    monthly_contract_df = monthly_contract_table(df, current_month)
    org_chart_order = unique_sorted(df[COL["org"]])

    chart_col1, chart_col2 = st.columns(2, gap="medium")

    with chart_col1:
        st.markdown("<div class='chart-subtitle'>조직별 계약건수</div>", unsafe_allow_html=True)
        st.plotly_chart(
            force_full_width_plot(
                apply_main_chart_layout(
                    apply_org_order_to_horizontal_bar(
                        build_org_contract_registration_bar(contract_status_df),
                        org_chart_order,
                    )
                )
            ),
            use_container_width=True,
            config={"responsive": True},
            key="contract_detail_org_registration_chart",
        )

    with chart_col2:
        st.markdown("<div class='chart-subtitle'>월별 누적 계약건수</div>", unsafe_allow_html=True)
        st.plotly_chart(
            force_full_width_plot(
                apply_main_chart_layout(build_monthly_contract_line(monthly_contract_df))
            ),
            use_container_width=True,
            config={"responsive": True},
            key="contract_detail_monthly_line_chart",
        )

    st.markdown("<div class='chart-subtitle'>월별 계약 상세 테이블</div>", unsafe_allow_html=True)
    display = monthly_contract_df[
        ["월표시", "계약건수", "누적계약건수", "품의완료건수", "누적품의완료건수"]
    ].copy()
    display = display.rename(
        columns={
            "월표시": "월",
            "계약건수": "월별 계약건수",
            "누적계약건수": "누적 계약건수",
            "품의완료건수": "월별 품의완료건수",
            "누적품의완료건수": "누적 품의완료건수",
        }
    )
    st.dataframe(display, use_container_width=True, hide_index=True)


def show_execution_detail_monitoring(df: pd.DataFrame, current_month: int, current_label: str) -> None:
    st.markdown(
        f"<div class='section-title'>{current_label}까지 집행 상세 모니터링</div>",
        unsafe_allow_html=True,
    )

    if df.empty:
        st.warning("집행 상세 모니터링을 표시할 데이터가 없습니다.")
        return

    stage_summary = make_stage_summary(df, current_month)
    render_mini_kpi_grid(
        [
            {
                "label": "품의금액",
                "value": fmt_eok_from_won(stage_summary["po_sum"]),
                "caption": "집행률 산정 기준 금액",
            },
            {
                "label": "기성처리금액",
                "value": fmt_eok_from_won(stage_summary["executed_sum"]),
                "caption": "기준월까지 실제 집행",
                "tone": "good",
            },
            {
                "label": "금액 기준 집행률",
                "value": fmt_pct(stage_summary["amount_execution_rate"]),
                "caption": "기성처리금액 / 품의금액",
                "tone": "good" if stage_summary["amount_execution_rate"] >= 70 else "warn",
            },
            {
                "label": "계약→집행 발생률",
                "value": fmt_pct(stage_summary["execution_conversion_rate"]),
                "caption": "집행발생 건 / 계약등록 건",
                "tone": "normal",
            },
            {
                "label": "집행 대기건",
                "value": fmt_count(stage_summary["execution_backlog_count"]),
                "caption": "품의/계약 후 집행 미발생",
                "tone": "warn" if stage_summary["execution_backlog_count"] > 0 else "good",
            },
            {
                "label": "예상 연말 집행률",
                "value": fmt_pct(stage_summary["expected_year_end_execution_rate"]),
                "caption": "예측 기성금액 / 품의금액",
                "tone": "normal",
            },
        ],
        columns=3,
    )

    org_df = org_execution_table(selected_df=df, total_df=None)
    monthly_df = monthly_progress_table(df, current_month)
    org_chart_order = unique_sorted(df[COL["org"]])

    chart_col1, chart_col2 = st.columns(2, gap="medium")

    with chart_col1:
        st.markdown("<div class='chart-subtitle'>조직별 집행금액</div>", unsafe_allow_html=True)
        st.plotly_chart(
            force_full_width_plot(
                apply_main_chart_layout(
                    apply_org_order_to_horizontal_bar(
                        build_org_stacked_bar(org_df),
                        org_chart_order,
                    )
                )
            ),
            use_container_width=True,
            config={"responsive": True},
            key="execution_detail_org_amount_chart",
        )

    with chart_col2:
        st.markdown("<div class='chart-subtitle'>월별 누적 집행률</div>", unsafe_allow_html=True)
        st.plotly_chart(
            force_full_width_plot(
                apply_main_chart_layout(build_monthly_line(monthly_df))
            ),
            use_container_width=True,
            config={"responsive": True},
            key="execution_detail_monthly_line_chart",
        )

    st.markdown("<div class='chart-subtitle'>월별 집행 상세 테이블</div>", unsafe_allow_html=True)
    display = monthly_df[
        [
            "월표시",
            "기성금액",
            "누적기성금액",
            "누적집행률",
            "기성금액_예측",
            "누적기성금액_예측",
            "예측누적집행률",
        ]
    ].copy()
    for col in ["기성금액", "누적기성금액", "기성금액_예측", "누적기성금액_예측"]:
        display[col] = display[col].map(fmt_eok)
    for col in ["누적집행률", "예측누적집행률"]:
        display[col] = display[col].map(fmt_pct)
    display = display.rename(
        columns={
            "월표시": "월",
            "기성금액": "월별 집행금액",
            "누적기성금액": "누적 집행금액",
            "기성금액_예측": "예상 월별 집행금액",
            "누적기성금액_예측": "예상 누적 집행금액",
        }
    )
    st.dataframe(display, use_container_width=True, hide_index=True)


def show_status_monthly_tab(
    df: pd.DataFrame,
    current_month: int,
    current_label: str,
) -> None:
    st.markdown(
        f"<div class='section-title'>{current_label} 기준 투자 진행 상세 현황</div>",
        unsafe_allow_html=True,
    )

    if df.empty:
        st.warning("투자 진행 상세 현황을 표시할 데이터가 없습니다.")
        return

    render_stage_overview(df, current_month)

    st.divider()

    po_detail_tab, contract_detail_tab, exec_detail_tab = st.tabs(
        ["품의 상세 모니터링", "계약 상세 모니터링", "집행 상세 모니터링"]
    )

    with po_detail_tab:
        show_po_detail_monitoring(df, current_month, current_label)

    with contract_detail_tab:
        show_contract_detail_monitoring(df, current_month, current_label)

    with exec_detail_tab:
        show_execution_detail_monitoring(df, current_month, current_label)

    st.divider()

    st.markdown(
        "<div class='section-title'>건별 단계 진단 테이블</div>",
        unsafe_allow_html=True,
    )
    stage_detail = make_stage_detail_table(df, current_month)
    st.dataframe(
        stage_detail,
        use_container_width=True,
        hide_index=True,
        height=360,
    )

    st.divider()

    st.markdown(
        "<div class='section-title'>월별 비교 테이블</div>",
        unsafe_allow_html=True,
    )
    show_monthly_compare_table_only(df, current_month)


# ============================================================
# 4) 앱 실행부
# ============================================================
def main() -> None:
    st.markdown(
        f"<div class='small-title'>{html.escape(APP_CONFIG['team_name'])}</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        f"<div class='big-title'>{html.escape(APP_CONFIG['dashboard_title'])}</div>",
        unsafe_allow_html=True,
    )

    all_data, current_month, current_label = load_current_data()

    st.markdown(
        f"<div class='desc'>현재 입력 데이터의 기준월을 <b>{current_label}</b>로 인식했습니다. "
        "조직, 계획구분, 품의상태, 심의상태별 투자 및 집행 현황을 확인합니다.</div>",
        unsafe_allow_html=True,
    )

    st.sidebar.markdown("### 기준 정보")
    st.sidebar.info(f"현재 기준월: {current_label}")
    st.sidebar.caption(f"입력 파일: {DATA_FILE.name}")

    filtered_data = apply_filters(all_data)

    if filtered_data.empty:
        st.warning("현재 필터 조건에 해당하는 데이터가 없습니다. 왼쪽 필터를 조정해 주세요.")
        st.stop()

    tab1, tab2 = st.tabs(APP_CONFIG["tab_titles"])

    with tab1:
        org_filtered_data = show_dashboard_tab(
            filtered_data,
            current_month,
            current_label,
            detail_base_df=all_data,
        )

    with tab2:
        show_status_monthly_tab(
            org_filtered_data,
            current_month,
            current_label,
        )


if __name__ == "__main__":
    main()
