"""Нормализация и валидация исходных данных (Спринт 3).

Приводит значения из разных источников (Jotform, Excel, CSV) к единому виду:
русская десятичная запятая → точка, удаление разделителей разрядов и пробелов,
трактовка пустых значений и прочерков как отсутствующих (None).
"""
from __future__ import annotations

# Значения, трактуемые как «нет данных».
_BLANKS = {"", "-", "—", "–", "н/д", "нд", "n/a", "na", "none", "null", "нет"}


def parse_decimal(value: object) -> float | None:
    """Привести значение к float или вернуть None для отсутствующих данных.

    Поддерживает русскую запятую («0,69» → 0.69), разделители разрядов
    («1 234 567» / «1\u00a0234\u00a0567»), уже числовые типы.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("boolean is not a numeric value")
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if s.lower() in _BLANKS:
        return None
    # убрать пробелы-разделители разрядов (обычные и неразрывные)
    s = s.replace("\u00a0", "").replace(" ", "")
    # десятичная запятая → точка (если запятая используется как десятичный разделитель)
    if "," in s and "." not in s:
        s = s.replace(",", ".")
    else:
        s = s.replace(",", "")  # запятая как разделитель тысяч
    try:
        return float(s)
    except ValueError as exc:
        raise ValueError(f"cannot parse numeric value: {value!r}") from exc


def parse_int(value: object) -> int | None:
    """Привести значение к int (через float) или вернуть None."""
    f = parse_decimal(value)
    return None if f is None else int(round(f))


def clean_text(value: object) -> str | None:
    """Очистить строковое значение; пустые → None."""
    if value is None:
        return None
    s = str(value).strip()
    return None if s.lower() in _BLANKS else s


def require_positive(value: float | None, field: str) -> float:
    """Проверить, что знаменатель строго положителен (для отношений «после/до»)."""
    if value is None or value <= 0:
        raise ValueError(f"{field}: ожидается строго положительное значение, получено {value!r}")
    return value
