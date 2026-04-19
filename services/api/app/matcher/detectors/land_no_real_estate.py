"""Detector: residential land owned, no house (``житловий_будинок``) registered.

An apartment does *not* close a residential plot: the flat sits on OSBB land,
not on the owner's 02.01/02.03 plot, so the house that should stand on that
plot is still missing from ДРРП.
"""

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
    house_types = set(cfg.house_object_types)

    land = ctx.zem[
        ctx.zem["intended_use_code"].isin(residential_codes)
        & ctx.zem["owner_tax_id"].notna()
    ]
    if land.empty:
        return []

    # For each tax_id in ctx.ner, which have an active ``житловий_будинок``?
    if ctx.ner.empty:
        persons_with_house: set[str] = set()
    else:
        active = ctx.ner[ctx.ner["terminated_at"].isna()]
        persons_with_house = set(
            active[active["object_type_norm"].isin(house_types)]["owner_tax_id"]
            .dropna()
            .unique()
        )

    drafts: list[FindingDraft] = []
    for tid, group in land.groupby("owner_tax_id"):
        if tid in persons_with_house:
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
