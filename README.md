# АгроЦифра

Автоматизированная информационная система оценки эффективности и оптимизации
цифровизации сельскохозяйственных организаций (растениеводство, Республика Беларусь).

Прикладной результат диссертационного исследования (специальность 08.00.05).
Архитектура и требования — см. `docs/ТЗ.pdf` (Спринт 1).

## Технологический стек
- **Backend:** FastAPI (Python 3.11+), SQLAlchemy, Pydantic, NumPy/SciPy, PuLP + CBC (оптимизация)
- **Frontend:** React (Vite)
- **БД:** PostgreSQL 15+
- **Интеграция:** Jotform REST API
- **Аутентификация:** JWT (OAuth2)
- **Развёртывание:** Docker / docker-compose; облако (Railway / Render / DigitalOcean)

## Структура репозитория
```
backend/   — сервер приложений и расчётное ядро
frontend/  — клиентское веб-приложение (React)
docs/      — ТЗ.pdf, Архитектура.png, Схема_БД.png (Спринт 1)
.github/   — непрерывная интеграция (GitHub Actions)
```

## Быстрый старт (разработка)
```bash
docker compose up --build          # поднимет postgres + backend + frontend
# backend:  http://localhost:8000/docs   (Swagger UI)
# frontend: http://localhost:5173
```

Backend без Docker:
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env               # при необходимости отредактировать
python -m app.db.init_db           # создать таблицы (dev); миграции — Спринт 3
uvicorn app.main:app --reload      # http://localhost:8000/docs
pytest -q                          # запуск тестов расчётного ядра
```

## Дорожная карта (спринты)
| Спринт | Содержание |
|---|---|
| 1 | ТЗ, архитектура, схема БД, пилотное подключение Jotform, репозиторий + CI |
| 2 | Расчётное ядро: метод Гурвица (пороги 0,134 / 0,366), 12 показателей, интегральный коэффициент |
| 3 | Слой данных, миграции, ETL-интеграция Jotform |
| 4 | Интерфейс и ролевая модель (организация / региональный оператор / госорган) |
| 5 | Отчёты, визуализация, экспорт (Word/Excel/PDF) |
| 6 | Развёртывание, тестирование, CI/CD |
| 7 | Финализация, регистрация в НЦИС |

## Развёртывание и тестирование (Спринт 6)
Развёртывание на одном сервере через Docker Compose, CI (GitHub Actions), нагрузочное
тестирование (Locust), резервное копирование и сквозные тесты описаны в
[docs/Развертывание.md](docs/Развертывание.md). Кратко: `cp .env.example .env` → задать
секреты → `docker compose up -d --build` → проверка `curl http://localhost/api/health`.
