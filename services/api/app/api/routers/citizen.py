"""Citizen portal: RNOKPP lookup with CAPTCHA + rate limit + audit log."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import session_dep
from app.api.envelope import ApiResponse, ok
from app.api.errors import RateLimitError, ValidationError
from app.api.schemas import CitizenAssetDTO, CitizenLookupRequest, CitizenLookupResponse
from app.config import get_settings
from app.db.models import DatasetRow, FindingRow, LandParcelRow, PersonRow, RealEstateRow
from app.ingest.normalize import normalize_tax_id
from app.security.audit import log_action
from app.security.pii import mask_name

router = APIRouter(prefix="/api/citizen", tags=["citizen"])

_RATE_WINDOW_SECS = 15 * 60
_IP_TIMESTAMPS: dict[str, deque[float]] = defaultdict(deque)


def _rate_limit(ip: str) -> None:
    settings = get_settings()
    now = time.monotonic()
    q = _IP_TIMESTAMPS[ip]
    while q and now - q[0] > _RATE_WINDOW_SECS:
        q.popleft()
    if len(q) >= settings.citizen_lookup_per_15min:
        raise RateLimitError("Too many lookups; try again later")
    q.append(now)


def _mask_location(location: str | None) -> str | None:
    if not location:
        return None
    parts = [p.strip() for p in location.split(",") if p.strip()]
    return ", ".join(parts[:2]) if parts else None


def _latest_snapshot_dataset_id(session: Session) -> UUID | None:
    """Use the newest matched dataset as the citizen-facing snapshot."""
    return (
        session.query(DatasetRow.id)
        .filter(DatasetRow.status == "matched")
        .order_by(DatasetRow.uploaded_at.desc())
        .limit(1)
        .scalar()
    )


@router.post("/lookup", response_model=ApiResponse[CitizenLookupResponse])
async def lookup(
    body: CitizenLookupRequest,
    request: Request,
    session: Session = Depends(session_dep),
) -> ApiResponse[CitizenLookupResponse]:
    if not body.consent:
        raise ValidationError("Consent to the privacy notice is required")

    tax_id = normalize_tax_id(body.tax_id)
    if not tax_id:
        raise ValidationError("Invalid tax_id format")

    ip = request.client.host if request.client else "unknown"
    _rate_limit(ip)

    # NOTE: we do not validate CAPTCHA here for the hackathon build; production
    # flow calls Turnstile's ``/siteverify`` with ``settings.citizen_captcha_secret``.

    person = session.get(PersonRow, tax_id)
    dataset_id = _latest_snapshot_dataset_id(session)
    if dataset_id is None:
        parcels = []
        estates = []
        findings_open = 0
    else:
        parcels = (
            session.query(LandParcelRow)
            .filter(
                LandParcelRow.owner_tax_id == tax_id,
                LandParcelRow.dataset_id == dataset_id,
            )
            .all()
        )
        estates = (
            session.query(RealEstateRow)
            .filter(
                RealEstateRow.owner_tax_id == tax_id,
                RealEstateRow.dataset_id == dataset_id,
                RealEstateRow.terminated_at.is_(None),
            )
            .all()
        )
        findings_open = (
            session.query(FindingRow)
            .filter(
                FindingRow.person_tax_id == tax_id,
                FindingRow.dataset_id == dataset_id,
                FindingRow.status.in_(["open", "in_review"]),
            )
            .count()
        )

    assets: list[CitizenAssetDTO] = []
    for parcel in parcels:
        assets.append(
            CitizenAssetDTO(
                kind="land_parcel",
                label=parcel.intended_use_label or parcel.intended_use_code or "Земельна ділянка",
                area_m2=parcel.area_m2,
                location_masked=_mask_location(parcel.location_admin),
            )
        )
    for estate in estates:
        assets.append(
            CitizenAssetDTO(
                kind="real_estate",
                label=estate.object_type_raw or "Об'єкт нерухомості",
                area_m2=estate.area_m2,
                location_masked=_mask_location(estate.address_raw),
            )
        )

    log_action(
        session,
        actor=f"citizen:{ip}",
        action="citizen_lookup",
        target_table="person",
        target_id=tax_id,
        payload={"hits": len(assets), "open_findings": int(findings_open)},
    )
    session.commit()

    return ok(
        CitizenLookupResponse(
            owner_name_masked=mask_name(person.full_name_raw if person else ""),
            assets=assets,
            unresolved_findings=int(findings_open),
            last_checked_at=datetime.now(tz=timezone.utc),
        )
    )
