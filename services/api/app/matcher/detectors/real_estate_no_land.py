"""Detector: residential real estate owned, no land in ДЗК."""

from __future__ import annotations

from app.domain.enums import FindingType, Severity
from app.matcher.context import MatcherContext
from app.matcher.detectors._helpers import real_estate_evidence
from app.matcher.draft import FindingDraft


def detect_real_estate_no_land(ctx: MatcherContext) -> list[FindingDraft]:
    cfg = ctx.config
    if ctx.ner.empty:
        return []

    residential_types = set(cfg.residential_object_types)
    active = ctx.ner[ctx.ner["terminated_at"].isna() & ctx.ner["object_type_norm"].isin(residential_types)]
    if active.empty:
        return []

    persons_with_land = set(
        ctx.zem["owner_tax_id"].dropna().unique().tolist() if not ctx.zem.empty else []
    )

    drafts: list[FindingDraft] = []
    for tid, group in active.groupby("owner_tax_id"):
        if tid in persons_with_land:
            continue
        drafts.append(
            FindingDraft(
                person_tax_id=str(tid),
                finding_type=FindingType.REAL_ESTATE_NO_LAND,
                severity=Severity.WARNING,
                computed_metrics={
                    "residential_objects": int(len(group)),
                    "total_residential_m2": round(float(group["area_m2"].sum()), 2),
                },
                evidence=tuple(real_estate_evidence(r) for _, r in group.iterrows()),
            )
        )
    return drafts
