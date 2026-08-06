"""No-DB 데이터 계층: base 또는 data_rev 스냅샷을 메모리에 보관.

기동 시 한 번 로드하고, 이후 요청은 메모리 상의 정규화 결과를 사용한다
(legacy load_current_data의 @st.cache_data 캐시 역할을 서버 프로세스 수준에서 대체).

편집(edit_row/add_row)은 append-only 이력을 남기지 않고, raw 데이터 전체를
매번 data_rev/*_rev.dat에 덮어쓰는 스냅샷 방식이다. load()는 이 rev 파일이
있으면 그것을, 없으면 base 원본을 읽는다 — 서버가 재기동해도 마지막으로
저장된 편집 상태를 그대로 이어서 시작한다.

관리자가 추가한 커스텀 컬럼의 타입(text/money/date)은 raw_df 자체에는
담기지 않으므로 별도 sidecar json(CUSTOM_COLUMN_TYPES_FILE)에 저장한다.
"""
from __future__ import annotations

import json
import logging
import re
import threading

import pandas as pd

from app.config import (
    BASE_FILE,
    CUSTOM_COLUMN_TYPES_BACKUP_FILE,
    CUSTOM_COLUMN_TYPES_FILE,
    REV_BACKUP_FILE,
    REV_FILE,
)
from app.data.columns import COL, MONEY_COLS, PROGRESS_PAIRS
from app.data.loader import read_dat
from app.data.normalize import infer_current_month, normalize_data
from app.data.writer import atomic_write_dat, atomic_write_json

logger = logging.getLogger(__name__)

CUSTOM_COLUMN_TYPES = ("text", "money", "date")

# normalize_data가 만들어내는 파생 컬럼명 — 커스텀 컬럼이 이 이름을 쓰면
# 계산용 정규화본에서 값이 조용히 덮어써지므로 예약어로 막는다.
_RESERVED_COLUMN_NAMES = {
    "집행률",
    "품의율",
    "미집행금액",
    "담당자변경",
    "투자명변경",
    "심의예정월_숫자",
    "심의진행월_숫자",
}

# .dat(탭) 저장/멀티값(/,|,;) 구분자와 충돌을 막기 위해 컬럼명에 금지하는 문자.
_FORBIDDEN_NAME_CHARS = set("\t\n\r|;/\"")


class RowNotFoundError(RuntimeError):
    pass


class InvalidFieldError(RuntimeError):
    pass


def _split_multi(value: object) -> list[str]:
    return [token for token in re.split(r"[/|;]+", str(value or "")) if token.strip()]


def _validate_fields(
    fields: dict[str, str],
    merged: dict[str, str],
    extra_money_fields: set[str] | None = None,
) -> None:
    """편집 결과(merged)를 저장하기 전 하이브리드 검증.

    금액 형식과 기성_월/기성_금액 쌍의 구분 개수 불일치만 하드블록한다(400).
    개수 검증은 이번 fields에 그 쌍의 필드가 하나라도 포함된 경우에만 수행 —
    과거에 이미 어긋나 있던 무관한 필드가 향후 모든 편집을 영구 차단하지
    않도록 하기 위함(감사이력이 없어 오탐 거부의 복구 비용이 큼).
    """
    money_fields = set(MONEY_COLS) | (extra_money_fields or set())

    for field, value in fields.items():
        if field in money_fields and value.strip():
            cleaned = value.replace("원", "").replace(",", "").replace(" ", "").strip()
            if not re.fullmatch(r"-?\d+", cleaned):
                raise InvalidFieldError(f"{field}는 숫자만 입력해야 합니다: {value!r}")

    for month_col, amount_col in PROGRESS_PAIRS:
        if month_col not in fields and amount_col not in fields:
            continue

        month_count = len(_split_multi(merged.get(month_col, "")))
        amount_count = len(_split_multi(merged.get(amount_col, "")))

        if month_count != amount_count:
            raise InvalidFieldError(
                f"{month_col}과 {amount_col}의 구분 개수가 일치해야 합니다 "
                f"({month_count}개 vs {amount_count}개)."
            )


def _validate_column_name(name: str, raw_df: pd.DataFrame) -> None:
    if not name:
        raise InvalidFieldError("컬럼명을 입력해주세요.")
    if any(ch in _FORBIDDEN_NAME_CHARS for ch in name):
        raise InvalidFieldError("컬럼명에 사용할 수 없는 문자가 포함되어 있습니다.")
    if name in raw_df.columns:
        raise InvalidFieldError(f"이미 존재하는 컬럼입니다: {name}")
    if name in _RESERVED_COLUMN_NAMES:
        raise InvalidFieldError(f"예약된 이름이라 사용할 수 없습니다: {name}")


class DataStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._raw_df: pd.DataFrame | None = None
        self._df: pd.DataFrame | None = None
        self._current_month: int | None = None
        self._current_label: str | None = None
        self._ready: bool = False
        self._custom_column_types: dict[str, str] = {}

    @property
    def is_ready(self) -> bool:
        return self._ready

    def load(self) -> None:
        with self._lock:
            self._load_locked()

    def refresh(self) -> None:
        self.load()

    def _load_locked(self) -> None:
        """self._lock을 이미 쥐고 있는 상태에서 호출한다(재진입 금지)."""
        source = REV_FILE if REV_FILE.exists() else BASE_FILE
        logger.info("데이터 로드 시작: source=%s", source)
        try:
            raw_df = read_dat(source)
            normalized_df = normalize_data(raw_df)
            current_month = infer_current_month(normalized_df)

            if CUSTOM_COLUMN_TYPES_FILE.exists():
                with open(CUSTOM_COLUMN_TYPES_FILE, "r", encoding="utf-8-sig") as f:
                    self._custom_column_types = json.load(f)
            else:
                self._custom_column_types = {}

            self._raw_df = raw_df
            self._df = normalized_df
            self._current_month = current_month
            self._current_label = f"2026년 {current_month}월"
            self._ready = True
        except Exception:
            self._ready = False
            logger.exception("데이터 로드 실패")
            raise

        logger.info(
            "데이터 로드 완료: rows=%d current_month=%s",
            len(normalized_df),
            current_month,
        )

    def get_df(self) -> pd.DataFrame:
        if self._df is None:
            self.load()
        assert self._df is not None
        return self._df

    def get_raw_df(self) -> pd.DataFrame:
        if self._raw_df is None:
            self.load()
        assert self._raw_df is not None
        return self._raw_df

    def get_current_month(self) -> int:
        if self._current_month is None:
            self.load()
        assert self._current_month is not None
        return self._current_month

    def get_current_label(self) -> str:
        if self._current_label is None:
            self.load()
        assert self._current_label is not None
        return self._current_label

    def get_column_types(self) -> dict[str, str]:
        if self._raw_df is None:
            self.load()
        return dict(self._custom_column_types)

    def _backup_before_write(self) -> None:
        """편집 직전 현재 상태를 1단계 백업으로 남긴다(되돌리기용).

        self._lock을 이미 쥐고 있는 상태에서 호출한다(재진입 금지). 매 편집마다
        직전 상태로 덮어써서, 항상 "바로 이전 상태" 1개만 유지한다. 데이터(rev)와
        커스텀 컬럼 타입(sidecar json)을 하나의 편집 단위로 묶어 함께 백업한다.
        """
        source = REV_FILE if REV_FILE.exists() else BASE_FILE
        current_df = read_dat(source)
        atomic_write_dat(current_df, REV_BACKUP_FILE)
        atomic_write_json(self._custom_column_types, CUSTOM_COLUMN_TYPES_BACKUP_FILE)

    def has_backup(self) -> bool:
        return REV_BACKUP_FILE.exists()

    def restore_backup(self) -> None:
        with self._lock:
            if not REV_BACKUP_FILE.exists():
                raise RowNotFoundError("되돌릴 이전 상태가 없습니다.")

            backup_df = read_dat(REV_BACKUP_FILE)
            atomic_write_dat(backup_df, REV_FILE)
            REV_BACKUP_FILE.unlink(missing_ok=True)

            if CUSTOM_COLUMN_TYPES_BACKUP_FILE.exists():
                with open(CUSTOM_COLUMN_TYPES_BACKUP_FILE, "r", encoding="utf-8-sig") as f:
                    restored_types = json.load(f)
            else:
                restored_types = {}
            atomic_write_json(restored_types, CUSTOM_COLUMN_TYPES_FILE)
            CUSTOM_COLUMN_TYPES_BACKUP_FILE.unlink(missing_ok=True)

            self._load_locked()

    def edit_row(self, no: int, fields: dict[str, str]) -> pd.Series:
        no_col = COL["no"]

        with self._lock:
            if self._raw_df is None:
                self._load_locked()

            raw_df = self._raw_df
            assert raw_df is not None

            mask = pd.to_numeric(raw_df[no_col], errors="coerce") == no
            if not bool(mask.any()):
                raise RowNotFoundError(f"NO={no} 행을 찾을 수 없습니다.")

            unknown = [f for f in fields if f not in raw_df.columns]
            if unknown:
                raise InvalidFieldError(f"존재하지 않는 컬럼입니다: {', '.join(unknown)}")
            if no_col in fields:
                raise InvalidFieldError(f"{no_col}는 수정할 수 없습니다.")

            current_row = raw_df.loc[mask].iloc[0].to_dict()
            merged = {**current_row, **fields}
            custom_money_fields = {k for k, v in self._custom_column_types.items() if v == "money"}
            _validate_fields(fields, merged, custom_money_fields)

            self._backup_before_write()

            for field, value in fields.items():
                raw_df.loc[mask, field] = value

            atomic_write_dat(raw_df, REV_FILE)
            self._load_locked()

            result_mask = pd.to_numeric(self._raw_df[no_col], errors="coerce") == no
            return self._raw_df.loc[result_mask].iloc[0]

    def add_row(self, fields: dict[str, str]) -> pd.Series:
        no_col = COL["no"]

        with self._lock:
            if self._raw_df is None:
                self._load_locked()

            raw_df = self._raw_df
            assert raw_df is not None

            unknown = [f for f in fields if f not in raw_df.columns and f != no_col]
            if unknown:
                raise InvalidFieldError(f"존재하지 않는 컬럼입니다: {', '.join(unknown)}")

            new_row = {col: "" for col in raw_df.columns}
            new_row.update({k: v for k, v in fields.items() if k != no_col})
            custom_money_fields = {k for k, v in self._custom_column_types.items() if v == "money"}
            _validate_fields(fields, new_row, custom_money_fields)

            self._backup_before_write()

            existing_no = pd.to_numeric(raw_df[no_col], errors="coerce").fillna(0)
            next_no = int(existing_no.max()) + 1 if len(existing_no) else 1
            new_row[no_col] = str(next_no)

            raw_df = pd.concat([raw_df, pd.DataFrame([new_row])], ignore_index=True)

            atomic_write_dat(raw_df, REV_FILE)
            self._raw_df = raw_df
            self._load_locked()

            result_mask = pd.to_numeric(self._raw_df[no_col], errors="coerce") == next_no
            return self._raw_df.loc[result_mask].iloc[0]

    def delete_row(self, no: int) -> None:
        no_col = COL["no"]

        with self._lock:
            if self._raw_df is None:
                self._load_locked()

            raw_df = self._raw_df
            assert raw_df is not None

            mask = pd.to_numeric(raw_df[no_col], errors="coerce") == no
            if not bool(mask.any()):
                raise RowNotFoundError(f"NO={no} 행을 찾을 수 없습니다.")

            self._backup_before_write()

            raw_df = raw_df.loc[~mask].reset_index(drop=True)

            atomic_write_dat(raw_df, REV_FILE)
            self._raw_df = raw_df
            self._load_locked()

    def add_column(self, name: str, col_type: str) -> None:
        name = name.strip()

        if col_type not in CUSTOM_COLUMN_TYPES:
            raise InvalidFieldError(f"지원하지 않는 컬럼 타입입니다: {col_type}")

        with self._lock:
            if self._raw_df is None:
                self._load_locked()

            raw_df = self._raw_df
            assert raw_df is not None

            _validate_column_name(name, raw_df)

            self._backup_before_write()

            raw_df[name] = ""
            atomic_write_dat(raw_df, REV_FILE)

            self._custom_column_types[name] = col_type
            atomic_write_json(self._custom_column_types, CUSTOM_COLUMN_TYPES_FILE)

            self._load_locked()

    def delete_column(self, key: str) -> None:
        with self._lock:
            if self._raw_df is None:
                self._load_locked()

            raw_df = self._raw_df
            assert raw_df is not None

            if key not in raw_df.columns:
                raise RowNotFoundError(f"컬럼을 찾을 수 없습니다: {key}")
            if key in COL.values():
                raise InvalidFieldError(f"기존 원본 컬럼은 삭제할 수 없습니다: {key}")

            self._backup_before_write()

            raw_df = raw_df.drop(columns=[key])
            atomic_write_dat(raw_df, REV_FILE)

            self._custom_column_types.pop(key, None)
            atomic_write_json(self._custom_column_types, CUSTOM_COLUMN_TYPES_FILE)

            self._raw_df = raw_df
            self._load_locked()


data_store = DataStore()


def get_store() -> DataStore:
    return data_store
