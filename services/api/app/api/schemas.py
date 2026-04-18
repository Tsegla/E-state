"""Shared request/response DTOs. Stay close to [docs/api-contract.md](../../../docs/api-contract.md)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import FindingStatus, FindingType, Severity


class DatasetSummaryDTO(BaseModel):
    id: UUID
    label: str
    uploaded_at: datetime
    uploaded_by: str | None = None
    status: str
    zem_rows: int = 0
    ner_rows: int = 0
    findings_total: int = 0


class MatcherRunRequest(BaseModel):
    dataset_id: UUID


class MatcherRunResponse(BaseModel):
    dataset_id: UUID
    findings_created: int
    by_type: dict[str, int]
    by_severity: dict[str, int]
    duration_ms: int


class FindingEvidenceDTO(BaseModel):
    kind: str
    ref_id: UUID
    snapshot: dict[str, Any] = Field(default_factory=dict)


class FindingSummaryDTO(BaseModel):
    id: UUID
    dataset_id: UUID
    person_tax_id_masked: str
    finding_type: FindingType
    severity: Severity
    status: FindingStatus
    computed_metrics: dict[str, Any]
    detected_at: datetime


class FindingDetailDTO(FindingSummaryDTO):
    evidence: list[FindingEvidenceDTO]
    person_name_masked: str


class InspectorVisitCreate(BaseModel):
    finding_id: UUID
    actual_object_type: str | None = None
    actual_area_m2: float | None = None
    actual_use: str | None = None
    notes: str | None = Field(default=None, max_length=2000)
    gps: dict[str, float] | None = None
    photo_refs: list[dict[str, Any]] = Field(default_factory=list)
    resolution: FindingStatus = FindingStatus.RESOLVED


class InspectorVisitDTO(BaseModel):
    id: UUID
    finding_id: UUID
    inspector_id: str
    actual_object_type: str | None
    actual_area_m2: float | None
    actual_use: str | None
    notes: str | None
    gps: dict[str, float] | None
    photo_refs: list[dict[str, Any]]
    created_at: datetime


class CitizenLookupRequest(BaseModel):
    tax_id: str = Field(min_length=8, max_length=10)
    captcha_token: str = Field(min_length=1)
    consent: bool

    model_config = ConfigDict(extra="forbid")


class CitizenAssetDTO(BaseModel):
    kind: str  # "land_parcel" | "real_estate"
    label: str
    area_m2: float
    location_masked: str | None = None


class CitizenLookupResponse(BaseModel):
    owner_name_masked: str
    assets: list[CitizenAssetDTO]
    unresolved_findings: int
    last_checked_at: datetime


class BudgetImpactDTO(BaseModel):
    total_uah_per_year: float
    by_type: dict[str, float]


class UploadResponse(BaseModel):
    dataset_id: UUID
    label: str
    zem_rows: int
    ner_rows: int
    persons: int
