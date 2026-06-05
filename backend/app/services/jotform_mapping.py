"""Сопоставление полей форм Jotform с входами расчётного ядра.

Карты подтверждены авторитетной выгрузкой соискателя (Pilot_Organizations_v2_0):
  * «Эффективность цифровизации» (222133487281353) — резолвинг по тексту полей;
    «урожайность ПОСЛЕ» отдельным полем не хранится и ВЫЧИСЛЯЕТСЯ как
    валовый сбор ÷ площадь обрабатываемых земель.
  * «Цифровая зрелость» (241376010701342) — два агрегата (потребность/возможности)
    и итоговый «Уровень цифровой зрелости» читаются по тексту полей.

Индексная формула КЭц и геометрическое среднее зрелости верифицированы на 7
пилотных организациях (см. tests/test_data_layer.py, tests/test_reports.py).
"""
from __future__ import annotations

from app.services.efficiency import EfficiencyIndexInputs
from app.services.normalize import parse_decimal, parse_int

# ─── Форма «Эффективность цифровизации»: ТЕКСТ поля → поле входа ───
EFFICIENCY_TEXT_MAP: dict[str, str] = {
    "Сумма затрат организации на производство продукции растительного происхождения ДО цифровизации, рублей": "cost_total_before",
    "1.2.1 Площадь обрабатываемых земель ДО цифровизации, га": "area_before_ha",
    "Затраты организации на 1 га обрабатываемых земель, рублей/га": "cost_per_ha_after",
    "Средняя урожайность культур в организации ДО цифровизации, тонн/га": "yield_before",
    "3.2.2 Прибыль от реализации продукции ПОСЛЕ цифровизации, рублей": "profit_after",
    "Направлено денежных средств (всего), рублей": "total_costs",
    "3.2.1 Прибыль от реализации продукции ДО цифровизации, рублей": "profit_before",
    "Направлено денежных средств (всего) ДО цифровизации, рублей": "total_costs_before",
    "2.1 Объем сожженного бензина ДО цифровизации, тонн": "petrol_before_t",
    "2.2 Объем сожженного бензина ПОСЛЕ цифровизации, тонн": "petrol_after_t",
    "2.3 Объем сожженного топлива дизельного ДО цифровизации, тонн": "diesel_before_t",
    "2.4 Объем сожженного топлива дизельного ПОСЛЕ цифровизации, тонн": "diesel_after_t",
    "Производительность труда ПОСЛЕ цифровизации, рублей/чел.": "productivity_after",
    "Производительность труда ДО цифровизации, рублей/чел.": "productivity_before",
    "Направлено денежных средств на уплату налогов и сборов ПОСЛЕ цифровизации, рублей": "taxes_after",
    "Направлено денежных средств на уплату налогов и сборов ДО цифровизации, рублей": "taxes_before",
}
# «Урожайность ПОСЛЕ» = валовый сбор ÷ площадь обрабатываемых земель (текущая)
GROSS_HARVEST_TEXT = "1.1.8 Валовый сбор урожая возделываемых культур, тонн"
AREA_CURRENT_TEXT = "1.1.7 Площадь обрабатываемых земель, га"

# ─── Форма «Цифровая зрелость»: тексты агрегатов и итогового уровня ───
MATURITY_NEED_AVG_TEXT = "Среднее значение показателей потребности во внедрении цифровых технологий"
MATURITY_CAPABILITY_AVG_TEXT = "Среднее значение показателей возможностей во внедрении цифровых технологий"
MATURITY_LEVEL_TEXT = "Уровень цифровой зрелости Вашей организации"

_OPTIONAL = {"profit_after", "total_costs", "profit_before", "total_costs_before"}
_REQUIRED = set(EfficiencyIndexInputs.__dataclass_fields__) - _OPTIONAL


def _norm(s: object) -> str:
    return " ".join(str(s or "").split()).lower()


def extract_answer(answers: dict, qid: str) -> object:
    cell = answers.get(qid)
    if cell is None:
        return None
    if isinstance(cell, dict):
        return cell.get("answer", cell.get("prettyFormat"))
    return cell


def answer_by_text(answers: dict, target_text: str) -> object:
    """Найти ответ по тексту вопроса (cell['text']); без учёта регистра/пробелов."""
    t = _norm(target_text)
    for cell in answers.values():
        if isinstance(cell, dict) and _norm(cell.get("text", "")) == t:
            return cell.get("answer", cell.get("prettyFormat"))
    return None


def efficiency_inputs_from_answers(answers: dict) -> EfficiencyIndexInputs:
    """Построить EfficiencyIndexInputs из сабмишена формы эффективности (по тексту полей)."""
    values: dict[str, float | None] = {}
    for text, field in EFFICIENCY_TEXT_MAP.items():
        values[field] = parse_decimal(answer_by_text(answers, text))
    # урожайность ПОСЛЕ = валовый сбор / площадь обрабатываемых земель
    gross = parse_decimal(answer_by_text(answers, GROSS_HARVEST_TEXT))
    area = parse_decimal(answer_by_text(answers, AREA_CURRENT_TEXT))
    if gross is not None and area:
        values["yield_after"] = gross / area
    missing = [f for f in _REQUIRED if values.get(f) is None]
    if missing:
        raise ValueError(f"Отсутствуют обязательные поля: {', '.join(sorted(missing))}")
    return EfficiencyIndexInputs(**values)


def maturity_aggregates_from_answers(
    answers: dict,
    need_text: str = MATURITY_NEED_AVG_TEXT,
    capability_text: str = MATURITY_CAPABILITY_AVG_TEXT,
) -> tuple[float, float]:
    """Прочитать агрегаты потребности и возможностей формы зрелости (по тексту полей)."""
    need = parse_decimal(answer_by_text(answers, need_text))
    cap = parse_decimal(answer_by_text(answers, capability_text))
    if need is None or cap is None:
        raise ValueError(
            "Не найдены агрегаты «Среднее значение показателей потребности/возможностей»"
        )
    return need, cap


def maturity_level_from_answers(answers: dict,
                                level_text: str = MATURITY_LEVEL_TEXT) -> float | None:
    """Прочитать итоговый «Уровень цифровой зрелости», вычисленный формой (если есть)."""
    return parse_decimal(answer_by_text(answers, level_text))


def maturity_scores_from_answers(
    answers: dict, need_qids: list[str], capability_qids: list[str]
) -> tuple[list[float], list[float]]:
    """Извлечь оценки потребности/возможностей по спискам qid (режим отдельных показателей)."""
    need = [parse_decimal(extract_answer(answers, q)) for q in need_qids]
    cap = [parse_decimal(extract_answer(answers, q)) for q in capability_qids]
    need = [v for v in need if v is not None]
    cap = [v for v in cap if v is not None]
    if not need or not cap:
        raise ValueError("Не удалось извлечь оценки потребности/возможностей по указанным qid")
    return need, cap


def organization_name_from_answers(answers: dict, name_qids: tuple[str, ...] = ()) -> str | None:
    for q in name_qids:
        v = extract_answer(answers, q)
        if v:
            return str(v).strip()
    for cell in answers.values():
        if isinstance(cell, dict):
            name = (cell.get("name") or "").lower()
            text = (cell.get("text") or "").lower()
            if "наименован" in name or "наименован" in text or "организац" in name:
                if cell.get("answer"):
                    return str(cell["answer"]).strip()
    return None


__all__ = [
    "EFFICIENCY_TEXT_MAP", "GROSS_HARVEST_TEXT", "AREA_CURRENT_TEXT",
    "MATURITY_NEED_AVG_TEXT", "MATURITY_CAPABILITY_AVG_TEXT", "MATURITY_LEVEL_TEXT",
    "efficiency_inputs_from_answers", "maturity_aggregates_from_answers",
    "maturity_level_from_answers", "maturity_scores_from_answers",
    "organization_name_from_answers", "answer_by_text", "extract_answer", "parse_int",
]
