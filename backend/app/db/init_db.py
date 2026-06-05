"""Создание таблиц для локальной разработки (Base.metadata.create_all).

В продакшене и CI схема управляется миграциями Alembic (Спринт 3).
Запуск: python -m app.db.init_db
"""
from app.db.session import Base, engine
import app.models.models  # noqa: F401  (регистрация всех таблиц в метаданных)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print("Схема БД создана (dev).")
