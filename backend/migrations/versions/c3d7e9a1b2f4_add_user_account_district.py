"""add user_account.district (V2.0, задача 1 — роль «районный оператор»)

Revision ID: c3d7e9a1b2f4
Revises: b1f4c2d8e7a9
Create Date: 2026-06-06
"""
from alembic import op
import sqlalchemy as sa

revision = "c3d7e9a1b2f4"
down_revision = "b1f4c2d8e7a9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_account", sa.Column("district", sa.String(length=120), nullable=True))


def downgrade() -> None:
    op.drop_column("user_account", "district")
