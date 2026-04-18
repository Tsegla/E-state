"""Budget impact and aggregate reports."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_analyst, session_dep
from app.api.envelope import ApiResponse, ok
from app.api.schemas import BudgetImpactDTO
from app.db.models import FindingRow
from app.domain.enums import FindingType
from app.matcher.config import default_config
from app.security.auth import Principal

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/budget-impact", response_model=ApiResponse[BudgetImpactDTO])
async def budget_impact(
    dataset_id: UUID = Query(...),
    _: Principal = Depends(require_analyst),
    session: Session = Depends(session_dep),
) -> ApiResponse[BudgetImpactDTO]:
    cfg = default_config()
    rows = (
        session.query(FindingRow)
        .filter(FindingRow.dataset_id == dataset_id, FindingRow.status.in_(["open", "in_review"]))
        .all()
    )

    by_type: dict[str, float] = {}
    total = 0.0
    for r in rows:
        amount = 0.0
        metrics = r.computed_metrics or {}
        if r.finding_type == FindingType.LAND_NO_REAL_ESTATE.value:
            m2 = float(metrics.get("total_residential_m2") or 0.0)
            amount = m2 * cfg.housing_rate_uah_per_m2_per_year
        elif r.finding_type == FindingType.AREA_PORTFOLIO_DELTA.value:
            delta = float(metrics.get("delta_m2") or 0.0)
            amount = max(delta, 0.0) * cfg.commercial_rate_uah_per_m2_per_year
        elif r.finding_type == FindingType.MISSING_OWNER.value:
            m2 = float(metrics.get("total_m2") or 0.0)
            amount = m2 * cfg.agri_rate_uah_per_m2_per_year
        else:
            continue
        by_type[r.finding_type] = by_type.get(r.finding_type, 0.0) + amount
        total += amount

    return ok(BudgetImpactDTO(total_uah_per_year=round(total, 2), by_type={k: round(v, 2) for k, v in by_type.items()}))
