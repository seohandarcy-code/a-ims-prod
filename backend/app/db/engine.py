"""DB 엔진 생성.

동기(sync) SQLAlchemy Engine 하나만 둔다 — 이 백엔드는 원래도 완전 동기
구조이고(app/data/store.py의 threading.Lock 기반 직렬화), 트래픽 규모가
작고 Replica=1을 전제하므로 비동기 드라이버(aiosqlite/asyncpg)를 들여올
이유가 없다. DATABASE_URL만 바꾸면(1단계 sqlite:// → 2단계 postgresql+psycopg://)
나머지 코드는 그대로 재사용된다.
"""
from __future__ import annotations

from sqlalchemy import create_engine, event

from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL, future=True)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:  # noqa: ANN001
    if engine.dialect.name != "sqlite":
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
