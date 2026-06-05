"""Эндпоинты расчётного ядра (демонстрационные обёртки сервисов).

Привязка к данным организаций, ролевой доступ и пакетные расчёты — Спринты 2–4.
"""
from fastapi import APIRouter

from app.schemas.calculations import (
    DscrRequest,
    DscrResponse,
    HurwiczRequest,
    HurwiczResponse,
    IntegralRequest,
    IntegralResponse,
)
from app.services import calculations as calc

router = APIRouter(prefix="/calc", tags=["calculations"])


@router.post("/hurwicz", response_model=HurwiczResponse)
def hurwicz(req: HurwiczRequest) -> HurwiczResponse:
    return HurwiczResponse(
        value=calc.hurwicz_value(req.payoffs, req.optimism),
        zone=calc.hurwicz_zone(req.optimism),
    )


@router.post("/integral", response_model=IntegralResponse)
def integral(req: IntegralRequest) -> IntegralResponse:
    return IntegralResponse(
        integral=calc.integral_efficiency(req.economic, req.ecological, req.social)
    )


@router.post("/dscr", response_model=DscrResponse)
def dscr(req: DscrRequest) -> DscrResponse:
    value = calc.dscr(req.cfads, req.principal, req.interest)
    return DscrResponse(dscr=value, meets_target=value >= calc.DSCR_MIN)
