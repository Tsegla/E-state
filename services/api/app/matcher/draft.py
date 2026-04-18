"""Lightweight ``FindingDraft`` used inside the matcher before DB persistence."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.domain.enums import FindingType, Severity


@dataclass(frozen=True, slots=True)
class EvidenceRef:
    kind: str  # "land_parcel" | "real_estate"
    ref_id: UUID
    snapshot: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FindingDraft:
    person_tax_id: str
    finding_type: FindingType
    severity: Severity
    computed_metrics: dict[str, Any]
    evidence: tuple[EvidenceRef, ...]

    def __post_init__(self) -> None:
        if not self.computed_metrics:
            raise ValueError(
                f"FindingDraft {self.finding_type} requires non-empty computed_metrics"
            )
        if not self.evidence:
            raise ValueError(
                f"FindingDraft {self.finding_type} requires at least one evidence reference"
            )
