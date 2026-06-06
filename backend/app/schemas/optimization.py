"""Схемы запроса/ответа модуля оптимизации затрат на цифровизацию."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ProjectIn(BaseModel):
    name: str
    cost: float = Field(gt=0, description="Требуемые инвестиции (capex), руб.")
    effect: float = Field(ge=0, description="Ожидаемый эффект при полном финансировании, руб.")
    var_type: str = Field(default="continuous", pattern="^(binary|continuous)$")
    score: float = Field(default=0.0, description="КЭц или уровень цифровой зрелости")
    maturity: float = Field(default=0.0, description="Уровень цифровой зрелости (для таблицы)")
    min_share: float = Field(default=0.5, ge=0, le=1)
    credit_limit: float | None = Field(
        default=None, description="Предел финансирования по кредитоспособности, руб."
    )
    key: str | None = None


class OptimizationRequest(BaseModel):
    budget: float = Field(gt=0, description="Общий бюджет цифровизации, руб.")
    coverage_weight: float = Field(
        default=0.0, ge=0,
        description="Вес охвата организаций с оценкой не ниже порога (вторичная цель)",
    )
    threshold: float = Field(default=1.0, description="Порог эффективности/зрелости")
    score_metric: str = Field(default="efficiency", pattern="^(efficiency|maturity)$")
    projects: list[ProjectIn] | None = Field(
        default=None, description="Явные проекты-кандидаты; при отсутствии берутся из БД"
    )


class MineOptimizationRequest(BaseModel):
    """Оптимальный уровень затрат для своей организации (роль «Организация»)."""
    budget: float | None = Field(
        default=None, gt=0,
        description="Бюджет, руб.; по умолчанию — полная стоимость проекта (CAPEX)",
    )
    threshold: float = Field(default=1.0, description="Порог эффективности/зрелости")
