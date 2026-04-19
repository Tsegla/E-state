"""Declarative schemas for the ingested workbooks.

Keeping the required columns and regex rules in data rather than buried in
:mod:`app.ingest.excel` means the checks can be adjusted without touching the
loading logic. Both the ingest pipeline and the validation layer read from the
same :class:`InputSchema` instances defined here.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class InputSchema:
    """Column contract + identifier regex rules for a workbook."""

    name: str
    required_columns: tuple[str, ...]
    optional_columns: tuple[str, ...] = field(default_factory=tuple)

    owner_id_column: str | None = None
    owner_id_pattern: str | None = None

    cadastral_column: str | None = None
    cadastral_pattern: str | None = None


# Regex sources of truth. Expose separately so other modules (normalize,
# tests, docs) can import them without re-declaring the string.
EDRPOU_PATTERN: str = r"^\d{8}$"
TAX_ID_PATTERN: str = r"^\d{8,10}$"
CADASTRAL_PATTERN: str = r"^\d{10}:\d{2}:\d{3}:\d{4}$"


ZEM_SCHEMA = InputSchema(
    name="zem",
    required_columns=(
        "Кадастровий номер",
        "Форма власності",
        "Цільове призначення",
        "Місцерозташування",
        "Площа, га",
        "Усереднена нормативно грошова оцінка",
        "ЄДРПОУ землекористувача",
        "Землекористувач",
        "Дата державної реєстрації права власності",
        "Номер запису про право власності",
        "Орган, що здійснив державну реєстрацію права власності",
        "Тип",
        "Підтип",
    ),
    optional_columns=(
        "koatuu",
        "Вид с/г угідь",
        "Частка володіння",
    ),
    owner_id_column="ЄДРПОУ землекористувача",
    owner_id_pattern=EDRPOU_PATTERN,
    cadastral_column="Кадастровий номер",
    cadastral_pattern=CADASTRAL_PATTERN,
)


# NER / ДРРП contains owners who can be either physical persons (10-digit
# РНОКПП) or legal entities (8-digit ЄДРПОУ); relax the pattern accordingly.
NER_SCHEMA = InputSchema(
    name="ner",
    required_columns=(
        "Податковий номер ПП",
        "Назва платника",
        "Тип об'єкта",
        "Адреса об'єкта",
        "Дата держ. реєстр. права власн",
        "Дата держ. реєстр. прип. права власн",
        "Загальна площа",
        "Розмір частки у праві спільної власності",
    ),
    optional_columns=(
        "Вид спіль ної власності",
        "Вид спільної власності",
    ),
    owner_id_column="Податковий номер ПП",
    owner_id_pattern=TAX_ID_PATTERN,
    cadastral_column=None,
    cadastral_pattern=None,
)


__all__ = [
    "CADASTRAL_PATTERN",
    "EDRPOU_PATTERN",
    "NER_SCHEMA",
    "TAX_ID_PATTERN",
    "ZEM_SCHEMA",
    "InputSchema",
]
