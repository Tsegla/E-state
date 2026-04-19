"""Detector: DRRP right terminated, but same РНОКПП still active in land registry.

Emits **one finding per owner**, not per terminated row. The previous
per-row version produced many duplicate findings for a single person whose
terminated real-estate portfolio is large (e.g. several sold flats), so
inspectors had to triage the same case multiple times.
"""

from __future__ import annotations

import pandas as pd

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
    if terminated.empty:
        return []

    drafts: list[FindingDraft] = []
    for tid, term_group in terminated.groupby("owner_tax_id"):
        parcels = land[land["owner_tax_id"] == tid]
        last_term = _latest_iso(term_group["terminated_at"])
        drafts.append(
            FindingDraft(
                person_tax_id=str(tid),
                finding_type=FindingType.TERMINATED_RIGHTS_MISMATCH,
                severity=Severity.WARNING,
                computed_metrics={
                    "terminated_count": int(len(term_group)),
                    "last_termination_at": last_term,
                    "land_status": "active",
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
