"""Inspector mobile endpoints: list assigned findings + submit visits."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_inspector, session_dep
from app.api.envelope import ApiResponse, ok
from app.api.errors import NotFoundError
from app.api.schemas import FindingSummaryDTO, InspectorVisitCreate, InspectorVisitDTO
from app.db.models import FieldVisitRow, FindingRow
from app.security.auth import Principal
from app.security.audit import log_action
from app.security.pii import mask_tax_id
from uuid import UUID

router = APIRouter(prefix="/api/inspector", tags=["inspector"])


@router.get("/findings", response_model=ApiResponse[list[FindingSummaryDTO]])
async def assigned(
    dataset_id: UUID = Query(...),
    _: Principal = Depends(require_inspector),
    session: Session = Depends(session_dep),
) -> ApiResponse[list[FindingSummaryDTO]]:
    rows = (
        session.query(FindingRow)
        .filter(FindingRow.dataset_id == dataset_id, FindingRow.status.in_(["open", "in_review"]))
        .order_by(FindingRow.severity.asc(), FindingRow.detected_at.desc())
        .all()
    )
    return ok(
        [
            FindingSummaryDTO(
                id=r.id,
                dataset_id=r.dataset_id,
                person_tax_id_masked=mask_tax_id(r.person_tax_id),
                finding_type=r.finding_type,  # type: ignore[arg-type]
                severity=r.severity,  # type: ignore[arg-type]
                status=r.status,  # type: ignore[arg-type]
                computed_metrics=r.computed_metrics or {},
                detected_at=r.detected_at,
            )
            for r in rows
        ]
    )


@router.post("/visits", response_model=ApiResponse[InspectorVisitDTO])
async def create_visit(
    body: InspectorVisitCreate,
    principal: Principal = Depends(require_inspector),
    session: Session = Depends(session_dep),
) -> ApiResponse[InspectorVisitDTO]:
    finding = session.get(FindingRow, body.finding_id)
    if finding is None:
        raise NotFoundError(f"Finding {body.finding_id} not found")

    visit = FieldVisitRow(
        finding_id=body.finding_id,
        inspector_id=principal.subject,
        photo_refs=[dict(p) for p in body.photo_refs],
        actual_object_type=body.actual_object_type,
        actual_area_m2=body.actual_area_m2,
        actual_use=body.actual_use,
        notes=body.notes,
        gps=dict(body.gps) if body.gps else None,
    )
    session.add(visit)
    session.flush()
    finding.last_visit_id = visit.id
    finding.status = body.resolution.value

    log_action(
        session,
        actor=principal.subject,
        action="inspector_visit",
        target_table="finding",
        target_id=str(body.finding_id),
        payload={"resolution": body.resolution.value, "photos": len(body.photo_refs)},
    )
    session.commit()
    session.refresh(visit)

    return ok(
        InspectorVisitDTO(
            id=visit.id,
            finding_id=visit.finding_id,
            inspector_id=visit.inspector_id,
            actual_object_type=visit.actual_object_type,
            actual_area_m2=visit.actual_area_m2,
            actual_use=visit.actual_use,
            notes=visit.notes,
            gps=visit.gps,
            photo_refs=visit.photo_refs,
            created_at=visit.created_at,
        )
    )
