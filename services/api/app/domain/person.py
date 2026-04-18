from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Person:
    tax_id: str
    full_name_raw: str
    full_name_norm: str
    sources: frozenset[str] = field(default_factory=frozenset)
