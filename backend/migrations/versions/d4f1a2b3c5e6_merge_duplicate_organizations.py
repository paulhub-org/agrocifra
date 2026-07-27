"""merge duplicate organizations (V3.0, задачи 4/5)

Слияние дубликатов организаций: ссылки переносятся на каноническую запись
(наименьший id), дубликаты удаляются. Идемпотентно — повторный прогон ничего не меняет.

Revision ID: d4f1a2b3c5e6
Revises: c3d7e9a1b2f4
Create Date: 2026-06-12
"""
from alembic import op
from sqlalchemy.orm import Session

revision = "d4f1a2b3c5e6"
down_revision = "c3d7e9a1b2f4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.services.org_dedup import merge_duplicate_organizations

    session = Session(bind=op.get_bind())
    report = merge_duplicate_organizations(session)
    session.commit()
    for line in report:
        print("[org-merge]", line)


def downgrade() -> None:
    # Слияние данных необратимо — откат не выполняется.
    pass
