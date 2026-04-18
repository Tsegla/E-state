from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class FieldVisit:
    id: UUID
    finding_id: UUID
    inspector_id: str
    photo_refs: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    actual_object_type: str | None = None
    actual_area_m2: float | None = None
    actual_use: str | None = None
    notes: str | None = None
    gps: dict[str, float] | None = None
    created_at: datetime | None = None
