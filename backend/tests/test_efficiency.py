"""Юнит-тесты расчётного ядра эффективности [Кандидатская_T3, §2.3; Formulas_10-13].

Экономическая цепочка (1)–(8) и формулы (11), (12) проверяются в том числе на
фактических данных пилотных организаций. По сводному коэффициенту (13) см.
оговорку: при Зц=Σ(строки 11–15) итог строки 55 книги пилота не воспроизводится
из сводных строк (расхождение масштабов в книге), поэтому проверяется структура.
"""
import pytest

from app.services.efficiency import (
    EFFICIENCY_THRESHOLD,
    IMPROVEMENT_RATE,
    CostFactors,
    DigitalizationCosts,
    EcologicalInputs,
    EconomicInputs,
    FertilizerChange,
    OrganizationData,
    SocialInputs,
    biological_effect,
    cost_per_ha,
    cost_per_tonne,
    derive_costs_after,
    ecological_effect,
    economic_effect,
    efficiency_zone,
    integral_coefficient,
    labor_productivity_effect,
    production_cost,
    social_effect,
    tax_effect,
    tech_tech_effect,
)


def _costs_before() -> CostFactors:
    return CostFactors(200.0, 300.0, 150.0, 250.0, 100.0, 0.0)  # = 1000


def _costs_after() -> CostFactors:
    return CostFactors(180.0, 270.0, 135.0, 225.0, 90.0, 0.0)   # = 900


def _econ() -> EconomicInputs:
    return EconomicInputs(_costs_before(), _costs_after(), 200.0, 100.0, 110.0, 5.0)


# ─── экономическая цепочка (1)–(8) ───
def test_production_cost_formula_1():
    assert production_cost(_costs_before()) == pytest.approx(1000.0)


def test_cost_per_ha_and_tonne_2_3():
    assert cost_per_ha(_costs_before(), 200.0) == pytest.approx(5.0)
    assert cost_per_tonne(_costs_before(), 100.0) == pytest.approx(10.0)


def test_tech_tech_effect_4_6():
    r = tech_tech_effect(_econ())
    assert r["ttae_c"] == pytest.approx(100.0)
    assert r["ttae_ga"] == pytest.approx(100.0)
    assert r["ttae_tn"] == pytest.approx(200.0)


def test_biological_and_economic_7_8():
    assert biological_effect(_econ()) == pytest.approx(50.0)
    assert economic_effect(_econ()) == pytest.approx(150.0)


def test_derive_costs_after_10_percent():
    assert production_cost(derive_costs_after(_costs_before(), IMPROVEMENT_RATE)) == pytest.approx(900.0)


# ─── экологический эффект (10) ───
def test_ecological_effect_formula_10():
    x = EcologicalInputs(
        area_ha=100.0,
        petrol_before_t=10.0, petrol_after_t=7.0,     # ∆Б = 3
        diesel_before_t=20.0, diesel_after_t=15.0,    # ∆ДТ = 5
        fertilizers=[FertilizerChange(change_t=2.0, price_rub_per_t=30.0)],
    )
    # 8·100 + 260·3 + 259·5 + 2·30 = 800 + 780 + 1295 + 60 = 2935
    assert ecological_effect(x) == pytest.approx(2935.0)


# ─── формулы (11), (12) на ФАКТИЧЕСКИХ данных «Доброволец» ───
def _dobrovolets_social() -> SocialInputs:
    return SocialInputs(
        revenue_before_rub=49_000_000.0, revenue_after_rub=51_200_000.0,
        headcount_before=450, headcount_after=450,
        taxable_profit_before=2_300_000.0, taxable_profit_after=2_550_000.0,
        value_added_before=8_123_227.16, value_added_after=10_200_000.0,
        payroll_before=6_480_000.0, payroll_after=6_500_000.0,
        fixed_assets_before=190_000_000.0, fixed_assets_after=190_076_227.16,
    )


def test_labor_productivity_effect_11_matches_workbook():
    # Доброволец: 51 200 000/450 − 49 000 000/450 = 4 888,89 (строка 45)
    assert labor_productivity_effect(_dobrovolets_social()) == pytest.approx(4888.89, abs=0.01)


def test_tax_effect_12_matches_workbook():
    # Доброволец: 0,18·250000 + 0,1·2076772,84 + 0,13·20000 + 0,01·76227,16 = 256 039,56 (строка 54)
    assert tax_effect(_dobrovolets_social()) == pytest.approx(256039.56, abs=0.01)


# ─── сводный коэффициент (13): структура ───
def test_integral_coefficient_structure_13():
    org = OrganizationData(
        name="Тест",
        economic=_econ(),
        ecological=EcologicalInputs(area_ha=125.0),          # ЭкЭц = 8·125 = 1000
        social=SocialInputs(                                  # ПТц = 0, НЭц = 0
            revenue_before_rub=1000.0, revenue_after_rub=1000.0,
            headcount_before=1, headcount_after=1,
        ),
        digitalization_costs=DigitalizationCosts(other=1000.0),  # Зц = 1000
        operating_profit_before=0.0, operating_profit_after=0.0, # ∆По = 0
    )
    r = integral_coefficient(org)
    assert r["numerator"] == pytest.approx(1000.0)   # 0 + 1000 + (0 + 0)
    assert r["coefficient"] == pytest.approx(1.0)
    assert r["zone"] == "на пороге"


def test_efficiency_zone_thresholds():
    assert efficiency_zone(1.22) == "эффективна"
    assert efficiency_zone(EFFICIENCY_THRESHOLD) == "на пороге"
    assert efficiency_zone(0.81) == "неэффективна"


def test_social_effect_is_pt_plus_tax():
    s = _dobrovolets_social()
    assert social_effect(s) == pytest.approx(labor_productivity_effect(s) + tax_effect(s))


def test_integral_requires_positive_costs():
    org = OrganizationData(
        name="Без затрат", economic=_econ(),
        ecological=EcologicalInputs(area_ha=1.0),
        social=SocialInputs(0.0, 0.0, 1, 1),
        digitalization_costs=DigitalizationCosts(),
    )
    with pytest.raises(ValueError):
        integral_coefficient(org)


# ─── ВЕРИФИКАЦИЯ виджетной (индексной) формулы КЭц на фактических данных ───
import json  # noqa: E402
from pathlib import Path  # noqa: E402

from app.services.efficiency import (  # noqa: E402
    EfficiencyIndexInputs,
    efficiency_index,
)

_PILOT = json.loads((Path(__file__).parent / "data" / "pilot_efficiency.json").read_text(encoding="utf-8"))


def _to_inputs(rec: dict) -> EfficiencyIndexInputs:
    keys = {k: rec[k] for k in (
        "cost_total_before", "area_before_ha", "cost_per_ha_after", "yield_before", "yield_after",
        "profit_after", "total_costs", "profit_before", "total_costs_before",
        "petrol_before_t", "petrol_after_t", "diesel_before_t", "diesel_after_t",
        "productivity_after", "productivity_before", "taxes_after", "taxes_before")}
    return EfficiencyIndexInputs(**keys)


@pytest.mark.parametrize("rec", [r for r in _PILOT if r["complete"]], ids=lambda r: r["name"])
def test_widget_efficiency_matches_for_complete_orgs(rec):
    # все 7 организаций воспроизводят интегральный коэффициент формы (r55) до 2 знаков
    got = efficiency_index(_to_inputs(rec))["coefficient"]
    assert got == pytest.approx(rec["ke"], abs=0.005), f"{rec['name']}: {got:.4f} ≠ {rec['ke']}"


def test_widget_efficiency_mean_is_benchmark():
    # среднее по 7 организациям ≈ 1,00
    vals = [efficiency_index(_to_inputs(r))["coefficient"] for r in _PILOT]
    assert sum(vals) / len(vals) == pytest.approx(1.00, abs=0.01)


def test_widget_efficiency_zone_classification():
    by_name = {r["name"]: efficiency_index(_to_inputs(r)) for r in _PILOT}
    zone = lambda sub: next(v["zone"] for n, v in by_name.items() if sub in n)  # noqa: E731
    assert zone("Шипяны") == "эффективна"        # 1,19 > 1,0
    assert zone("ДолжаАгро") == "неэффективна"   # 0,56 < 1,0
    assert zone("Достоево") == "эффективна"       # 1,21 > 1,0
