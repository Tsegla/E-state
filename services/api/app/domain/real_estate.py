from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RealEstate:
    id: UUID
    dataset_id: UUID
    owner_tax_id: str | None
    owner_name_raw: str | None
    object_type_raw: str | None
    object_type_norm: str | None
    address_raw: str | None
    address_norm: str | None
    area_m2: float
    registered_at: date | None
    terminated_at: date | None
    joint_ownership_kind: str | None
    share: float
