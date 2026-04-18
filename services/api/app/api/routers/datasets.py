"""Dataset listing + summary."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import require_analyst, session_dep
from app.api.envelope import ApiResponse, Meta, ok
from app.api.schemas import DatasetSummaryDTO
from app.db.models import DatasetRow, FindingRow, LandParcelRow, RealEstateRow
from app.security.auth import Principal

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


def _summary(session: Session, row: DatasetRow) -> DatasetSummaryDTO:
    zem_n = session.query(func.count(LandParcelRow.id)).filter(LandParcelRow.dataset_id == row.id).scalar() or 0
    ner_n = session.query(func.count(RealEstateRow.id)).filter(RealEstateRow.dataset_id == row.id).scalar() or 0
    findings_n = session.query(func.count(FindingRow.id)).filter(FindingRow.dataset_id == row.id).scalar() or 0
    return DatasetSummaryDTO(
        id=row.id,
        label=row.label,
        uploaded_at=row.uploaded_at,
        uploaded_by=row.uploaded_by,
        status=row.status,
        zem_rows=int(zem_n),
        ner_rows=int(ner_n),
        findings_total=int(findings_n),
    )


@router.get("", response_model=ApiResponse[list[DatasetSummaryDTO]])
async def list_datasets(
    _: Principal = Depends(require_analyst),
    session: Session = Depends(session_dep),
) -> ApiResponse[list[DatasetSummaryDTO]]:
    rows = session.query(DatasetRow).order_by(DatasetRow.uploaded_at.desc()).all()
    items = [_summary(session, r) for r in rows]
    return ok(items, meta=Meta(total=len(items), page=1, limit=len(items) or 50))
