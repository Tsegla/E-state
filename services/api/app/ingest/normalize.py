"""Pure normalization helpers per [docs/data-dictionary.md](../../../docs/data-dictionary.md)."""

from __future__ import annotations

import re
import unicodedata
from datetime import date, timedelta

_EXCEL_EPOCH = date(1899, 12, 30)

_CAD_RE = re.compile(r"^\d{10}:\d{2}:\d{3}:\d{4}$")
_TAX_ID_RE = re.compile(r"^\d{8,10}$")
_USE_CODE_RE = re.compile(r"^(\d{2}\.\d{2})\s+(.+)$")


def excel_serial_to_date(value: str | float | int | None) -> date | None:
    """Convert an Excel date serial to a Python ``date``.

    Excel counts days from 1900-01-01 but incorrectly treats 1900 as a leap
    year, which is why the 1899-12-30 anchor is correct.
    """
    if value in (None, "", 0, "0"):
        return None
    try:
        days = int(float(value))
    except (TypeError, ValueError):
        return None
    if days <= 0:
        return None
    return _EXCEL_EPOCH + timedelta(days=days)


def ga_to_m2(value: str | float | int | None) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(value) * 10_000.0
    except (TypeError, ValueError):
        return 0.0


def parse_float(value: str | float | int | None, default: float = 0.0) -> float:
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_tax_id(value: str | None) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    if not _TAX_ID_RE.match(s):
        return None
    return s


def normalize_cadastral(value: str | None) -> str | None:
    if value is None:
        return None
    s = str(value).strip().upper().replace(" ", "")
    if not s:
        return None
    return s if _CAD_RE.match(s) else s


def normalize_koatuu(value: str | None) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    digits = re.sub(r"\D", "", s)
    return digits.rjust(10, "0") if digits else None


def normalize_name(raw: str | None) -> str:
    if not raw:
        return ""
    s = unicodedata.normalize("NFKC", str(raw)).strip().lower().replace("ё", "е")
    return " ".join(s.split())


def split_intended_use(raw: str | None) -> tuple[str | None, str | None]:
    """Split ``"02.01 Для будівництва..."`` into ``(code, label)``."""
    if not raw:
        return (None, None)
    s = str(raw).strip()
    if not s:
        return (None, None)
    m = _USE_CODE_RE.match(s)
    if m:
        return (m.group(1), m.group(2).strip())
    return (None, s)


_OBJECT_TYPE_MAP: dict[str, str] = {
    # квартира
    "квартира": "квартира",
    # residential houses
    "житловий будинок": "житловий_будинок",
    "будинок": "житловий_будинок",
    "садовий будинок": "житловий_будинок",
    # garages
    "гараж": "гараж",
    "гаражi": "гараж",
    "гаражі": "гараж",
    # non-residential building
    "нежитлова будiвля": "нежитлова_будівля",
    "нежитлова будівля": "нежитлова_будівля",
    "будiвля": "нежитлова_будівля",
    "будівля": "нежитлова_будівля",
    # non-residential premises
    "нежиле примiщення": "нежитлове_приміщення",
    "нежиле приміщення": "нежитлове_приміщення",
    "нежитлове примiщення": "нежитлове_приміщення",
    "нежитлове приміщення": "нежитлове_приміщення",
    "примiщення": "нежитлове_приміщення",
    "приміщення": "нежитлове_приміщення",
    # industrial
    "будiвлi промисловостi та склади": "промислова_будівля",
    "будівлі промисловості та склади": "промислова_будівля",
    "iншi будiвлi": "промислова_будівля",
    "інші будівлі": "промислова_будівля",
    # retail / office
    "будiвлi торговельнi": "торгова_будівля",
    "будівлі торговельні": "торгова_будівля",
    "будiвлi офiснi": "офісна_будівля",
    "будівлі офісні": "офісна_будівля",
}


def normalize_object_type(raw: str | None) -> str:
    if not raw:
        return "інше"
    s = unicodedata.normalize("NFKC", str(raw)).strip().lower()
    # Collapse Latin 'i' to Cyrillic 'і' (the ДРРП export mixes both)
    s_collapsed = s.replace("i", "і").replace("\u0456", "і")
    s = " ".join(s.split())
    s_collapsed = " ".join(s_collapsed.split())
    return _OBJECT_TYPE_MAP.get(s) or _OBJECT_TYPE_MAP.get(s_collapsed) or "інше"


def normalize_address(raw: str | None) -> str:
    if not raw:
        return ""
    s = unicodedata.normalize("NFKC", str(raw)).strip().lower()
    return " ".join(s.split())


def valuation_to_kop(value: str | float | int | None) -> int | None:
    if value in (None, ""):
        return None
    try:
        uah = float(value)
    except (TypeError, ValueError):
        return None
    return int(round(uah * 100))
