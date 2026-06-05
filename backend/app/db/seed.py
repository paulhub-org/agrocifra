"""Демонстрационные пользователи и справочники для UAT (Спринт 4).

Запуск: python -m app.db.seed   (после `alembic upgrade head`).
Пароли демонстрационные — сменить перед реальной эксплуатацией.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.models import Region, Role, UserAccount

DEMO_USERS = [
    ("org", "org123", Role.organization, "Оператор организации"),
    ("region", "region123", Role.regional_operator, "Региональный оператор"),
    ("office", "office123", Role.digitalization_office, "Офис цифровизации"),
    ("gov", "gov123", Role.state_authority, "Государственный орган"),
]
DEMO_REGIONS = ["Брестская", "Витебская", "Гомельская", "Гродненская", "Минская", "Могилёвская"]


def seed(db: Session) -> None:
    for name in DEMO_REGIONS:
        if not db.execute(select(Region).where(Region.name == name)).scalar_one_or_none():
            db.add(Region(name=name))
    for login, pw, role, full_name in DEMO_USERS:
        if not db.execute(select(UserAccount).where(UserAccount.login == login)).scalar_one_or_none():
            db.add(UserAccount(login=login, password_hash=hash_password(pw),
                               role=role.value, full_name=full_name, is_active=True))
    db.commit()


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed(db)
        print("Демо-данные созданы. Пользователи: org / region / office / gov (пароли *123).")
    finally:
        db.close()
