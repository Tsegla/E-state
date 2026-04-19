"""Subscription quote endpoints for OTG yearly plans."""

from __future__ import annotations

import shutil
import tempfile
import time
from collections import defaultdict, deque
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import require_analyst, session_dep
from app.api.envelope import ApiResponse, ok
from app.api.errors import NotFoundError, ValidationError
from app.api.schemas import SubscriptionQuoteDTO
from app.pricing.engine import quote_from_dataset, quote_from_file
from app.security.audit import log_action
from app.security.auth import Principal

router = APIRouter(prefix="/api/pricing", tags=["pricing"])
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 20
_RATE_LIMIT_BUCKETS: dict[str, deque[float]] = defaultdict(deque)


def _save_temp(upload: UploadFile, suffix: str) -> Path:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        shutil.copyfileobj(upload.file, tmp)
    finally:
        tmp.close()
    return Path(tmp.name)


def _sanitize_filename(filename: str) -> str:
    trimmed = Path(filename).name.strip()
    if not trimmed:
        return "unknown"
    return trimmed[:120]


def _enforce_rate_limit(client_ip: str) -> None:
    now = time.time()
    bucket = _RATE_LIMIT_BUCKETS[client_ip]
    while bucket and (now - bucket[0]) > RATE_LIMIT_WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= RATE_LIMIT_MAX_REQUESTS:
        raise ValidationError("Too many pricing requests. Please retry in one minute.")
    bucket.append(now)


@router.get("/quote", response_model=ApiResponse[SubscriptionQuoteDTO])
async def pricing_quote(
    dataset_id: UUID = Query(...),
    principal: Principal = Depends(require_analyst),
    session: Session = Depends(session_dep),
) -> ApiResponse[SubscriptionQuoteDTO]:
    try:
        quote = quote_from_dataset(session, dataset_id=dataset_id)
    except ValueError as exc:
        raise NotFoundError(f"Dataset {dataset_id} not found") from exc

    log_action(
        session,
        actor=principal.subject,
        action="view_subscription_quote",
        target_table="dataset",
        target_id=str(dataset_id),
        payload={"source": "dataset"},
    )
    session.commit()
    return ok(quote)


@router.post("/quote-upload", response_model=ApiResponse[SubscriptionQuoteDTO])
async def pricing_quote_upload(
    request: Request,
    file: UploadFile = File(..., description="Land register file: .xlsx/.xls/.csv"),
    session: Session = Depends(session_dep),
) -> ApiResponse[SubscriptionQuoteDTO]:
    if not file.filename:
        raise ValidationError("File is required")
    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".xlsx", ".xls", ".csv"}:
        raise ValidationError("Expected .xlsx, .xls or .csv file")

    client_ip = request.client.host if request.client else "unknown"
    _enforce_rate_limit(client_ip)

    temp_path = _save_temp(file, suffix)
    try:
        if temp_path.stat().st_size > MAX_UPLOAD_BYTES:
            raise ValidationError("File is too large. Maximum allowed size is 10MB.")
        quote = quote_from_file(temp_path)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
    finally:
        temp_path.unlink(missing_ok=True)

    log_action(
        session,
        actor="public_quote",
        action="view_subscription_quote",
        target_table="pricing",
        target_id="upload",
        payload={"source": "upload", "filename": _sanitize_filename(file.filename)},
    )
    session.commit()
    return ok(quote)
