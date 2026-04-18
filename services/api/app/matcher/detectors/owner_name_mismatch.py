"""Detector: same tax_id, substantially different owner names across registries."""

from __future__ import annotations

import pandas as pd
from rapidfuzz import fuzz

from app.domain.enums import FindingType, Severity
from app.ingest.normalize import normalize_name
from app.matcher.context import MatcherContext
from app.matcher.detectors._helpers import land_evidence, real_estate_evidence
from app.matcher.draft import FindingDraft


def detect_owner_name_mismatch(ctx: MatcherContext) -> list[FindingDraft]:
    cfg = ctx.config
    if ctx.ner.empty or ctx.zem.empty:
        return []

    zem_names = (
        ctx.zem.dropna(subset=["owner_tax_id"])
        .groupby("owner_tax_id")["owner_name_raw"]
        .first()
        .apply(normalize_name)
    )
    ner_names = (
        ctx.ner.dropna(subset=["owner_tax_id"])
        .groupby("owner_tax_id")["owner_name_raw"]
        .first()
        .apply(normalize_name)
    )

    drafts: list[FindingDraft] = []
    for tid in set(zem_names.index).intersection(ner_names.index):
        a = zem_names.loc[tid]
        b = ner_names.loc[tid]
        if not a or not b:
            continue
        score = fuzz.token_set_ratio(a, b) / 100.0
        if score >= cfg.owner_name_mismatch_max:
            continue
        parcels = ctx.zem[ctx.zem["owner_tax_id"] == tid]
        objects = ctx.ner[ctx.ner["owner_tax_id"] == tid]
        drafts.append(
            FindingDraft(
                person_tax_id=str(tid),
                finding_type=FindingType.OWNER_NAME_MISMATCH,
                severity=Severity.INFO,
                computed_metrics={
                    "zem_name": str(parcels.iloc[0]["owner_name_raw"] or ""),
                    "ner_name": str(objects.iloc[0]["owner_name_raw"] or ""),
                    "similarity": round(score, 3),
                },
                evidence=(
                    land_evidence(parcels.iloc[0]),
                    real_estate_evidence(objects.iloc[0]),
                ),
            )
        )
    return drafts
