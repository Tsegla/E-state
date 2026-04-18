from app.security.pii import mask_name, mask_tax_id


def test_mask_tax_id_hides_middle() -> None:
    assert mask_tax_id("1234567890") == "12••••••90"


def test_mask_tax_id_short() -> None:
    assert mask_tax_id("1234") == "••••••"


def test_mask_tax_id_none() -> None:
    assert mask_tax_id(None) == ""


def test_mask_name_initials() -> None:
    assert mask_name("Хоцевич Григорій Іванович") == "Х. Г. І."


def test_mask_name_empty() -> None:
    assert mask_name("") == ""
