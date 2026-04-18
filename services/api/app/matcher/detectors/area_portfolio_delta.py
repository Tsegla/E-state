"""Detector: built-up real-estate area materially exceeds allocated land area.

Signals potential self-built structures outside of registered land use.
"""

from __future__ import annotations

from app.domain.enums import FindingType, Severity
from app.matcher.context import MatcherContext
from app.matcher.detectors._helpers import land_evidence, real_estate_evidence
from app.matcher.draft import FindingDraft


def detect_area_portfolio_delta(ctx: MatcherContext) -> list[FindingDraft]:
    cfg = ctx.config
    if ctx.ner.empty or ctx.zem.empty:
        return []

    active_ner = ctx.ner[ctx.ner["terminated_at"].isna()].copy()
    if active_ner.empty:
        return []

    ner_by_owner = active_ner.groupby("owner_tax_id")["area_m2"].sum().to_dict()
    zem_by_owner = ctx.zem.groupby("owner_tax_id")["area_m2"].sum().to_dict()

    drafts: list[FindingDraft] = []
    for tid, ner_m2 in ner_by_owner.items():
        if tid is None:
            continue
        zem_m2 = float(zem_by_owner.get(tid, 0.0))
        ner_m2 = float(ner_m2)
        if zem_m2 <= 0:
            continue
        ratio = ner_m2 / zem_m2
        if ratio < cfg.area_portfolio_ratio_warning:
            continue
        severity = (
            Severity.CRITICAL if ratio >= cfg.area_portfolio_ratio_critical else Severity.WARNING
        )
        parcels = ctx.zem[ctx.zem["owner_tax_id"] == tid]
        objects = active_ner[active_ner["owner_tax_id"] == tid]
        drafts.append(
            FindingDraft(
                person_tax_id=str(tid),
                finding_type=FindingType.AREA_PORTFOLIO_DELTA,
                severity=severity,
                computed_metrics={
                    "zem_m2": round(zem_m2, 2),
                    "ner_m2": round(ner_m2, 2),
                    "ratio": round(ratio, 3),
                    "delta_m2": round(ner_m2 - zem_m2, 2),
                },
                evidence=(
                    *tuple(land_evidence(r) for _, r in parcels.iterrows()),
                    *tuple(real_estate_evidence(r) for _, r in objects.iterrows()),
                ),
            )
        )
    return drafts
