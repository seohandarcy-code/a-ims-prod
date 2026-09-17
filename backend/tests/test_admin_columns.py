"""관리자 커스텀 컬럼 추가/삭제 API 테스트."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.data.store import DataStore
from app.main import app


def _login(client: TestClient) -> str:
    r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "0000"})
    return r.json()["token"]


def _find_column(columns: list[dict], key: str) -> dict:
    return next(c for c in columns if c["key"] == key)


def test_add_text_column_appears_in_raw_data():
    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        r = client.post("/api/v1/admin/columns", json={"name": "비고", "type": "text"}, headers=headers)
        assert r.status_code == 201

        raw = client.get("/api/v1/admin/raw-data", headers=headers).json()

    col = _find_column(raw["columns"], "비고")
    assert col["type"] == "text"
    assert col["deletable"] is True
    assert all(row["비고"] == "" for row in raw["rows"])


def test_add_money_column_has_money_type_and_validation():
    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        client.post("/api/v1/admin/columns", json={"name": "추가예산", "type": "money"}, headers=headers)
        raw = client.get("/api/v1/admin/raw-data", headers=headers).json()
        col = _find_column(raw["columns"], "추가예산")
        assert col["type"] == "money"

        bad = client.patch("/api/v1/admin/rows/1", json={"fields": {"추가예산": "만원"}}, headers=headers)
        assert bad.status_code == 400

        good = client.patch("/api/v1/admin/rows/1", json={"fields": {"추가예산": "5000000"}}, headers=headers)
        assert good.status_code == 200
        assert good.json()["row"]["추가예산"] == "5000000"


def test_add_date_column_has_date_type():
    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        client.post("/api/v1/admin/columns", json={"name": "검토일", "type": "date"}, headers=headers)
        raw = client.get("/api/v1/admin/raw-data", headers=headers).json()

    col = _find_column(raw["columns"], "검토일")
    assert col["type"] == "date"
    assert col["placeholder"]


def test_add_column_rejects_duplicate_name():
    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        r = client.post("/api/v1/admin/columns", json={"name": "PJT"}, headers=headers)

    assert r.status_code == 400


def test_add_column_rejects_reserved_name():
    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        r = client.post("/api/v1/admin/columns", json={"name": "집행률"}, headers=headers)

    assert r.status_code == 400


def test_add_column_rejects_forbidden_char():
    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        r = client.post("/api/v1/admin/columns", json={"name": "a/b"}, headers=headers)

    assert r.status_code == 400


def test_add_column_rejects_empty_name():
    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        r = client.post("/api/v1/admin/columns", json={"name": "   "}, headers=headers)

    assert r.status_code == 400


def test_delete_custom_column_removes_it():
    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        client.post("/api/v1/admin/columns", json={"name": "임시컬럼"}, headers=headers)
        r = client.delete("/api/v1/admin/columns/임시컬럼", headers=headers)
        assert r.status_code == 200

        raw = client.get("/api/v1/admin/raw-data", headers=headers).json()

    assert not any(c["key"] == "임시컬럼" for c in raw["columns"])


def test_delete_fixed_column_rejected():
    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        r = client.delete("/api/v1/admin/columns/PJT", headers=headers)

    assert r.status_code == 400


def test_delete_nonexistent_column_returns_404():
    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        r = client.delete("/api/v1/admin/columns/없는컬럼", headers=headers)

    assert r.status_code == 404


def test_new_row_can_fill_custom_column_value():
    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        client.post("/api/v1/admin/columns", json={"name": "메모"}, headers=headers)
        r = client.post(
            "/api/v1/admin/rows",
            json={"fields": {"WBS_Code": "예정", "메모": "신규 행 메모"}},
            headers=headers,
        )

    assert r.status_code == 201
    assert r.json()["row"]["메모"] == "신규 행 메모"


def test_custom_column_and_type_persist_after_restart():
    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}
        client.post("/api/v1/admin/columns", json={"name": "잔여예산", "type": "money"}, headers=headers)

    fresh_store = DataStore()
    fresh_store.load()

    assert "잔여예산" in fresh_store.get_raw_df().columns
    assert fresh_store.get_column_types().get("잔여예산") == "money"


def test_restore_backup_undoes_column_add():
    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        client.post("/api/v1/admin/columns", json={"name": "취소될컬럼", "type": "money"}, headers=headers)
        r = client.post("/api/v1/admin/rows/restore", headers=headers)
        assert r.status_code == 200

        raw = client.get("/api/v1/admin/raw-data", headers=headers).json()

    assert not any(c["key"] == "취소될컬럼" for c in raw["columns"])
