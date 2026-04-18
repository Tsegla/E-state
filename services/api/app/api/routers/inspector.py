"""Inspector mobile endpoints: list assigned findings, fetch detail, submit visits.

Submitting a visit upserts a row in ``verified_asset`` — the canonical
"main table" that downstream surfaces read as ground truth.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import require_inspector, session_dep
from app.api.envelope import ApiResponse, ok
from app.api.errors import NotFoundError, ValidationError
from app.api.schemas import (
    FindingDetailDTO,
    FindingEvidenceDTO,
    FindingSummaryDTO,
    InspectorVisitCreate,
    InspectorVisitDTO,
    VerifiedAssetDTO,
)
from app.db.models import (
    FieldVisitRow,
    FindingEvidenceRow,
    FindingRow,
    PersonRow,
    VerifiedAssetRow,
)
from app.security.auth import Principal
from app.security.audit import log_action
from app.security.pii import mask_name, mask_tax_id

router = APIRouter(prefix="/api/inspector", tags=["inspector"])


@router.get("/findings", response_model=ApiResponse[list[FindingSummaryDTO]])
async def assigned(
    dataset_id: UUID = Query(...),
    _: Principal = Depends(require_inspector),
    session: Session = Depends(session_dep),
) -> ApiResponse[list[FindingSummaryDTO]]:
    # Inspector queue = findings explicitly handed off by an analyst
    # (assigned_at is set when status transitions open -> in_review).
    # Without this filter the queue would drown the assigned item in
    # thousands of unassigned "open" findings for the same dataset.
    rows = (
        session.query(FindingRow)
        .filter(
            FindingRow.dataset_id == dataset_id,
            FindingRow.status == "in_review",
            FindingRow.assigned_at.isnot(None),
        )
        .order_by(FindingRow.assigned_at.desc())
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


@router.get("/findings/{finding_id}", response_model=ApiResponse[FindingDetailDTO])
async def assigned_detail(
    finding_id: UUID,
    _: Principal = Depends(require_inspector),
    session: Session = Depends(session_dep),
) -> ApiResponse[FindingDetailDTO]:
    """Inspector-scoped finding detail with full evidence snapshots.

    Only open or in_review findings are visible on mobile — resolved ones
    have no further work.
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
    if row is None or row.status not in ("open", "in_review"):
        raise NotFoundError(f"Finding {finding_id} not found")
    person = session.get(PersonRow, row.person_tax_id)
    return ok(
        FindingDetailDTO(
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
            assignment_note=row.assignment_note,
            assigned_at=row.assigned_at,
        )
    )


def _resolve_truth_fields(
    body: InspectorVisitCreate, evidence: FindingEvidenceRow | None
) -> dict[str, str | float | None]:
    """Pick the fields that land in verified_asset based on source_of_truth."""
    if body.source_of_truth == "field_override" or evidence is None:
        return {
            "object_type": body.actual_object_type,
            "area_m2": body.actual_area_m2,
            "use": body.actual_use,
            "address": None,
        }
    snapshot = evidence.snapshot or {}
    if evidence.kind == "land_parcel":
        return {
            "object_type": snapshot.get("intended_use_label")
            or snapshot.get("intended_use_code"),
            "area_m2": _to_float(snapshot.get("area_m2")),
            "use": snapshot.get("agri_use_kind") or snapshot.get("intended_use_label"),
            "address": snapshot.get("location_admin"),
        }
    return {
        "object_type": snapshot.get("object_type_raw") or snapshot.get("object_type_norm"),
        "area_m2": _to_float(snapshot.get("area_m2")),
        "use": snapshot.get("object_type_norm") or snapshot.get("object_type_raw"),
        "address": snapshot.get("address_raw") or snapshot.get("address_norm"),
    }


def _to_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _upsert_verified_asset(
    session: Session,
    *,
    finding: FindingRow,
    visit: FieldVisitRow,
    evidence: FindingEvidenceRow | None,
    body: InspectorVisitCreate,
) -> VerifiedAssetRow:
    source = body.source_of_truth or "field_override"
    truth = _resolve_truth_fields(body, evidence)

    existing = (
        session.query(VerifiedAssetRow)
        .filter(VerifiedAssetRow.finding_id == finding.id)
        .one_or_none()
    )
    if existing is None:
        existing = VerifiedAssetRow(
            finding_id=finding.id,
            dataset_id=finding.dataset_id,
            person_tax_id=finding.person_tax_id,
            verified_by=visit.inspector_id,
        )
        session.add(existing)

    existing.source_of_truth = source
    existing.chosen_ref_kind = evidence.kind if evidence else None
    existing.chosen_ref_id = evidence.ref_id if evidence else None
    existing.object_type = truth["object_type"]  # type: ignore[assignment]
    existing.area_m2 = truth["area_m2"]  # type: ignore[assignment]
    existing.use = truth["use"]  # type: ignore[assignment]
    existing.address = truth["address"]  # type: ignore[assignment]
    existing.verified_by = visit.inspector_id
    return existing


def _verified_asset_dto(row: VerifiedAssetRow) -> VerifiedAssetDTO:
    return VerifiedAssetDTO(
        id=row.id,
        finding_id=row.finding_id,
        dataset_id=row.dataset_id,
        person_tax_id_masked=mask_tax_id(row.person_tax_id),
        source_of_truth=row.source_of_truth,  # type: ignore[arg-type]
        chosen_ref_kind=row.chosen_ref_kind,
        chosen_ref_id=row.chosen_ref_id,
        object_type=row.object_type,
        area_m2=row.area_m2,
        use=row.use,
        address=row.address,
        verified_by=row.verified_by,
        verified_at=row.verified_at,
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

    evidence: FindingEvidenceRow | None = None
    if body.source_of_truth in ("dzk", "drrp"):
        if body.truth_evidence_id is None:
            raise ValidationError(
                "truth_evidence_id is required when source_of_truth is dzk or drrp"
            )
        evidence = session.get(FindingEvidenceRow, body.truth_evidence_id)
        if evidence is None or evidence.finding_id != finding.id:
            raise ValidationError("truth_evidence_id does not belong to this finding")
        expected_kind = "land_parcel" if body.source_of_truth == "dzk" else "real_estate"
        if evidence.kind != expected_kind:
            raise ValidationError(
                f"Evidence kind '{evidence.kind}' does not match source_of_truth "
                f"'{body.source_of_truth}' (expected '{expected_kind}')"
            )

    visit = FieldVisitRow(
        finding_id=body.finding_id,
        inspector_id=principal.subject,
        photo_refs=[dict(p) for p in body.photo_refs],
        actual_object_type=body.actual_object_type,
        actual_area_m2=body.actual_area_m2,
        actual_use=body.actual_use,
        notes=body.notes,
        gps=dict(body.gps) if body.gps else None,
        source_of_truth=body.source_of_truth,
        truth_evidence_id=body.truth_evidence_id,
    )
    session.add(visit)
    session.flush()
    finding.last_visit_id = visit.id
    finding.status = body.resolution.value

    verified: VerifiedAssetRow | None = None
    if body.resolution.value == "resolved":
        verified = _upsert_verified_asset(
            session, finding=finding, visit=visit, evidence=evidence, body=body
        )
        session.flush()

    log_action(
        session,
        actor=principal.subject,
        action="inspector_visit",
        target_table="finding",
        target_id=str(body.finding_id),
        payload={
            "resolution": body.resolution.value,
            "photos": len(body.photo_refs),
            "source_of_truth": body.source_of_truth,
        },
    )
    if verified is not None:
        log_action(
            session,
            actor=principal.subject,
            action="verify_truth",
            target_table="verified_asset",
            target_id=str(verified.id),
            payload={
                "source_of_truth": verified.source_of_truth,
                "chosen_ref_kind": verified.chosen_ref_kind,
            },
        )
    session.commit()
    session.refresh(visit)
    if verified is not None:
        session.refresh(verified)

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
            source_of_truth=visit.source_of_truth,  # type: ignore[arg-type]
            truth_evidence_id=visit.truth_evidence_id,
            verified_asset=_verified_asset_dto(verified) if verified else None,
            created_at=visit.created_at,
        )
    )
