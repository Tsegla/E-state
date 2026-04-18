"""Detector: ДЗК land parcel without any tax_id or owner name."""

from __future__ import annotations

from app.domain.enums import FindingType, Severity
from app.matcher.context import MatcherContext
from app.matcher.detectors._helpers import land_evidence
from app.matcher.draft import FindingDraft

_UNKNOWN_PLACEHOLDER = "__unknown__"


def detect_missing_owner(ctx: MatcherContext) -> list[FindingDraft]:
    if ctx.zem.empty:
        return []
    z = ctx.zem
    orphans = z[z["owner_tax_id"].isna() & (z["owner_name_raw"].isna() | (z["owner_name_raw"] == ""))]
    if orphans.empty:
        return []
    return [
        FindingDraft(
            person_tax_id=_UNKNOWN_PLACEHOLDER,
            finding_type=FindingType.MISSING_OWNER,
            severity=Severity.WARNING,
            computed_metrics={
                "parcels": int(len(orphans)),
                "total_m2": round(float(orphans["area_m2"].sum()), 2),
            },
            evidence=tuple(land_evidence(r) for _, r in orphans.iterrows()),
        )
    ]
