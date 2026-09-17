"""app/db/seed.py, app/db/export.py 단위 테스트 (API/DataStore를 거치지 않고 직접 검증)."""
from __future__ import annotations

import json

from sqlalchemy import delete, insert, update

from app.config import BASE_FILE
from app.data.loader import read_dat
from app.db.engine import engine
from app.db.export import export_to_dat, fetch_raw_dataframe
from app.db.models import custom_column_defs, custom_column_values, investment_rows
from app.db.seed import is_empty, replace_all_from_dataframe, seed_if_empty


def test_seed_if_empty_seeds_from_base_file_when_db_empty():
    assert is_empty()

    seed_if_empty()

    base_df = read_dat(BASE_FILE)
    raw_df, _custom_types = fetch_raw_dataframe()
    assert len(raw_df) == len(base_df)
    assert not is_empty()


def test_seed_if_empty_is_noop_when_db_already_has_data():
    seed_if_empty()

    with engine.begin() as conn:
        conn.execute(update(investment_rows).where(investment_rows.c.no == 1).values(org="시드후변경"))

    seed_if_empty()  # 이미 데이터가 있으므로 재시딩되면 안 된다 (덮어쓰면 방금 바꾼 값이 사라짐)

    raw_df, _custom_types = fetch_raw_dataframe()
    row1 = raw_df.loc[raw_df["NO"] == "1"].iloc[0]
    assert row1["PJT"] == "시드후변경"


def test_export_to_dat_round_trip(tmp_path):
    seed_if_empty()

    with engine.begin() as conn:
        conn.execute(delete(custom_column_values))
        conn.execute(delete(custom_column_defs))
        conn.execute(insert(custom_column_defs), {"key": "테스트컬럼", "col_type": "text"})

    raw_df_before, custom_types_before = fetch_raw_dataframe()

    dest = tmp_path / "backup.dat"
    types_dest = tmp_path / "backup_column_types.json"
    export_to_dat(dest, types_dest)

    # DB를 완전히 비우고 방금 내보낸 백업으로 재시딩했을 때 원래 상태와 동일해야 한다
    # (로컬 개발 환경을 운영 백업으로 재구성하는 시나리오와 동일한 코드 경로).
    with engine.begin() as conn:
        conn.execute(delete(custom_column_values))
        conn.execute(delete(custom_column_defs))
        conn.execute(delete(investment_rows))

    reseeded_df = read_dat(dest)
    with open(types_dest, "r", encoding="utf-8-sig") as f:
        reseeded_types = json.load(f)

    replace_all_from_dataframe(reseeded_df, reseeded_types)

    raw_df_after, custom_types_after = fetch_raw_dataframe()
    assert raw_df_after.equals(raw_df_before)
    assert custom_types_after == custom_types_before
