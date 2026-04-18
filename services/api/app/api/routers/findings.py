"""Findings list + detail."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import require_analyst, session_dep
from app.api.envelope import ApiResponse, Meta, ok
from app.api.errors import NotFoundError
from app.api.schemas import FindingDetailDTO, FindingEvidenceDTO, FindingSummaryDTO
from app.db.models import FindingRow, PersonRow
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

    severity_order = {"critical": 0, "warning": 1, "info": 2}
    rows = (
        session.execute(
            stmt.order_by(FindingRow.severity.asc(), FindingRow.detected_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        .scalars()
        .all()
    )
    rows = sorted(rows, key=lambda r: (severity_order.get(r.severity, 99), -r.detected_at.timestamp()))
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
        session.query(FindingRow)
        .options(joinedload(FindingRow.evidence))
        .filter(FindingRow.id == finding_id)
        .unique()
        .one_or_none()
    )
    if row is None:
        raise NotFoundError(f"Finding {finding_id} not found")
    person = session.get(PersonRow, row.person_tax_id)
    detail = FindingDetailDTO(
        id=row.id,
        dataset_id=row.dataset_id,
        person_tax_id_masked=mask_tax_id(row.person_tax_id),
        person_name_masked=mask_name(person.full_name_raw if person else ""),
        finding_type=row.finding_type,  # type: ignore[arg-type]
        severity=row.severity,  # type: ignore[arg-type]
        status=row.status,  # type: ignore[arg-type]
        computed_metrics=row.computed_metrics or {},
        detected_at=row.detected_at,
        evidence=[
            FindingEvidenceDTO(kind=e.kind, ref_id=e.ref_id, snapshot=e.snapshot or {})
            for e in row.evidence
        ],
    )
    return ok(detail)
