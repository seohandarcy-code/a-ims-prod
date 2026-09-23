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

from sqlalchemy import Boolean, Column, ForeignKey, Integer, MetaData, Table, Text

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

# SSO 로그인 접근 제어 목록 — sso_id(SSO_USER_ID_CLAIM 클레임 값)가 여기 등록돼
# 있어야 로그인(세션 발급)이 허용된다(app/api/auth.py의 /sso/callback 참고).
# 투자 데이터를 사람별로 다르게 보여주는 행 단위 권한이 아니라, 누가 볼 수 있는지/
# 누가 admin인지만 관리하는 접근 제어 테이블이다.
allowed_users = Table(
    "allowed_users",
    metadata,
    Column("sso_id", Text, primary_key=True),
    Column("name", Text, nullable=False),
    Column("team", Text, nullable=False, server_default=""),
    Column("is_admin", Boolean, nullable=False, server_default="0"),
    Column("created_at", Text, nullable=False),
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
