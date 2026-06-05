"""Расчётное ядро АИС «АгроЦифра».

Реализует:
  * критерий (метод) Гурвица с пороговыми значениями 0,134 и 0,366
    [Кандидатская_T3, п. 2.2.2];
  * интегральный коэффициент эффективности цифровизации на основе
    равнозначности экономической, экологической и социальной компонент
    [Автореферат, гл. 2];
  * индикаторы проектного финансирования DSCR и ICR
    [Yescombe, 2014; Постановление Министерства экономики № 158];
  * коэффициенты финансовой устойчивости (нормативы по ОКЭД)
    [Постановление Совета Министров № 1672 / № 574].

Полная реализация и верификация на пилотных данных — Спринт 2.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

# Пороговые значения коэффициента оптимизма (метод Гурвица)
HURWICZ_LOW = 0.134
HURWICZ_HIGH = 0.366

# Целевые/нормативные значения (см. ТЗ, Приложение Д)
DSCR_TARGET = 1.5
DSCR_MIN = 1.3
ICR_MIN = 2.0


def hurwicz_value(payoffs: list[float], optimism: float) -> float:
    """Свёртка Гурвица: H = a*max + (1-a)*min, a — коэффициент оптимизма [0;1]."""
    if not payoffs:
        raise ValueError("payoffs must be non-empty")
    if not 0.0 <= optimism <= 1.0:
        raise ValueError("optimism must be in [0, 1]")
    return optimism * max(payoffs) + (1.0 - optimism) * min(payoffs)


def hurwicz_zone(optimism: float) -> str:
    """Зона управленческого решения по порогам 0,134 / 0,366."""
    if optimism < HURWICZ_LOW:
        return "conservative"   # осторожная (пессимистическая) стратегия
    if optimism <= HURWICZ_HIGH:
        return "balanced"       # сбалансированная стратегия
    return "optimistic"         # оптимистическая стратегия


def digital_maturity_zone(value: float) -> str:
    """Зона цифровой зрелости по итоговому показателю Гурвица [Кандидатская_T3, п. 2.2.2].

    Границы интервалов 0,134 и 0,366: < 0,134 — низкая; [0,134; 0,366] — средняя;
    > 0,366 — высокая цифровая зрелость (среднее по 7 пилотным организациям ≈ 0,35).
    """
    if value < HURWICZ_LOW:
        return "низкая"
    if value <= HURWICZ_HIGH:
        return "средняя"
    return "высокая"


def digital_maturity(
    need_scores: list[float],
    capability_scores: list[float],
) -> dict[str, float | str]:
    """Итоговый показатель цифровой зрелости [Кандидатская_T3, п. 2.2.2].

    Раздельно усредняются оценки потребности (need) и возможностей (capability)
    цифровизации (нормированные значения); итоговый уровень — ГЕОМЕТРИЧЕСКОЕ
    СРЕДНЕЕ двух агрегатов: КЗ = sqrt(потребность · возможности). Соответствие
    подтверждено на 7 пилотных организациях (выгрузка формы «Цифровая зрелость»:
    напр., sqrt(0,21 · 1,01) = 0,46). Классификация по порогам 0,134 / 0,366.
    """
    if not need_scores or not capability_scores:
        raise ValueError("need_scores and capability_scores must be non-empty")
    need_agg = sum(need_scores) / len(need_scores)
    capability_agg = sum(capability_scores) / len(capability_scores)
    value = math.sqrt(max(need_agg, 0.0) * max(capability_agg, 0.0))
    return {
        "need": need_agg,
        "capability": capability_agg,
        "maturity": value,
        "zone": digital_maturity_zone(value),
    }


def integral_efficiency(
    economic: float,
    ecological: float,
    social: float,
    weights: tuple[float, float, float] = (1 / 3, 1 / 3, 1 / 3),
) -> float:
    """Интегральный коэффициент эффективности K_инт = a*E_эк + b*E_экол + g*E_соц.

    По умолчанию веса равнозначны (a=b=g=1/3) [Автореферат, положения, выносимые на защиту].
    """
    a, b, g = weights
    if abs((a + b + g) - 1.0) > 1e-9:
        raise ValueError("weights must sum to 1")
    return a * economic + b * ecological + g * social


def dscr(cfads: float, principal: float, interest: float) -> float:
    """Коэффициент покрытия обслуживания долга: CFADS / (P + I)."""
    denom = principal + interest
    if denom <= 0:
        raise ValueError("debt service must be positive")
    return cfads / denom


def icr(ebit: float, interest: float) -> float:
    """Коэффициент покрытия процентов: EBIT / I."""
    if interest <= 0:
        raise ValueError("interest must be positive")
    return ebit / interest


@dataclass
class StabilityRatios:
    """Коэффициенты финансовой устойчивости (нормативы растениеводства РБ)."""
    current_liquidity: float    # К1 ≥ 1,5
    own_working_capital: float  # К2 (Косос) ≥ 0,2
    liabilities_to_assets: float  # К3 (Кооа) ≤ 0,85
    autonomy: float             # ≈ 0,5

    def meets_norms(self) -> bool:
        return (
            self.current_liquidity >= 1.5
            and self.own_working_capital >= 0.2
            and self.liabilities_to_assets <= 0.85
        )
