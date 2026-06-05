"""Схемы запросов/ответов расчётного ядра (Pydantic)."""
from pydantic import BaseModel, Field


class HurwiczRequest(BaseModel):
    payoffs: list[float] = Field(..., min_length=1, description="Исходы по состояниям среды")
    optimism: float = Field(..., ge=0.0, le=1.0, description="Коэффициент оптимизма a ∈ [0;1]")


class HurwiczResponse(BaseModel):
    value: float
    zone: str


class IntegralRequest(BaseModel):
    economic: float
    ecological: float
    social: float


class IntegralResponse(BaseModel):
    integral: float


class DscrRequest(BaseModel):
    cfads: float
    principal: float
    interest: float


class DscrResponse(BaseModel):
    dscr: float
    meets_target: bool
