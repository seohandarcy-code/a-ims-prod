"""DB(SQLite, 추후 PostgreSQL) 데이터 계층: DB에 저장된 투자 데이터를 메모리에 캐시.

기동 시 DB가 비어있으면 base 또는 data_rev 스냅샷(.dat)으로 최초 1회 시딩하고
(app/db/seed.py.seed_if_empty), 이후로는 오직 DB만 읽고 쓴다. 매 요청은 메모리
상의 정규화 결과를 사용한다(legacy load_current_data의 @st.cache_data 캐시
역할을 서버 프로세스 수준에서 대체).

이전 파일 기반 버전(2026-09-16 이전)과 동일하게, 편집(edit_row/add_row/...)마다
DB 전체를 다시 조회해 raw_df/정규화본을 재구성한다 — append-only 이력 없이
"현재 상태" 스냅샷만 관리하는 설계를 그대로 유지한다. get_df()/get_raw_df()가
파일 시절과 동일하게 한글 헤더를 가진 pandas DataFrame을 반환하므로,
app/calc/*·app/api/*는 데이터가 파일에서 오는지 DB에서 오는지 알 필요가 없다.

관리자가 추가한 커스텀 컬럼(text/money/date)은 EAV 테이블
(custom_column_defs/custom_column_values)에 저장된다. 되돌리기(undo)는
"바로 이전 상태 1개"만 backup_snapshot 테이블에 JSON으로 보관하는 단일 슬롯
방식이다(기존 REV_BACKUP_FILE과 동일한 의미).
"""
from __future__ import annotations

import json
import logging
import re
import threading
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import delete, insert, select, update

from app.data.columns import COL, HEADER_TO_KEY, MONEY_COLS, PROGRESS_PAIRS
from app.data.normalize import infer_current_month, normalize_data
from app.db.engine import engine
from app.db.export import fetch_raw_dataframe
from app.db.models import backup_snapshot, custom_column_defs, custom_column_values, investment_rows
from app.db.seed import replace_all_from_dataframe, seed_if_empty

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
        logger.info("데이터 로드 시작 (DB)")
        try:
            seed_if_empty()
            raw_df, custom_types = fetch_raw_dataframe()
            normalized_df = normalize_data(raw_df)
            current_month = infer_current_month(normalized_df)

            self._raw_df = raw_df
            self._df = normalized_df
            self._current_month = current_month
            self._current_label = f"2026년 {current_month}월"
            self._custom_column_types = custom_types
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
        """편집 직전 DB 전체 상태를 1단계 백업(단일 슬롯)으로 남긴다(되돌리기용).

        self._lock을 이미 쥐고 있는 상태에서 호출한다(재진입 금지). 매 편집마다
        직전 상태로 덮어써서, 항상 "바로 이전 상태" 1개만 유지한다. 데이터와
        커스텀 컬럼 타입을 하나의 JSON 스냅샷으로 묶어 함께 백업한다.
        """
        raw_df, custom_types = fetch_raw_dataframe()
        data_json = raw_df.to_json(orient="records", force_ascii=False)
        types_json = json.dumps(custom_types, ensure_ascii=False)

        with engine.begin() as conn:
            conn.execute(delete(backup_snapshot))
            conn.execute(
                insert(backup_snapshot),
                {
                    "id": 1,
                    "data_json": data_json,
                    "custom_types_json": types_json,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
            )

    def has_backup(self) -> bool:
        with engine.connect() as conn:
            row = conn.execute(select(backup_snapshot.c.id)).first()
        return row is not None

    def restore_backup(self) -> None:
        with self._lock:
            with engine.connect() as conn:
                row = conn.execute(select(backup_snapshot)).mappings().first()

            if row is None:
                raise RowNotFoundError("되돌릴 이전 상태가 없습니다.")

            backup_df = pd.DataFrame(json.loads(row["data_json"]))
            custom_types = json.loads(row["custom_types_json"])

            replace_all_from_dataframe(backup_df, custom_types)

            with engine.begin() as conn:
                conn.execute(delete(backup_snapshot))

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

            core_updates = {HEADER_TO_KEY[h]: v for h, v in fields.items() if h in HEADER_TO_KEY}
            custom_updates = {h: v for h, v in fields.items() if h not in HEADER_TO_KEY}

            with engine.begin() as conn:
                if core_updates:
                    conn.execute(
                        update(investment_rows).where(investment_rows.c.no == no).values(**core_updates)
                    )
                for header, value in custom_updates.items():
                    conn.execute(
                        update(custom_column_values)
                        .where(
                            custom_column_values.c.row_no == no,
                            custom_column_values.c.column_key == header,
                        )
                        .values(value=value)
                    )

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

            core_values = {
                HEADER_TO_KEY[h]: v for h, v in new_row.items() if h in HEADER_TO_KEY and h != no_col
            }
            custom_values = {h: v for h, v in new_row.items() if h not in HEADER_TO_KEY}

            with engine.begin() as conn:
                conn.execute(insert(investment_rows), {"no": next_no, **core_values})
                if custom_values:
                    conn.execute(
                        insert(custom_column_values),
                        [{"row_no": next_no, "column_key": k, "value": v} for k, v in custom_values.items()],
                    )

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

            with engine.begin() as conn:
                conn.execute(delete(custom_column_values).where(custom_column_values.c.row_no == no))
                conn.execute(delete(investment_rows).where(investment_rows.c.no == no))

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

            with engine.begin() as conn:
                conn.execute(insert(custom_column_defs), {"key": name, "col_type": col_type})

                nos = [int(n) for n in pd.to_numeric(raw_df[COL["no"]], errors="coerce").dropna().tolist()]
                if nos:
                    conn.execute(
                        insert(custom_column_values),
                        [{"row_no": no, "column_key": name, "value": ""} for no in nos],
                    )

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

            with engine.begin() as conn:
                conn.execute(delete(custom_column_values).where(custom_column_values.c.column_key == key))
                conn.execute(delete(custom_column_defs).where(custom_column_defs.c.key == key))

            self._load_locked()


data_store = DataStore()


def get_store() -> DataStore:
    return data_store
