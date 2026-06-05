"""Модуль оценки эффективности цифровизации растениеводства (расчётное ядро).

Реализует методику §2.3 [Кандидатская_T3] по трём составляющим — экономической,
экологической и социальной — и сводный коэффициент эффективности КЭц (порог 1,0).

Формулы (1)–(8) — экономическая цепочка; (10) — экологический эффект; (11) —
трудовой эффект; (12) — налоговый эффект; (13) — сводный коэффициент. Точные
символьные формы (10)–(13) внесены по файлу Formulas_10-13:

  (10) ЭкЭц = 8·ПП + 260·∆Б + 259·∆ДТ + Σ(∆УДᵢ·ЦУДᵢ)
  (11) ПТц = В₁/ЧР₁ − В₀/ЧР₀
  (12) НЭц = 0,18·∆Пр + 0,1·∆ДС + 0,13·∆ФОТ + 0,01·∆ОС
  (13) КЭц = (0,1·∆По + ЭкЭц + (ПТц + НЭц)) / Зц

СТАТУС ВЕРИФИКАЦИИ (данные 6 пилотных организаций, лист «Эффективность»):
  * (1)–(8) экономическая цепочка — СОВПАДАЕТ покопеечно (6 организаций);
  * (11) ПТц — СОВПАДАЕТ (напр., Доброволец 4 888,89 = строка 45);
  * (12) НЭц — СОВПАДАЕТ (напр., Доброволец 256 039,56 = строка 54);
  * цифровая зрелость (Гурвиц, 0,134/0,366) — СОВПАДАЕТ (7 организаций, среднее 0,42).

ВАЖНО: ДВЕ РАЗНЫЕ ФОРМУЛЫ КЭц.
  * Текстовая формула (13) `КЭц=(0,1·∆По+ЭкЭц+(ПТц+НЭц))/Зц` реализована функцией
    `integral_coefficient` ниже. Она НЕ воспроизводит значения КЭ из таблиц
    диссертации (строка 55): даже социальный блок (ПТц+НЭц)/Зц для «Доброволец»
    = 2,12 > 1,12.
  * Реальные значения КЭ в таблицах сформированы ВИДЖЕТОМ «Калькуляции формы»
    (Jotform) по ИНДЕКСНОЙ формуле — произведение средних по отношениям
    «после/до» (см. функцию `efficiency_index` и её документацию ниже).
    Проверено покопеечно на 4 организациях; среднее по 6 ≈ 0,99.
  Рекомендация для диссертации: привести текст (13) и формулу виджета к единому
  виду перед защитой. Обе формулы оставлены в коде для прозрачности.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# ─────────────────────────── калибровочные константы ───────────────────────────
IMPROVEMENT_RATE: float = 0.10                 # средний процент сокращения затрат/роста урожайности [65]
PESTICIDE_DAMAGE_RUB_PER_HA: float = 8.0       # предотвращённый ущерб, руб./га (середина 6–9) [66], формула (10)
CO2_DAMAGE_RUB_PER_T_PETROL: float = 260.0     # ущерб от CO₂, руб./т бензина, формула (10)
CO2_DAMAGE_RUB_PER_T_DIESEL: float = 259.0     # ущерб от CO₂, руб./т дизельного топлива, формула (10)
TAX_RATE_PROFIT: float = 0.18                  # налог на прибыль, формула (12)
TAX_RATE_VAT: float = 0.10                     # НДС (коэффициент), формула (12)
TAX_RATE_INCOME: float = 0.13                  # подоходный налог (ФОТ), формула (12)
TAX_RATE_PROPERTY: float = 0.01                # налог на имущество (ОС), формула (12)
OPERATING_PROFIT_WEIGHT: float = 0.10          # 0,1·∆По в формуле (13)
EFFICIENCY_THRESHOLD: float = 1.0              # лингвистический порог КЭц


# ─────────────────────────── входные данные ───────────────────────────
@dataclass
class CostFactors:
    """Затраты-факторы себестоимости [формула (1)], руб. за период."""
    planting_material: float
    fertilizers: float
    plant_protection: float
    machinery_cost: float
    labor_and_social: float = 0.0
    additional: float = 0.0

    def total(self) -> float:
        return (self.planting_material + self.fertilizers + self.plant_protection
                + self.machinery_cost + self.labor_and_social + self.additional)


@dataclass
class EconomicInputs:
    costs_before: CostFactors
    costs_after: CostFactors
    area_ha: float
    gross_yield_before_t: float
    gross_yield_after_t: float
    crop_price_rub_per_t: float


@dataclass
class FertilizerChange:
    """Изменение по i-му удобрению [формула (10)]: ∆УДᵢ (тонн) и цена ЦУДᵢ (руб./т)."""
    change_t: float          # ∆УДᵢ = объём до − объём после, тонн (сокращение → положительное)
    price_rub_per_t: float   # ЦУДᵢ


@dataclass
class EcologicalInputs:
    """Данные экологического эффекта [формула (10)]. ∆ = (до − после)."""
    area_ha: float                       # ПП
    petrol_before_t: float = 0.0         # бензин до
    petrol_after_t: float = 0.0          # бензин после
    diesel_before_t: float = 0.0         # дизель до
    diesel_after_t: float = 0.0          # дизель после
    fertilizers: list[FertilizerChange] = field(default_factory=list)


@dataclass
class SocialInputs:
    """Данные социального эффекта [формулы (11), (12)]."""
    # (11) производительность труда
    revenue_before_rub: float
    revenue_after_rub: float
    headcount_before: int
    headcount_after: int
    # (12) налоговый эффект — значения «до» и «после»
    taxable_profit_before: float = 0.0
    taxable_profit_after: float = 0.0
    value_added_before: float = 0.0
    value_added_after: float = 0.0
    payroll_before: float = 0.0
    payroll_after: float = 0.0
    fixed_assets_before: float = 0.0
    fixed_assets_after: float = 0.0


@dataclass
class DigitalizationCosts:
    """Совокупные затраты на цифровизацию (Зц) — строки 11–15 пилотной книги."""
    uav: float = 0.0          # БЛА (комплексы)
    internet: float = 0.0     # подключение к сети
    software: float = 0.0     # ПО
    workstations: float = 0.0 # АРМ (компьютеры)
    other: float = 0.0        # прочие

    def total(self) -> float:
        return self.uav + self.internet + self.software + self.workstations + self.other


@dataclass
class OrganizationData:
    name: str
    economic: EconomicInputs
    ecological: EcologicalInputs
    social: SocialInputs
    digitalization_costs: DigitalizationCosts
    operating_profit_before: float = 0.0   # для ∆По в (13)
    operating_profit_after: float = 0.0


# ─────────────────────────── экономическая цепочка (1)–(8) ───────────────────────────
def production_cost(costs: CostFactors) -> float:
    """(1) полные затраты на производство, руб."""
    return costs.total()


def cost_per_ha(costs: CostFactors, area_ha: float) -> float:
    """(2) удельные затраты, руб./га."""
    if area_ha <= 0:
        raise ValueError("area_ha must be positive")
    return costs.total() / area_ha


def cost_per_tonne(costs: CostFactors, gross_yield_t: float) -> float:
    """(3) удельные затраты, руб./т."""
    if gross_yield_t <= 0:
        raise ValueError("gross_yield_t must be positive")
    return costs.total() / gross_yield_t


def tech_tech_effect(e: EconomicInputs) -> dict[str, float]:
    """(4)–(6) технико-технологический эффект."""
    z_before, z_after = e.costs_before.total(), e.costs_after.total()
    ttae_c = z_before - z_after
    ttae_ga = (cost_per_ha(e.costs_before, e.area_ha)
               - cost_per_ha(e.costs_after, e.area_ha)) * e.area_ha
    ttae_tn = (cost_per_tonne(e.costs_before, e.gross_yield_before_t)
               - cost_per_tonne(e.costs_after, e.gross_yield_after_t)) * e.gross_yield_after_t
    return {"ttae_c": ttae_c, "ttae_ga": ttae_ga, "ttae_tn": ttae_tn}


def biological_effect(e: EconomicInputs) -> float:
    """(7) БЭ = (ВС_после − ВС_до)·Ц, руб."""
    return (e.gross_yield_after_t - e.gross_yield_before_t) * e.crop_price_rub_per_t


def economic_effect(e: EconomicInputs) -> float:
    """(8) суммарный экономический эффект ТТЭ_ц + БЭ, руб."""
    return tech_tech_effect(e)["ttae_c"] + biological_effect(e)


# ─────────────────────────── экологический эффект (10) ───────────────────────────
def ecological_effect(x: EcologicalInputs) -> float:
    """(10) ЭкЭц = 8·ПП + 260·∆Б + 259·∆ДТ + Σ(∆УДᵢ·ЦУДᵢ), руб.  (∆ = до − после)"""
    delta_petrol = x.petrol_before_t - x.petrol_after_t
    delta_diesel = x.diesel_before_t - x.diesel_after_t
    fert = sum(f.change_t * f.price_rub_per_t for f in x.fertilizers)
    return (PESTICIDE_DAMAGE_RUB_PER_HA * x.area_ha
            + CO2_DAMAGE_RUB_PER_T_PETROL * delta_petrol
            + CO2_DAMAGE_RUB_PER_T_DIESEL * delta_diesel
            + fert)


# ─────────────────────────── социальные эффекты (11), (12) ───────────────────────────
def labor_productivity_effect(s: SocialInputs) -> float:
    """(11) ПТц = В₁/ЧР₁ − В₀/ЧР₀, руб./чел."""
    if s.headcount_before <= 0 or s.headcount_after <= 0:
        raise ValueError("headcount must be positive")
    return (s.revenue_after_rub / s.headcount_after
            - s.revenue_before_rub / s.headcount_before)


def tax_effect(s: SocialInputs) -> float:
    """(12) НЭц = 0,18·∆Пр + 0,1·∆ДС + 0,13·∆ФОТ + 0,01·∆ОС, руб.  (∆ = после − до)"""
    return (TAX_RATE_PROFIT * (s.taxable_profit_after - s.taxable_profit_before)
            + TAX_RATE_VAT * (s.value_added_after - s.value_added_before)
            + TAX_RATE_INCOME * (s.payroll_after - s.payroll_before)
            + TAX_RATE_PROPERTY * (s.fixed_assets_after - s.fixed_assets_before))


def social_effect(s: SocialInputs) -> float:
    """Социальный эффект = ПТц + НЭц (как в числителе (13))."""
    return labor_productivity_effect(s) + tax_effect(s)


# ─────────────────────────── сводный коэффициент (13) ───────────────────────────
def efficiency_zone(coefficient: float) -> str:
    """Лингвистическая шкала [п. 2.3.1]: порог 1,0."""
    if coefficient > EFFICIENCY_THRESHOLD:
        return "эффективна"
    if coefficient == EFFICIENCY_THRESHOLD:
        return "на пороге"
    return "неэффективна"


def integral_coefficient(org: OrganizationData) -> dict[str, float | str]:
    """(13) КЭц = (0,1·∆По + ЭкЭц + (ПТц + НЭц)) / Зц."""
    z_dig = org.digitalization_costs.total()
    if z_dig <= 0:
        raise ValueError("digitalization costs (Зц) must be positive")
    delta_op_profit = org.operating_profit_after - org.operating_profit_before
    eco = ecological_effect(org.ecological)
    pt = labor_productivity_effect(org.social)
    tax = tax_effect(org.social)
    numerator = OPERATING_PROFIT_WEIGHT * delta_op_profit + eco + (pt + tax)
    coefficient = numerator / z_dig
    return {
        "delta_operating_profit": delta_op_profit,
        "ecological_effect": eco,
        "labor_productivity_effect": pt,
        "tax_effect": tax,
        "numerator": numerator,
        "digitalization_cost": z_dig,
        "coefficient": coefficient,
        "zone": efficiency_zone(coefficient),
    }


def derive_costs_after(costs_before: CostFactors,
                       reduction_rate: float = IMPROVEMENT_RATE) -> CostFactors:
    """Смоделировать затраты «после» как «до», сниженные на reduction_rate [65]."""
    k = 1.0 - reduction_rate
    return CostFactors(
        planting_material=costs_before.planting_material * k,
        fertilizers=costs_before.fertilizers * k,
        plant_protection=costs_before.plant_protection * k,
        machinery_cost=costs_before.machinery_cost * k,
        labor_and_social=costs_before.labor_and_social * k,
        additional=costs_before.additional,
    )


# ─────────────────────────── ОПЕРАЦИОННАЯ формула КЭц (виджет Jotform) ───────────────────────────
# Виджет «Калькуляции формы» вычисляет интегральный показатель как ПРОИЗВЕДЕНИЕ
# средних по отношениям «после/до» (индексная модель), а НЕ по текстовой формуле
# (13). Именно эта формула сформировала значения КЭ в таблицах диссертации:
#
#   КЭц = avg( (Зрастит_до/Площ_до)/Затр_на_га ,  Урож_до/Урож_после ,
#              (Приб_после/Сов.затр)/(Приб_до/Общ.затр_до) )
#         × avg( Бензин_до/после ,  Дизель_до/после )
#         × avg( Произв_после/до ,  Налоги_после/до )
#
# Проверено покопеечно на 4 организациях с полными данными (Доброволец 1,12;
# Минскоблагросервис 0,91; Олекшицы 1,22; Тихиничи 0,81); среднее по 6 ≈ 0,99.

def _avg_present(values: list[float | None]) -> float:
    """Среднее без учёта отсутствующих аргументов — как avg() в виджете Jotform."""
    present = [v for v in values if v is not None]
    if not present:
        raise ValueError("avg() requires at least one present argument")
    return sum(present) / len(present)


@dataclass
class EfficiencyIndexInputs:
    """Поля для индексной (виджетной) формулы КЭц. Отношения «после/до»."""
    # экономический блок
    cost_total_before: float          # сумма затрат на растениеводство ДО
    area_before_ha: float             # площадь обрабатываемых земель ДО, га
    cost_per_ha_after: float          # затраты на 1 га (после), руб./га
    yield_before: float               # урожайность ДО, т/га
    yield_after: float                # урожайность ПОСЛЕ, т/га
    profit_after: float | None = None         # прибыль ПОСЛЕ
    total_costs: float | None = None          # совокупные затраты организации
    profit_before: float | None = None        # прибыль ДО
    total_costs_before: float | None = None   # общие затраты организации ДО
    # экологический блок
    petrol_before_t: float = 0.0
    petrol_after_t: float = 0.0
    diesel_before_t: float = 0.0
    diesel_after_t: float = 0.0
    # социальный блок
    productivity_after: float = 0.0
    productivity_before: float = 0.0
    taxes_after: float = 0.0
    taxes_before: float = 0.0


def efficiency_index(x: EfficiencyIndexInputs) -> dict[str, float | str]:
    """Интегральный показатель эффективности цифровизации (виджетная формула).

    КЭц = avg(экономические отношения) × avg(экологические) × avg(социальные).
    Член рентабельности опускается, если отсутствуют совокупные/общие затраты
    (как при пустых полях в avg() виджета).
    """
    a1 = (x.cost_total_before / x.area_before_ha) / x.cost_per_ha_after
    a2 = x.yield_before / x.yield_after
    a3: float | None = None
    if None not in (x.profit_after, x.total_costs, x.profit_before, x.total_costs_before) \
            and x.total_costs and x.total_costs_before:
        a3 = (x.profit_after / x.total_costs) / (x.profit_before / x.total_costs_before)
    economic = _avg_present([a1, a2, a3])
    ecological = _avg_present([
        x.petrol_before_t / x.petrol_after_t,
        x.diesel_before_t / x.diesel_after_t,
    ])
    social = _avg_present([
        x.productivity_after / x.productivity_before,
        x.taxes_after / x.taxes_before,
    ])
    coefficient = economic * ecological * social
    return {
        "economic_index": economic,
        "ecological_index": ecological,
        "social_index": social,
        "coefficient": coefficient,
        "zone": efficiency_zone(coefficient),
    }
