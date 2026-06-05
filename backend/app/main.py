"""Точка входа приложения АИС «АгроЦифра» (FastAPI).

Поднимает API-шлюз с разграничением по ролям (admin / organization / ministry),
подключает расчётное ядро (метод Гурвица, интегральный коэффициент, DSCR/ICR)
и финансово-экономический модуль оптимизации (MILP). См. ТЗ, раздел 4.

Полная реализация эндпоинтов и ролевой модели — Спринты 2–4.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "АИС оценки эффективности и оптимизации цифровизации "
        "сельскохозяйственных организаций (растениеводство, Республика Беларусь)."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # в продакшене ограничить доменом клиента
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/", tags=["service"])
def root() -> dict:
    return {"name": settings.app_name, "docs": "/docs", "health": "/health"}
