from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID


@dataclass(frozen=True, slots=True)
class LandParcel:
    id: UUID
    dataset_id: UUID
    cadastral_no: str
    koatuu: str | None
    ownership_form: str | None
    intended_use_code: str | None
    intended_use_label: str | None
    location_admin: str | None
    agri_use_kind: str | None
    area_m2: float
    valuation_kop: int | None
    owner_tax_id: str | None
    owner_name_raw: str | None
    share: float
    registered_at: date | None
    record_no: str | None
    registrar: str | None
    record_kind: str | None
    record_subkind: str | None
