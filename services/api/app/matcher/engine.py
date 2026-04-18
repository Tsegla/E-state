"""Matcher orchestration: load → run detectors → persist findings.

Runs are idempotent: the existing findings for a dataset are deleted before
new ones are written, so rerunning yields the same output modulo config
changes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from time import perf_counter
from uuid import UUID

import pandas as pd
from sqlalchemy.orm import Session

from app.db.models import (
    FindingEvidenceRow,
    FindingRow,
    LandParcelRow,
    PersonRow,
    RealEstateRow,
)
from app.matcher.config import MatcherConfig, default_config
from app.matcher.context import MatcherContext
from app.matcher.detectors import REGISTRY
from app.matcher.draft import FindingDraft

_LOG = logging.getLogger("e_state.matcher")


@dataclass(frozen=True, slots=True)
class MatcherResult:
    dataset_id: UUID
    findings_created: int
    by_type: dict[str, int]
    by_severity: dict[str, int]
    duration_ms: int


def _load_zem(session: Session, dataset_id: UUID) -> pd.DataFrame:
    rows = (
        session.query(LandParcelRow)
        .filter(LandParcelRow.dataset_id == dataset_id)
        .all()
    )
    if not rows:
        return pd.DataFrame(
            columns=[
                "id",
                "cadastral_no",
                "owner_tax_id",
                "owner_name_raw",
                "intended_use_code",
                "intended_use_label",
                "area_m2",
                "location_admin",
            ]
        )
    return pd.DataFrame(
        [
            {
                "id": r.id,
                "cadastral_no": r.cadastral_no,
                "owner_tax_id": r.owner_tax_id,
                "owner_name_raw": r.owner_name_raw,
                "intended_use_code": r.intended_use_code,
                "intended_use_label": r.intended_use_label,
                "area_m2": float(r.area_m2 or 0.0),
                "location_admin": r.location_admin,
            }
            for r in rows
        ]
    )


def _load_ner(session: Session, dataset_id: UUID) -> pd.DataFrame:
    rows = (
        session.query(RealEstateRow)
        .filter(RealEstateRow.dataset_id == dataset_id)
        .all()
    )
    if not rows:
        return pd.DataFrame(
            columns=[
                "id",
                "owner_tax_id",
                "owner_name_raw",
                "object_type_raw",
                "object_type_norm",
                "address_raw",
                "area_m2",
                "terminated_at",
            ]
        )
    return pd.DataFrame(
        [
            {
                "id": r.id,
                "owner_tax_id": r.owner_tax_id,
                "owner_name_raw": r.owner_name_raw,
                "object_type_raw": r.object_type_raw,
                "object_type_norm": r.object_type_norm,
                "address_raw": r.address_raw,
                "area_m2": float(r.area_m2 or 0.0),
                "terminated_at": pd.to_datetime(r.terminated_at) if r.terminated_at else pd.NaT,
            }
            for r in rows
        ]
    )


def _load_persons(session: Session) -> pd.DataFrame:
    rows = session.query(PersonRow).all()
    return pd.DataFrame(
        [
            {
                "tax_id": r.tax_id,
                "full_name_raw": r.full_name_raw,
                "full_name_norm": r.full_name_norm,
            }
            for r in rows
        ]
    ) if rows else pd.DataFrame(columns=["tax_id", "full_name_raw", "full_name_norm"])


def _delete_existing(session: Session, dataset_id: UUID) -> None:
    existing = session.query(FindingRow).filter(FindingRow.dataset_id == dataset_id).all()
    for row in existing:
        session.delete(row)
    session.flush()


def _persist(session: Session, dataset_id: UUID, draft: FindingDraft) -> None:
    row = FindingRow(
        dataset_id=dataset_id,
        person_tax_id=draft.person_tax_id,
        finding_type=draft.finding_type.value,
        severity=draft.severity.value,
        computed_metrics=dict(draft.computed_metrics),
    )
    for ev in draft.evidence:
        row.evidence.append(
            FindingEvidenceRow(kind=ev.kind, ref_id=ev.ref_id, snapshot=dict(ev.snapshot))
        )
    session.add(row)


def run(
    session: Session,
    dataset_id: UUID,
    *,
    config: MatcherConfig | None = None,
) -> MatcherResult:
    """Run all enabled detectors for a dataset and persist findings."""
    cfg = config or default_config()
    started = perf_counter()
    ctx = MatcherContext(
        dataset_id=dataset_id,
        zem=_load_zem(session, dataset_id),
        ner=_load_ner(session, dataset_id),
        persons=_load_persons(session),
        config=cfg,
    )
    _LOG.info(
        "matcher.start dataset=%s zem=%d ner=%d", dataset_id, len(ctx.zem), len(ctx.ner)
    )
    _delete_existing(session, dataset_id)

    by_type: dict[str, int] = {}
    by_sev: dict[str, int] = {}
    total = 0
    for name in cfg.enabled_detectors:
        fn = REGISTRY.get(name)
        if fn is None:
            _LOG.warning("Unknown detector %s in config; skipping", name)
            continue
        drafts = fn(ctx)
        for d in drafts:
            _persist(session, dataset_id, d)
            by_type[name] = by_type.get(name, 0) + 1
            by_sev[d.severity.value] = by_sev.get(d.severity.value, 0) + 1
            total += 1
    session.flush()

    duration_ms = int((perf_counter() - started) * 1000)
    _LOG.info(
        "matcher.done dataset=%s findings=%d duration_ms=%d", dataset_id, total, duration_ms
    )
    return MatcherResult(
        dataset_id=dataset_id,
        findings_created=total,
        by_type=by_type,
        by_severity=by_sev,
        duration_ms=duration_ms,
    )
