"""app/config.py의 DATABASE_URL 조립 우선순위(DATABASE_URL > DB_HOST 조합 > SQLite 폴백)를 검증한다."""
from __future__ import annotations

from app.config import _build_database_url


def _clear_db_env(monkeypatch) -> None:
    for key in ("DATABASE_URL", "DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"):
        monkeypatch.delenv(key, raising=False)


def test_database_url_env_takes_priority(monkeypatch):
    _clear_db_env(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://explicit-dsn")
    monkeypatch.setenv("DB_HOST", "should-be-ignored")

    assert _build_database_url() == "postgresql+psycopg://explicit-dsn"


def test_decomposed_vars_assemble_dsn_when_no_database_url(monkeypatch):
    _clear_db_env(monkeypatch)
    monkeypatch.setenv("DB_HOST", "db.internal")
    monkeypatch.setenv("DB_PORT", "6543")
    monkeypatch.setenv("DB_NAME", "ims_prod")
    monkeypatch.setenv("DB_USER", "svc_ims")
    monkeypatch.setenv("DB_PASSWORD", "s3cr3t")

    assert _build_database_url() == "postgresql+psycopg://svc_ims:s3cr3t@db.internal:6543/ims_prod"


def test_decomposed_vars_url_encode_special_characters(monkeypatch):
    _clear_db_env(monkeypatch)
    monkeypatch.setenv("DB_HOST", "db.internal")
    monkeypatch.setenv("DB_USER", "svc/ims")
    monkeypatch.setenv("DB_PASSWORD", "p@ss w:rd/!")

    url = _build_database_url()
    assert url == "postgresql+psycopg://svc%2Fims:p%40ss+w%3Ard%2F%21@db.internal:5432/ims"


def test_decomposed_vars_use_defaults_for_missing_port_and_name(monkeypatch):
    _clear_db_env(monkeypatch)
    monkeypatch.setenv("DB_HOST", "db.internal")

    assert _build_database_url() == "postgresql+psycopg://:@db.internal:5432/ims"


def test_falls_back_to_sqlite_when_nothing_set(monkeypatch):
    _clear_db_env(monkeypatch)

    assert _build_database_url().startswith("sqlite:///")
