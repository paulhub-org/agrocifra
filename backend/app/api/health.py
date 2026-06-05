"""Служебные эндпоинты: проверка работоспособности и версия."""
from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["service"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/version")
def version() -> dict:
    return {"app": settings.app_name, "version": "0.1.0"}
