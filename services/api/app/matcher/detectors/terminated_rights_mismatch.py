"""Detector: DRRP right terminated, but same РНОКПП still active in land registry."""

from __future__ import annotations

from app.domain.enums import FindingType, Severity
from app.matcher.context import MatcherContext
from app.matcher.detectors._helpers import land_evidence, real_estate_evidence
from app.matcher.draft import FindingDraft


def detect_terminated_rights_mismatch(ctx: MatcherContext) -> list[FindingDraft]:
    if ctx.ner.empty or ctx.zem.empty:
        return []
    land = ctx.zem.dropna(subset=["owner_tax_id"])
    if land.empty:
        return []
    landowners = set(land["owner_tax_id"].unique())
    terminated = ctx.ner[
        ctx.ner["terminated_at"].notna() & ctx.ner["owner_tax_id"].isin(landowners)
    ]

    drafts: list[FindingDraft] = []
    for _, ner_row in terminated.iterrows():
        tid = ner_row["owner_tax_id"]
        parcels = land[land["owner_tax_id"] == tid]
        term_at = ner_row["terminated_at"]
        drafts.append(
            FindingDraft(
                person_tax_id=str(tid),
                finding_type=FindingType.TERMINATED_RIGHTS_MISMATCH,
                severity=Severity.WARNING,
                computed_metrics={
                    "drrp_termination_date": term_at.isoformat()
                    if hasattr(term_at, "isoformat")
                    else str(term_at),
                    "land_status": "active",
                },
                evidence=(
                    real_estate_evidence(ner_row),
                    *tuple(land_evidence(r) for _, r in parcels.iterrows()),
                ),
            )
        )
    return drafts
