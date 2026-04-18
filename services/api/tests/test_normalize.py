from datetime import date

from app.ingest.normalize import (
    excel_serial_to_date,
    ga_to_m2,
    normalize_cadastral,
    normalize_name,
    normalize_object_type,
    normalize_tax_id,
    split_intended_use,
    valuation_to_kop,
)


def test_excel_serial_to_date_typical() -> None:
    # 44562 -> 2022-01-01 (Excel)
    assert excel_serial_to_date(44562) == date(2022, 1, 1)


def test_excel_serial_to_date_empty() -> None:
    assert excel_serial_to_date(None) is None
    assert excel_serial_to_date("") is None
    assert excel_serial_to_date(0) is None


def test_ga_to_m2() -> None:
    assert ga_to_m2(1.5) == 15000.0
    assert ga_to_m2("") == 0.0
    assert ga_to_m2(None) == 0.0


def test_normalize_tax_id_valid() -> None:
    assert normalize_tax_id("1234567890") == "1234567890"
    assert normalize_tax_id(" 12345678") == "12345678"


def test_normalize_tax_id_invalid() -> None:
    assert normalize_tax_id("abc") is None
    assert normalize_tax_id("") is None
    assert normalize_tax_id(None) is None


def test_split_intended_use() -> None:
    assert split_intended_use("02.01 Для будівництва і обслуговування жилого будинку") == (
        "02.01",
        "Для будівництва і обслуговування жилого будинку",
    )
    assert split_intended_use("Без коду") == (None, "Без коду")


def test_normalize_object_type_collapse_latin_i() -> None:
    assert normalize_object_type("Нежитлова будiвля") == "нежитлова_будівля"
    assert normalize_object_type("квартира") == "квартира"
    assert normalize_object_type("невідомий") == "інше"


def test_normalize_name_lowercase_collapse() -> None:
    assert normalize_name("  Хоцевич   Григорій  ") == "хоцевич григорій"


def test_normalize_cadastral() -> None:
    assert normalize_cadastral(" 1234567890:01:002:0003 ") == "1234567890:01:002:0003"


def test_valuation_to_kop() -> None:
    assert valuation_to_kop(12.34) == 1234
    assert valuation_to_kop(None) is None
