"""Сборка маршрутов API АИС «АгроЦифра»."""
from fastapi import APIRouter

from app.api import auth, calculations, data, health, optimization, reports

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(calculations.router)
api_router.include_router(data.router)
api_router.include_router(reports.router)
api_router.include_router(optimization.router)
