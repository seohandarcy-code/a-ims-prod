"""legacy read_dat / detect_delimiter 이식."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def detect_delimiter(path: str | Path, encoding: str) -> str:
    with open(path, "r", encoding=encoding, errors="ignore") as f:
        first_line = f.readline()

    candidates = ["\t", "|", ";"]
    counts = {sep: first_line.count(sep) for sep in candidates}
    best_sep = max(counts, key=counts.get)

    return best_sep if counts[best_sep] > 0 else "\t"


def read_dat(path: str | Path) -> pd.DataFrame:
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

        except Exception as exc:  # noqa: BLE001
            last_error = exc
            continue

    raise RuntimeError(f"DAT 파일을 읽지 못했습니다: {path}\n{last_error}")
