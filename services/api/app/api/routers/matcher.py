"""Kick off the matcher engine for a dataset."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_analyst, session_dep
from app.api.envelope import ApiResponse, ok
from app.api.errors import NotFoundError
from app.api.schemas import MatcherRunRequest, MatcherRunResponse
from app.db.models import DatasetRow
from app.matcher.engine import run as run_matcher
from app.security.audit import log_action
from app.security.auth import Principal

router = APIRouter(prefix="/api/matcher", tags=["matcher"])


@router.post("/run", response_model=ApiResponse[MatcherRunResponse])
async def run(
    body: MatcherRunRequest,
    principal: Principal = Depends(require_analyst),
    session: Session = Depends(session_dep),
) -> ApiResponse[MatcherRunResponse]:
    dataset = session.get(DatasetRow, body.dataset_id)
    if dataset is None:
        raise NotFoundError(f"Dataset {body.dataset_id} not found")
    result = run_matcher(session, body.dataset_id)
    dataset.status = "matched"
    log_action(
        session,
        actor=principal.subject,
        action="matcher_run",
        target_table="dataset",
        target_id=str(body.dataset_id),
        payload={"findings_created": result.findings_created},
    )
    session.commit()
    return ok(
        MatcherRunResponse(
            dataset_id=result.dataset_id,
            findings_created=result.findings_created,
            by_type=result.by_type,
            by_severity=result.by_severity,
            duration_ms=result.duration_ms,
        )
    )
