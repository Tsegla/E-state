from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from app.domain.enums import FindingStatus, FindingType, Severity


@dataclass(frozen=True, slots=True)
class FindingEvidence:
    kind: str
    ref_id: UUID
    snapshot: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Finding:
    id: UUID
    dataset_id: UUID
    person_tax_id: str
    finding_type: FindingType
    severity: Severity
    computed_metrics: dict[str, Any]
    evidence: tuple[FindingEvidence, ...] = ()
    status: FindingStatus = FindingStatus.OPEN
    detected_at: datetime | None = None
    last_visit_id: UUID | None = None

    def __post_init__(self) -> None:
        if not self.computed_metrics:
            raise ValueError(
                f"Finding {self.finding_type} requires non-empty computed_metrics"
            )
        if not self.evidence:
            raise ValueError(
                f"Finding {self.finding_type} requires at least one evidence reference"
            )
