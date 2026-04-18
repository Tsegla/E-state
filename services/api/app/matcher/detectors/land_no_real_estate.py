"""Detector: residential land owned, no residential real estate registered."""

from __future__ import annotations

import pandas as pd

from app.domain.enums import FindingType, Severity
from app.matcher.context import MatcherContext
from app.matcher.detectors._helpers import land_evidence
from app.matcher.draft import FindingDraft


def detect_land_no_real_estate(ctx: MatcherContext) -> list[FindingDraft]:
    cfg = ctx.config
    if ctx.zem.empty:
        return []

    residential_codes = set(cfg.residential_use_codes)
    residential_types = set(cfg.residential_object_types)

    land = ctx.zem[
        ctx.zem["intended_use_code"].isin(residential_codes)
        & ctx.zem["owner_tax_id"].notna()
    ]
    if land.empty:
        return []

    # For each tax_id in ctx.ner, which have an active residential object?
    if ctx.ner.empty:
        persons_with_residential: set[str] = set()
    else:
        active = ctx.ner[ctx.ner["terminated_at"].isna()]
        persons_with_residential = set(
            active[active["object_type_norm"].isin(residential_types)]["owner_tax_id"]
            .dropna()
            .unique()
        )

    drafts: list[FindingDraft] = []
    for tid, group in land.groupby("owner_tax_id"):
        if tid in persons_with_residential:
            continue
        total_m2 = float(group["area_m2"].sum())
        drafts.append(
            FindingDraft(
                person_tax_id=str(tid),
                finding_type=FindingType.LAND_NO_REAL_ESTATE,
                severity=Severity.WARNING,
                computed_metrics={
                    "residential_parcels": int(len(group)),
                    "total_residential_m2": round(total_m2, 2),
                },
                evidence=tuple(land_evidence(r) for _, r in group.iterrows()),
            )
        )
    return drafts
