"""Detector: intended-use vs object-type mismatch (residential/commercial/industrial)."""

from __future__ import annotations

import pandas as pd

from app.domain.enums import FindingType, Severity
from app.matcher.context import MatcherContext
from app.matcher.detectors._helpers import land_evidence, real_estate_evidence
from app.matcher.draft import FindingDraft


def _categorize_use(code: str | None, cfg) -> str | None:
    if not code:
        return None
    if code in cfg.residential_use_codes:
        return "residential"
    if code in cfg.commercial_use_codes:
        return "commercial"
    if code in cfg.industrial_use_codes:
        return "industrial"
    if code in cfg.agri_use_codes:
        return "agricultural"
    return None


def _categorize_object(norm: str | None, cfg) -> str | None:
    if not norm:
        return None
    if norm in cfg.residential_object_types:
        return "residential"
    if norm in cfg.commercial_object_types:
        return "commercial"
    if norm in cfg.industrial_object_types:
        return "industrial"
    return None


def detect_use_vs_object_mismatch(ctx: MatcherContext) -> list[FindingDraft]:
    cfg = ctx.config
    if ctx.zem.empty or ctx.ner.empty:
        return []

    active_ner = ctx.ner[ctx.ner["terminated_at"].isna()].copy()
    active_ner["_category"] = active_ner["object_type_norm"].apply(lambda v: _categorize_object(v, cfg))
    zem = ctx.zem.copy()
    zem["_category"] = zem["intended_use_code"].apply(lambda v: _categorize_use(v, cfg))

    drafts: list[FindingDraft] = []
    for tid in set(zem["owner_tax_id"].dropna().unique()).intersection(
        set(active_ner["owner_tax_id"].dropna().unique())
    ):
        land_cats = set(zem[zem["owner_tax_id"] == tid]["_category"].dropna())
        obj_cats = set(active_ner[active_ner["owner_tax_id"] == tid]["_category"].dropna())
        if not land_cats or not obj_cats:
            continue
        mismatched = (land_cats | obj_cats) - (land_cats & obj_cats)
        # Only flag when the sets diverge and nothing aligns.
        if land_cats.isdisjoint(obj_cats) and mismatched:
            parcels = zem[zem["owner_tax_id"] == tid]
            objects = active_ner[active_ner["owner_tax_id"] == tid]
            drafts.append(
                FindingDraft(
                    person_tax_id=str(tid),
                    finding_type=FindingType.USE_VS_OBJECT_MISMATCH,
                    severity=Severity.WARNING,
                    computed_metrics={
                        "land_categories": sorted(land_cats),
                        "object_categories": sorted(obj_cats),
                    },
                    evidence=(
                        *tuple(land_evidence(r) for _, r in parcels.iterrows()),
                        *tuple(real_estate_evidence(r) for _, r in objects.iterrows()),
                    ),
                )
            )
    return drafts
