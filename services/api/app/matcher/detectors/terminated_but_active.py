"""Detector: ДРРП records show ownership terminated, but ДЗК still shows active land."""

from __future__ import annotations

import pandas as pd

from app.domain.enums import FindingType, Severity
from app.matcher.context import MatcherContext
from app.matcher.detectors._helpers import land_evidence, real_estate_evidence
from app.matcher.draft import FindingDraft


def detect_terminated_but_active(ctx: MatcherContext) -> list[FindingDraft]:
    if ctx.ner.empty or ctx.zem.empty:
        return []

    terminated = ctx.ner[ctx.ner["terminated_at"].notna()]
    if terminated.empty:
        return []

    active_land = ctx.zem.dropna(subset=["owner_tax_id"])
    if active_land.empty:
        return []

    persons_with_land = set(active_land["owner_tax_id"].unique())
    # For each terminated record keep only persons still holding land
    grouped = terminated.groupby("owner_tax_id")

    drafts: list[FindingDraft] = []
    for tid, term_group in grouped:
        if tid not in persons_with_land:
            continue
        # Ensure the person has no *active* ДРРП record — otherwise ownership
        # simply changed, not a dangling reference
        active_for_tid = ctx.ner[(ctx.ner["owner_tax_id"] == tid) & ctx.ner["terminated_at"].isna()]
        if not active_for_tid.empty:
            continue
        parcels = active_land[active_land["owner_tax_id"] == tid]
        drafts.append(
            FindingDraft(
                person_tax_id=str(tid),
                finding_type=FindingType.TERMINATED_BUT_ACTIVE,
                severity=Severity.CRITICAL,
                computed_metrics={
                    "terminated_objects": int(len(term_group)),
                    "active_parcels": int(len(parcels)),
                    "last_termination_at": _latest_iso(term_group["terminated_at"]),
                },
                evidence=(
                    *tuple(real_estate_evidence(r) for _, r in term_group.iterrows()),
                    *tuple(land_evidence(r) for _, r in parcels.iterrows()),
                ),
            )
        )
    return drafts


def _latest_iso(series: pd.Series) -> str | None:
    cleaned = series.dropna()
    if cleaned.empty:
        return None
    latest = cleaned.max()
    return latest.isoformat() if hasattr(latest, "isoformat") else str(latest)
