import pytest

from app.services.efficiency import efficiency_index
from app.services.jotform_mapping import (
    efficiency_inputs_from_answers,
    maturity_aggregates_from_answers,
    maturity_level_from_answers,
    organization_name_from_answers,
)


def test_efficiency_inputs_from_answers_reproduces_shipyany(efficiency_answers):
    inputs = efficiency_inputs_from_answers(efficiency_answers)
    # урожайность ПОСЛЕ выведена из валового сбора и площади: 2700/4500 = 0,60
    assert inputs.yield_after == pytest.approx(0.60, abs=0.001)
    # та же индексная формула КЭц, что верифицирована в Спринте 2 → 1,19 (Шипяны)
    assert efficiency_index(inputs)["coefficient"] == pytest.approx(1.19, abs=0.01)


def test_organization_name_detected(efficiency_answers):
    assert "Шипяны" in (organization_name_from_answers(efficiency_answers) or "")


def test_missing_required_field_raises(efficiency_answers):
    a = dict(efficiency_answers)
    del a["1"]  # «Сумма затрат … ДО цифровизации» — обязательное поле
    with pytest.raises(ValueError):
        efficiency_inputs_from_answers(a)


def test_maturity_fields_resolved_by_text(maturity_answers):
    need, cap = maturity_aggregates_from_answers(maturity_answers)
    assert (need, cap) == (pytest.approx(0.46), pytest.approx(0.28))
    assert maturity_level_from_answers(maturity_answers) == pytest.approx(0.36)
