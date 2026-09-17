"""initial schema: investment_rows, custom_column_defs, custom_column_values, backup_snapshot

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-16
"""
from __future__ import annotations

from alembic import op

# investment_rows의 39개 컬럼은 app/data/columns.py의 COL 딕셔너리가 유일한
# 정답이다. 여기서 다시 하드코딩해 두 곳이 어긋날 위험을 만드는 대신, 최초
# 스키마 생성(이 뒤에 선행 리비전이 없는 첫 마이그레이션)에 한해 현재
# app/db/models.py의 metadata를 그대로 적용한다. 이후 스키마 변경은 이 파일을
# 고치지 말고 새 리비전에서 op.add_column 등으로 일반적인 방식으로 추가한다.
from app.db.models import metadata  # noqa: E402

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    metadata.drop_all(bind=bind)
