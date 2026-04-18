"""Detector: same cadastral number registered under different tax_ids in ДЗК."""

from __future__ import annotations

from app.domain.enums import FindingType, Severity
from app.matcher.context import MatcherContext
from app.matcher.detectors._helpers import land_evidence
from app.matcher.draft import FindingDraft


def detect_duplicate_registration(ctx: MatcherContext) -> list[FindingDraft]:
    if ctx.zem.empty:
        return []

    z = ctx.zem.dropna(subset=["owner_tax_id"])
    if z.empty:
        return []

    dup = (
        z.groupby("cadastral_no")["owner_tax_id"]
        .nunique()
        .reset_index(name="distinct_owners")
    )
    duplicates = dup[dup["distinct_owners"] > 1]
    if duplicates.empty:
        return []

    drafts: list[FindingDraft] = []
    for _, row in duplicates.iterrows():
        cad = row["cadastral_no"]
        group = z[z["cadastral_no"] == cad]
        owners = sorted(str(v) for v in group["owner_tax_id"].unique())
        # Emit one finding per *primary* owner (the lexicographically-first one)
        primary_tid = owners[0]
        drafts.append(
            FindingDraft(
                person_tax_id=primary_tid,
                finding_type=FindingType.DUPLICATE_REGISTRATION,
                severity=Severity.CRITICAL,
                computed_metrics={
                    "cadastral_no": str(cad),
                    "distinct_owners": int(row["distinct_owners"]),
                    "owner_tax_ids": owners,
                },
                evidence=tuple(land_evidence(r) for _, r in group.iterrows()),
            )
        )
    return drafts
