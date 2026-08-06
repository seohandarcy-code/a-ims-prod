"""legacy calculate_kpi_values 이식."""
from __future__ import annotations

import pandas as pd

from app.calc.helpers import count_po_completed, money_eok, safe_divide
from app.data.columns import COL


def calculate_kpi_values(df: pd.DataFrame) -> dict[str, dict[str, str]]:
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
