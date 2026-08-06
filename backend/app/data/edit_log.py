"""append-only 편집 이력(edit_log.jsonl) 스키마와 재생(replay) 로직.

plan_v5의 No-DB 구조를 위한 읽기 측 구현이다. 이번 라운드에는 이 로그에
실제로 append하는 편집 API가 없어 파일은 항상 비어 있지만, DataStore는
기동 시마다 이 로그를 처음부터 재생해 base 데이터 위에 편집을 반영하는
구조를 그대로 갖춘다. 다음 라운드에서 편집 API가 로그에 라인을 추가하기
시작하면 이 함수를 다시 손대지 않아도 된다.

한 줄(JSON) 스키마:
    {
        "timestamp": "2026-07-17T10:00:00+09:00",
        "wbs_code": "WBS-2026-001",
        "field": "팀장심의_의견",
        "old_value": "-",
        "new_value": "승인",
        "editor": "admin"
    }
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from app.data.columns import COL


def replay(df: pd.DataFrame, log_path: str | Path) -> pd.DataFrame:
    log_path = Path(log_path)

    if not log_path.exists():
        return df

    df = df.copy()
    wbs_col = COL["wbs"]

    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            entry = json.loads(line)
            wbs_code = entry.get("wbs_code")
            field = entry.get("field")
            new_value = entry.get("new_value")

            if wbs_code is None or field is None or field not in df.columns:
                continue

            df.loc[df[wbs_col] == wbs_code, field] = new_value

    return df
