import pytest

from app.services.normalize import parse_decimal, parse_int, clean_text, require_positive


def test_parse_decimal_russian_comma():
    assert parse_decimal("0,69") == pytest.approx(0.69)
    assert parse_decimal("40876772,84") == pytest.approx(40876772.84)


def test_parse_decimal_thousands_and_spaces():
    assert parse_decimal("1 234 567") == pytest.approx(1234567.0)
    assert parse_decimal("1\u00a0234\u00a0567,5") == pytest.approx(1234567.5)


def test_parse_decimal_blanks_and_numbers():
    for blank in (None, "", "—", "-", "н/д", "N/A"):
        assert parse_decimal(blank) is None
    assert parse_decimal(5) == 5.0
    assert parse_decimal(0.48) == pytest.approx(0.48)


def test_parse_decimal_rejects_garbage():
    with pytest.raises(ValueError):
        parse_decimal("abc")


def test_parse_int_and_clean_text():
    assert parse_int("450,0") == 450
    assert parse_int("—") is None
    assert clean_text("  Доброволец ") == "Доброволец"
    assert clean_text("—") is None


def test_require_positive():
    assert require_positive(3.0, "x") == 3.0
    with pytest.raises(ValueError):
        require_positive(0, "x")
    with pytest.raises(ValueError):
        require_positive(None, "x")
