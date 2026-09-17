"""관리자 원본 데이터 편집(행 수정/추가) 및 DB 저장/재기동 로드 테스트."""
from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import BASE_FILE
from app.data.loader import read_dat
from app.data.store import DataStore
from app.db.engine import engine
from app.db.models import investment_rows
from app.db.seed import replace_all_from_dataframe
from app.main import app


def _login(client: TestClient) -> str:
    r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "0000"})
    return r.json()["token"]


def test_edit_row_success_and_persisted_to_db():
    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        r = client.patch("/api/v1/admin/rows/1", json={"fields": {"PJT": "테스트조직"}}, headers=headers)

    assert r.status_code == 200
    assert r.json()["row"]["PJT"] == "테스트조직"

    with engine.connect() as conn:
        stored = conn.execute(
            select(investment_rows.c.org).where(investment_rows.c.no == 1)
        ).scalar_one()
    assert stored == "테스트조직"


def test_edit_row_not_found():
    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        r = client.patch("/api/v1/admin/rows/999999", json={"fields": {"PJT": "x"}}, headers=headers)

    assert r.status_code == 404


def test_edit_row_rejects_no_field_change():
    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        r = client.patch("/api/v1/admin/rows/1", json={"fields": {"NO": "999"}}, headers=headers)

    assert r.status_code == 400


def test_edit_row_rejects_unknown_column():
    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        r = client.patch("/api/v1/admin/rows/1", json={"fields": {"존재하지않는컬럼": "x"}}, headers=headers)

    assert r.status_code == 400


def test_add_row_autonumbers_and_allows_free_wbs_code():
    base_row_count = len(read_dat(BASE_FILE))

    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        r1 = client.post("/api/v1/admin/rows", json={"fields": {"WBS_Code": "예정"}}, headers=headers)
        r2 = client.post("/api/v1/admin/rows", json={"fields": {"WBS_Code": "예정"}}, headers=headers)

    assert r1.status_code == 201
    assert r2.status_code == 201
    assert int(r1.json()["row"]["NO"]) == base_row_count + 1
    assert int(r2.json()["row"]["NO"]) == base_row_count + 2
    assert r1.json()["row"]["WBS_Code"] == "예정"
    assert r2.json()["row"]["WBS_Code"] == "예정"


def test_restart_reloads_from_db():
    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}
        client.patch("/api/v1/admin/rows/1", json={"fields": {"PJT": "재시작테스트"}}, headers=headers)

    # 새 DataStore 인스턴스로 서버 재기동을 시뮬레이션 - 같은 DATABASE_URL을 가리키므로
    # 편집 내용이 그대로 유지되어야 한다(이미 데이터가 있으니 재시딩되면 안 된다).
    fresh_store = DataStore()
    fresh_store.load()
    raw_df = fresh_store.get_raw_df()

    edited = raw_df.loc[raw_df["NO"].astype(str) == "1", "PJT"].iloc[0]
    assert edited == "재시작테스트"


def test_csv_export():
    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        r = client.get("/api/v1/admin/export/csv", headers=headers)

    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "NO" in r.text.splitlines()[0]


def test_raw_data_reports_money_column_type_and_no_backup_initially():
    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        r = client.get("/api/v1/admin/raw-data", headers=headers)

    assert r.status_code == 200
    body = r.json()
    assert body["has_backup"] is False
    money_cols = {c["key"] for c in body["columns"] if c["type"] == "money"}
    assert "투자비" in money_cols
    status_cols = {c["key"] for c in body["columns"] if c["type"] == "status"}
    assert "PJT" in status_cols
    text_cols = {c["key"] for c in body["columns"] if c["type"] == "text"}
    assert "담당자" in text_cols


def test_delete_row_success_and_row_gone():
    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        add = client.post("/api/v1/admin/rows", json={"fields": {"WBS_Code": "예정"}}, headers=headers)
        new_no = add.json()["row"]["NO"]

        r = client.delete(f"/api/v1/admin/rows/{new_no}", headers=headers)
        assert r.status_code == 200

        raw = client.get("/api/v1/admin/raw-data", headers=headers).json()

    assert not any(row["NO"] == new_no for row in raw["rows"])


def test_delete_row_not_found():
    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        r = client.delete("/api/v1/admin/rows/999999", headers=headers)

    assert r.status_code == 404


def test_restore_backup_undoes_last_edit():
    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        client.patch("/api/v1/admin/rows/1", json={"fields": {"PJT": "변경됨"}}, headers=headers)

        raw = client.get("/api/v1/admin/raw-data", headers=headers).json()
        assert raw["has_backup"] is True

        r = client.post("/api/v1/admin/rows/restore", headers=headers)
        assert r.status_code == 200

        raw_after = client.get("/api/v1/admin/raw-data", headers=headers).json()

    assert raw_after["has_backup"] is False
    row1 = next(row for row in raw_after["rows"] if row["NO"] == "1")
    assert row1["PJT"] != "변경됨"


def test_edit_money_field_rejects_non_numeric():
    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        r = client.patch("/api/v1/admin/rows/1", json={"fields": {"투자비": "약 4.8억"}}, headers=headers)

    assert r.status_code == 400


def test_edit_money_field_accepts_pure_digits():
    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        r = client.patch("/api/v1/admin/rows/1", json={"fields": {"투자비": "123456789"}}, headers=headers)

    assert r.status_code == 200
    assert r.json()["row"]["투자비"] == "123456789"


def test_edit_money_field_accepts_comma_and_won_suffix():
    # clean_money_series가 원/쉼표/공백을 허용하는 것과 동일한 관용 범위를 검증에도 적용한다.
    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        r = client.patch("/api/v1/admin/rows/1", json={"fields": {"투자비": "480,000,000원"}}, headers=headers)

    assert r.status_code == 200


def test_edit_progress_month_amount_count_mismatch_blocked():
    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        r = client.patch(
            "/api/v1/admin/rows/1",
            json={"fields": {"기성_월": "1월/2월/3월", "기성_금액": "100/200"}},
            headers=headers,
        )

    assert r.status_code == 400


def test_edit_progress_month_amount_matching_count_succeeds():
    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        r = client.patch(
            "/api/v1/admin/rows/1",
            json={"fields": {"기성_월": "1월/2월/3월", "기성_금액": "100/200/300"}},
            headers=headers,
        )

    assert r.status_code == 200


def test_edit_unrelated_field_not_blocked_by_preexisting_mismatch():
    # NO=1 행에 기성_월/기성_금액이 이미 개수가 안 맞는 상태를 API 밖에서 직접 만들어둔다
    # (기능 도입 이전부터 있던 레거시 불일치를 흉내). 이런 행이라도 그 두 필드를
    # 건드리지 않는 다른 필드 수정은 막히면 안 된다(영구 잠김 방지 안전장치).
    base_df = read_dat(BASE_FILE)
    base_df.loc[base_df["NO"] == "1", "기성_월"] = "1월/2월"
    base_df.loc[base_df["NO"] == "1", "기성_금액"] = "1000"
    replace_all_from_dataframe(base_df)

    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        r = client.patch("/api/v1/admin/rows/1", json={"fields": {"PJT": "안전장치테스트"}}, headers=headers)

    assert r.status_code == 200
    assert r.json()["row"]["PJT"] == "안전장치테스트"


def test_add_row_money_field_rejects_non_numeric():
    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        r = client.post("/api/v1/admin/rows", json={"fields": {"투자비": "abc"}}, headers=headers)

    assert r.status_code == 400


def test_restore_backup_without_prior_edit_returns_404():
    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        r = client.post("/api/v1/admin/rows/restore", headers=headers)

    assert r.status_code == 404
