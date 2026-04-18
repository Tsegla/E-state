"""Findings list + detail + analyst actions (assign to inspector)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import require_analyst, session_dep
from app.api.envelope import ApiResponse, Meta, ok
from app.api.errors import ConflictError, NotFoundError
from app.api.schemas import (
    AssignInspectorRequest,
    FindingDetailDTO,
    FindingEvidenceDTO,
    FindingSummaryDTO,
)
from app.db.models import FindingRow, PersonRow
from app.domain.enums import FindingStatus
from app.security.audit import log_action
from app.security.auth import Principal
from app.security.pii import mask_name, mask_tax_id

router = APIRouter(prefix="/api/findings", tags=["findings"])


def _to_summary(row: FindingRow) -> FindingSummaryDTO:
    return FindingSummaryDTO(
        id=row.id,
        dataset_id=row.dataset_id,
        person_tax_id_masked=mask_tax_id(row.person_tax_id),
        finding_type=row.finding_type,  # type: ignore[arg-type]
        severity=row.severity,  # type: ignore[arg-type]
        status=row.status,  # type: ignore[arg-type]
        computed_metrics=row.computed_metrics or {},
        detected_at=row.detected_at,
    )


@router.get("", response_model=ApiResponse[list[FindingSummaryDTO]])
async def list_findings(
    dataset_id: UUID = Query(...),
    severity: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    finding_type: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    _: Principal = Depends(require_analyst),
    session: Session = Depends(session_dep),
) -> ApiResponse[list[FindingSummaryDTO]]:
    stmt = select(FindingRow).where(FindingRow.dataset_id == dataset_id)
    count_stmt = select(func.count(FindingRow.id)).where(FindingRow.dataset_id == dataset_id)
    if severity:
        stmt = stmt.where(FindingRow.severity == severity)
        count_stmt = count_stmt.where(FindingRow.severity == severity)
    if status_filter:
        stmt = stmt.where(FindingRow.status == status_filter)
        count_stmt = count_stmt.where(FindingRow.status == status_filter)
    if finding_type:
        stmt = stmt.where(FindingRow.finding_type == finding_type)
        count_stmt = count_stmt.where(FindingRow.finding_type == finding_type)

    severity_rank = case(
        (FindingRow.severity == "critical", 0),
        (FindingRow.severity == "warning", 1),
        (FindingRow.severity == "info", 2),
        else_=99,
    )
    rows = (
        session.execute(
            stmt.order_by(severity_rank.asc(), FindingRow.detected_at.desc())
            .order_by(FindingRow.id.asc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        .scalars()
        .all()
    )
    total = int(session.execute(count_stmt).scalar_one())
    items = [_to_summary(r) for r in rows]
    return ok(items, meta=Meta(total=total, page=page, limit=limit))


@router.get("/{finding_id}", response_model=ApiResponse[FindingDetailDTO])
async def get_finding(
    finding_id: UUID,
    _: Principal = Depends(require_analyst),
    session: Session = Depends(session_dep),
) -> ApiResponse[FindingDetailDTO]:
    row = (
        session.execute(
            select(FindingRow)
            .options(joinedload(FindingRow.evidence))
            .where(FindingRow.id == finding_id)
        )
        .unique()
        .scalar_one_or_none()
    )
    if row is None:
        raise NotFoundError(f"Finding {finding_id} not found")
    person = session.get(PersonRow, row.person_tax_id)
    detail = _to_detail(row, person_name=person.full_name_raw if person else "")
    return ok(detail)


def _to_detail(row: FindingRow, *, person_name: str) -> FindingDetailDTO:
    return FindingDetailDTO(
        id=row.id,
        dataset_id=row.dataset_id,
        person_tax_id_masked=mask_tax_id(row.person_tax_id),
        person_name_masked=mask_name(person_name),
        finding_type=row.finding_type,  # type: ignore[arg-type]
        severity=row.severity,  # type: ignore[arg-type]
        status=row.status,  # type: ignore[arg-type]
        computed_metrics=row.computed_metrics or {},
        detected_at=row.detected_at,
        evidence=[
            FindingEvidenceDTO(id=e.id, kind=e.kind, ref_id=e.ref_id, snapshot=e.snapshot or {})
            for e in row.evidence
        ],
        assignment_note=row.assignment_note,
        assigned_at=row.assigned_at,
    )


@router.post("/{finding_id}/assign", response_model=ApiResponse[FindingDetailDTO])
async def assign_to_inspector(
    finding_id: UUID,
    body: AssignInspectorRequest,
    principal: Principal = Depends(require_analyst),
    session: Session = Depends(session_dep),
) -> ApiResponse[FindingDetailDTO]:
    """Analyst hands off a finding for field inspection.

    Transitions status ``open -> in_review`` and stores the free-text note on
    the finding itself (audit_log only persists hashes, so the inspector would
    not be able to read it from there).
    """
    row = (
        session.execute(
            select(FindingRow)
            .options(joinedload(FindingRow.evidence))
            .where(FindingRow.id == finding_id)
        )
        .unique()
        .scalar_one_or_none()
    )
    if row is None:
        raise NotFoundError(f"Finding {finding_id} not found")
    if row.status != FindingStatus.OPEN.value:
        raise ConflictError(
            f"Finding is already {row.status}; can only assign from 'open'",
            details={"current_status": row.status},
        )

    row.status = FindingStatus.IN_REVIEW.value
    row.assignment_note = body.note
    row.assigned_at = datetime.now(tz=timezone.utc)

    log_action(
        session,
        actor=principal.subject,
        action="assign_inspector",
        target_table="finding",
        target_id=str(finding_id),
        payload={"has_note": bool(body.note)},
    )
    session.commit()
    session.refresh(row)

    person = session.get(PersonRow, row.person_tax_id)
    return ok(_to_detail(row, person_name=person.full_name_raw if person else ""))
