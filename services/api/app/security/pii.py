"""PII masking helpers. ALWAYS mask РНОКПП in logs, audit payloads, and citizen responses."""

from __future__ import annotations

_PLACEHOLDER = "••••••"


def mask_tax_id(value: str | None) -> str:
    """Keep the first 2 and last 2 characters, mask the middle.

    Example: ``"1234567890" -> "12••••••90"``.
    """
    if not value:
        return ""
    s = str(value).strip()
    if len(s) <= 4:
        return _PLACEHOLDER
    return f"{s[:2]}{_PLACEHOLDER}{s[-2:]}"


def mask_name(value: str | None) -> str:
    """Keep the first letter of each name part, mask the rest."""
    if not value:
        return ""
    parts = str(value).strip().split()
    return " ".join((p[:1] + "." if p else "") for p in parts)
