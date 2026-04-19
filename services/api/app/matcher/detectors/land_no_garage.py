"""Detector: garage land owned (intended-use 02.05), no garage registered.

Mirrors :mod:`land_no_real_estate` but for the ``garage_use_codes``/
``garage_object_types`` taxonomy. Flags when a person holds at least one
``02.05`` parcel and has no active ``гараж`` object in ДРРП.
"""

from __future__ import annotations

from app.domain.enums import FindingType, Severity
from app.matcher.context import MatcherContext
from app.matcher.detectors._helpers import land_evidence
from app.matcher.draft import FindingDraft


def detect_land_no_garage(ctx: MatcherContext) -> list[FindingDraft]:
    cfg = ctx.config
    if ctx.zem.empty:
        return []

    garage_codes = set(cfg.garage_use_codes)
    garage_types = set(cfg.garage_object_types)

    land = ctx.zem[
        ctx.zem["intended_use_code"].isin(garage_codes)
        & ctx.zem["owner_tax_id"].notna()
    ]
    if land.empty:
        return []

    if ctx.ner.empty:
        persons_with_garage: set[str] = set()
    else:
        active = ctx.ner[ctx.ner["terminated_at"].isna()]
        persons_with_garage = set(
            active[active["object_type_norm"].isin(garage_types)]["owner_tax_id"]
            .dropna()
            .unique()
        )

    drafts: list[FindingDraft] = []
    for tid, group in land.groupby("owner_tax_id"):
        if tid in persons_with_garage:
            continue
        total_m2 = float(group["area_m2"].sum())
        drafts.append(
            FindingDraft(
                person_tax_id=str(tid),
                finding_type=FindingType.LAND_NO_GARAGE,
                severity=Severity.WARNING,
                computed_metrics={
                    "garage_parcels": int(len(group)),
                    "total_garage_m2": round(total_m2, 2),
                },
                evidence=tuple(land_evidence(r) for _, r in group.iterrows()),
            )
        )
    return drafts
