import os
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")  # noqa: E402

import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402


@pytest.fixture
def db():
    from app.db.session import Base
    import app.models.models  # noqa: F401  (register tables)
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool, future=True
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, future=True)
    s = Session()
    try:
        yield s
    finally:
        s.close()
        engine.dispose()


# Фактические данные «Шипяны-АСК» в формате ответов формы эффективности
# (резолвинг по ТЕКСТУ поля; «урожайность ПОСЛЕ» = валовый сбор ÷ площадь).
@pytest.fixture
def efficiency_answers():
    pairs = [
        ("Сумма затрат организации на производство продукции растительного происхождения ДО цифровизации, рублей", "6150100"),
        ("1.2.1 Площадь обрабатываемых земель ДО цифровизации, га", "4500"),
        ("Затраты организации на 1 га обрабатываемых земель, рублей/га", "1313.58"),
        ("Средняя урожайность культур в организации ДО цифровизации, тонн/га", "0,59"),
        ("1.1.8 Валовый сбор урожая возделываемых культур, тонн", "2700"),
        ("1.1.7 Площадь обрабатываемых земель, га", "4500"),
        ("3.2.2 Прибыль от реализации продукции ПОСЛЕ цифровизации, рублей", "1222000"),
        ("Направлено денежных средств (всего), рублей", "26232000"),
        ("3.2.1 Прибыль от реализации продукции ДО цифровизации, рублей", "1684000"),
        ("Направлено денежных средств (всего) ДО цифровизации, рублей", "21749000"),
        ("2.1 Объем сожженного бензина ДО цифровизации, тонн", "790"),
        ("2.2 Объем сожженного бензина ПОСЛЕ цифровизации, тонн", "687"),
        ("2.3 Объем сожженного топлива дизельного ДО цифровизации, тонн", "1350"),
        ("2.4 Объем сожженного топлива дизельного ПОСЛЕ цифровизации, тонн", "1320"),
        ("Производительность труда ПОСЛЕ цифровизации, рублей/чел.", "191934.21"),
        ("Производительность труда ДО цифровизации, рублей/чел.", "173503.31"),
        ("Направлено денежных средств на уплату налогов и сборов ПОСЛЕ цифровизации, рублей", "504000"),
        ("Направлено денежных средств на уплату налогов и сборов ДО цифровизации, рублей", "359000"),
        ("Наименование сельскохозяйственной организации", "РСДУП «Шипяны-АСК»"),
    ]
    return {str(i): {"answer": val, "text": text} for i, (text, val) in enumerate(pairs, 1)}


# Сабмишен формы зрелости: два агрегата + итоговый уровень (по текстам полей).
@pytest.fixture
def maturity_answers():
    return {
        "1": {"answer": "0,46",
              "text": "Среднее значение показателей потребности во внедрении цифровых технологий"},
        "2": {"answer": "0,28",
              "text": "Среднее значение показателей возможностей во внедрении цифровых технологий"},
        "3": {"answer": "0,36",
              "text": "Уровень цифровой зрелости Вашей организации"},
        "4": {"answer": "РСДУП «Шипяны-АСК»",
              "text": "Наименование сельскохозяйственной организации"},
    }


@pytest.fixture
def client():
    """FastAPI TestClient с БД на SQLite и засеянными демо-пользователями."""
    from fastapi.testclient import TestClient
    from sqlalchemy.pool import StaticPool

    from app.db.session import Base, get_db
    import app.models.models  # noqa: F401
    from app.db.seed import seed
    from app.main import app

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool, future=True
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, future=True)()
    seed(session)

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()
