"""원자적 .dat 파일 쓰기.

같은 디렉터리에 임시 파일을 먼저 쓰고 os.replace()로 교체한다. 쓰는 도중
프로세스가 죽어도 원본 파일은 항상 이전 상태 또는 새 상태 중 하나로만
남는다(중간에 깨진 상태로 남지 않음). os.replace()는 Windows/POSIX 양쪽에서
같은 파일시스템 내 이동 시 원자적으로 동작한다.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd


def _atomic_write(path: str | Path, write_fn) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    tmp_path = Path(tmp_name)

    try:
        with os.fdopen(fd, "w", encoding="utf-8-sig", newline="") as f:
            write_fn(f)
        os.replace(tmp_path, path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def atomic_write_dat(df: pd.DataFrame, path: str | Path) -> None:
    _atomic_write(path, lambda f: df.to_csv(f, sep="\t", index=False))


def atomic_write_json(data: Any, path: str | Path) -> None:
    _atomic_write(path, lambda f: json.dump(data, f, ensure_ascii=False, indent=2))
