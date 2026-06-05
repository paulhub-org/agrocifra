"""Тесты расчётного ядра: метод Гурвица, интегральный коэффициент, DSCR/ICR."""
import pytest

from app.services.calculations import (
    HURWICZ_HIGH,
    HURWICZ_LOW,
    digital_maturity,
    digital_maturity_zone,
    dscr,
    hurwicz_value,
    hurwicz_zone,
    icr,
    integral_efficiency,
)


def test_hurwicz_value_bounds():
    payoffs = [10.0, 50.0, 30.0]
    assert hurwicz_value(payoffs, 0.0) == 10.0  # пессимизм → min
    assert hurwicz_value(payoffs, 1.0) == 50.0  # оптимизм → max
    assert hurwicz_value(payoffs, 0.5) == 30.0  # 0.5*50 + 0.5*10


def test_hurwicz_zone_thresholds():
    assert hurwicz_zone(HURWICZ_LOW - 0.01) == "conservative"
    assert hurwicz_zone(HURWICZ_LOW) == "balanced"
    assert hurwicz_zone(HURWICZ_HIGH) == "balanced"
    assert hurwicz_zone(HURWICZ_HIGH + 0.01) == "optimistic"


def test_integral_equal_weights():
    # равнозначные компоненты: (0.9 + 1.2 + 0.9) / 3 = 1.0
    assert integral_efficiency(0.9, 1.2, 0.9) == pytest.approx(1.0)


def test_integral_weights_must_sum_to_one():
    with pytest.raises(ValueError):
        integral_efficiency(1.0, 1.0, 1.0, weights=(0.5, 0.5, 0.5))


def test_dscr_and_icr():
    assert dscr(150.0, 60.0, 40.0) == pytest.approx(1.5)
    assert icr(200.0, 100.0) == pytest.approx(2.0)


def test_invalid_inputs():
    with pytest.raises(ValueError):
        hurwicz_value([], 0.5)
    with pytest.raises(ValueError):
        hurwicz_value([1.0], 1.5)
    with pytest.raises(ValueError):
        dscr(100.0, 0.0, 0.0)


def test_digital_maturity_zone_thresholds():
    # границы 0,134 / 0,366 [Кандидатская_T3, п. 2.2.2]
    assert digital_maturity_zone(HURWICZ_LOW - 0.01) == "низкая"
    assert digital_maturity_zone(HURWICZ_LOW) == "средняя"
    assert digital_maturity_zone(HURWICZ_HIGH) == "средняя"
    assert digital_maturity_zone(HURWICZ_HIGH + 0.01) == "высокая"
    # значение выше 0,366 → высокая зрелость
    assert digital_maturity_zone(0.55) == "высокая"


def test_digital_maturity_is_geometric_mean():
    # итоговый уровень = sqrt(потребность · возможности) [подтверждено формой зрелости]
    r = digital_maturity([0.21], [1.01])
    assert r["maturity"] == pytest.approx(0.4605, abs=0.001)   # sqrt(0,21·1,01)
    assert r["zone"] == "высокая"
    assert digital_maturity([0.46], [0.28])["maturity"] == pytest.approx(0.359, abs=0.001)


# Верификация цифровой зрелости на 7 пилотных организациях (форма «Цифровая
# зрелость», 241376010701342): итог — ГЕОМЕТРИЧЕСКОЕ среднее средних потребности
# и возможностей; классификация по 0,134 / 0,366. Среднее по 7 организациям ≈ 0,35.
PILOT_MATURITY = [
    # (name, need, capability, expected_level, expected_zone)
    ("Шипяны-АСК", 0.46, 0.28, 0.36, "средняя"),
    ("Достоево", 0.39, 0.10, 0.20, "средняя"),
    ("ДолжаАгро", 0.33, 0.92, 0.55, "высокая"),
    ("Криничная", 0.44, 0.35, 0.39, "высокая"),
    ("Олекшицы", 0.19, 0.28, 0.23, "средняя"),
    ("Минскоблагросервис", 0.21, 1.01, 0.46, "высокая"),
    ("Учхоз БГСХА", 0.21, 0.32, 0.26, "средняя"),
]


@pytest.mark.parametrize("name,need,cap,exp,zone", PILOT_MATURITY)
def test_pilot_digital_maturity(name, need, cap, exp, zone):
    r = digital_maturity([need], [cap])
    assert r["maturity"] == pytest.approx(exp, abs=0.01)
    assert r["zone"] == zone


def test_pilot_digital_maturity_mean_is_benchmark():
    mats = [digital_maturity([n], [c])["maturity"] for _, n, c, _, _ in PILOT_MATURITY]
    assert sum(mats) / len(mats) == pytest.approx(0.35, abs=0.01)
