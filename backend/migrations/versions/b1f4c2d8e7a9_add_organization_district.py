"""add organization.district (Спринт 8, задача 9)

Revision ID: b1f4c2d8e7a9
Revises: a036cc892a7e
Create Date: 2026-06-05
"""
from alembic import op
import sqlalchemy as sa

revision = "b1f4c2d8e7a9"
down_revision = "a036cc892a7e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("organization", sa.Column("district", sa.String(length=120), nullable=True))


def downgrade() -> None:
    op.drop_column("organization", "district")
