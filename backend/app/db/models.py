"""SQLAlchemy Core 테이블 정의.

ORM 클래스 대신 Core Table을 쓰는 이유: 이 앱은 처음부터 끝까지 pandas
DataFrame(한글 헤더)을 주고받는 구조라(app/data/store.py, app/calc/*),
행을 객체로 매핑하는 ORM보다 select()/insert() 결과를 바로 DataFrame으로
바꾸기 쉬운 Core 스타일이 더 잘 맞는다.

investment_rows의 컬럼 목록은 app/data/columns.py의 COL 딕셔너리에서
그대로 가져온다 — COL이 유일한 정답(single source of truth)이고, 여기서
39개 필드를 다시 하드코딩하면 두 곳이 어긋날 위험이 생긴다.
"""
from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Integer, MetaData, Table, Text

from app.data.columns import COL

metadata = MetaData()

investment_rows = Table(
    "investment_rows",
    metadata,
    Column("no", Integer, primary_key=True, autoincrement=False),
    *[
        Column(key, Text, nullable=False, server_default="")
        for key in COL
        if key != "no"
    ],
)

custom_column_defs = Table(
    "custom_column_defs",
    metadata,
    Column("key", Text, primary_key=True),
    Column("col_type", Text, nullable=False),
)

custom_column_values = Table(
    "custom_column_values",
    metadata,
    Column("row_no", Integer, ForeignKey("investment_rows.no", ondelete="CASCADE"), primary_key=True),
    Column("column_key", Text, ForeignKey("custom_column_defs.key", ondelete="CASCADE"), primary_key=True),
    Column("value", Text, nullable=False, server_default=""),
)

# 단일 슬롯 백업(id=1 고정) — 편집 직전 전체 상태를 JSON으로 통째로 저장해
# "바로 이전 상태 1개"만 되돌릴 수 있게 한다(기존 REV_BACKUP_FILE과 동일한 의미).
backup_snapshot = Table(
    "backup_snapshot",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=False),
    Column("data_json", Text, nullable=False),
    Column("custom_types_json", Text, nullable=False),
    Column("created_at", Text, nullable=False),
)
