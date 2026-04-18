"""Budget impact, executive summary, and downloadable exports."""

from __future__ import annotations

import re
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import require_analyst, session_dep
from app.api.envelope import ApiResponse, ok
from app.api.errors import ForbiddenError, NotFoundError, ValidationError
from app.api.schemas import BudgetImpactDTO, ExecutiveSummaryDTO
from app.reports.service import (
    ReportFilters,
    build_budget_impact,
    build_executive_summary,
    build_findings_export,
    executive_pdf_bytes,
    findings_csv_bytes,
    findings_xlsx_bytes,
)
from app.security.audit import log_action
from app.security.auth import Principal

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _safe_label(label: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_-]+", "-", label).strip("-")
    return slug or "dataset"


def _parse_pii_scope(pii_scope: str, principal: Principal) -> str:
    if pii_scope not in {"masked", "full"}:
        raise ValidationError("pii_scope must be either 'masked' or 'full'")
    if pii_scope == "full" and not principal.is_admin:
        raise ForbiddenError("pii_scope=full is only allowed for admin role")
    return pii_scope


@router.get("/budget-impact", response_model=ApiResponse[BudgetImpactDTO])
async def budget_impact(
    dataset_id: UUID = Query(...),
    principal: Principal = Depends(require_analyst),
    session: Session = Depends(session_dep),
) -> ApiResponse[BudgetImpactDTO]:
    try:
        dto = build_budget_impact(session, dataset_id=dataset_id)
    except ValueError as exc:
        raise NotFoundError(f"Dataset {dataset_id} not found") from exc

    log_action(
        session,
        actor=principal.subject,
        action="export_report",
        target_table="report",
        target_id=str(dataset_id),
        payload={"kind": "budget-impact"},
    )
    session.commit()
    return ok(dto)


@router.get("/executive-summary", response_model=ApiResponse[ExecutiveSummaryDTO])
async def executive_summary(
    dataset_id: UUID = Query(...),
    severity: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    finding_type: str | None = Query(default=None),
    koatuu: str | None = Query(default=None),
    q: str | None = Query(default=None),
    pii_scope: str = Query(default="masked"),
    principal: Principal = Depends(require_analyst),
    session: Session = Depends(session_dep),
) -> ApiResponse[ExecutiveSummaryDTO]:
    scope = _parse_pii_scope(pii_scope, principal)
    filters = ReportFilters(
        dataset_id=dataset_id,
        severity=severity,
        status=status_filter,
        finding_type=finding_type,
        koatuu=koatuu,
        q=q,
    )
    try:
        dto = build_executive_summary(session, filters=filters, pii_scope=scope)
    except ValueError as exc:
        raise NotFoundError(f"Dataset {dataset_id} not found") from exc

    log_action(
        session,
        actor=principal.subject,
        action="export_report",
        target_table="report",
        target_id=str(dataset_id),
        payload={"kind": "executive-summary", "pii_scope": scope},
    )
    session.commit()
    return ok(dto)


@router.get("/findings-export")
async def findings_export_csv(
    dataset_id: UUID = Query(...),
    severity: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    finding_type: str | None = Query(default=None),
    koatuu: str | None = Query(default=None),
    q: str | None = Query(default=None),
    pii_scope: str = Query(default="masked"),
    principal: Principal = Depends(require_analyst),
    session: Session = Depends(session_dep),
) -> Response:
    scope = _parse_pii_scope(pii_scope, principal)
    filters = ReportFilters(
        dataset_id=dataset_id,
        severity=severity,
        status=status_filter,
        finding_type=finding_type,
        koatuu=koatuu,
        q=q,
    )
    try:
        context, rows, _, truncated = build_findings_export(session, filters=filters, pii_scope=scope)
    except ValueError as exc:
        raise NotFoundError(f"Dataset {dataset_id} not found") from exc

    payload = findings_csv_bytes(rows)
    filename = f"findings_{_safe_label(context.dataset_label)}_{datetime.now().strftime('%Y%m%d')}.csv"
    log_action(
        session,
        actor=principal.subject,
        action="export_report",
        target_table="report",
        target_id=str(dataset_id),
        payload={"kind": "findings-csv", "rows": len(rows), "pii_scope": scope},
    )
    session.commit()
    return Response(
        content=payload,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Report-Truncated": str(truncated).lower(),
        },
    )


@router.get("/findings-export.xlsx")
async def findings_export_xlsx(
    dataset_id: UUID = Query(...),
    severity: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    finding_type: str | None = Query(default=None),
    koatuu: str | None = Query(default=None),
    q: str | None = Query(default=None),
    pii_scope: str = Query(default="masked"),
    principal: Principal = Depends(require_analyst),
    session: Session = Depends(session_dep),
) -> Response:
    scope = _parse_pii_scope(pii_scope, principal)
    filters = ReportFilters(
        dataset_id=dataset_id,
        severity=severity,
        status=status_filter,
        finding_type=finding_type,
        koatuu=koatuu,
        q=q,
    )
    try:
        context, rows, summary, truncated = build_findings_export(session, filters=filters, pii_scope=scope)
    except ValueError as exc:
        raise NotFoundError(f"Dataset {dataset_id} not found") from exc

    payload = findings_xlsx_bytes(rows, summary)
    filename = f"findings_{_safe_label(context.dataset_label)}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    log_action(
        session,
        actor=principal.subject,
        action="export_report",
        target_table="report",
        target_id=str(dataset_id),
        payload={"kind": "findings-xlsx", "rows": len(rows), "pii_scope": scope},
    )
    session.commit()
    return Response(
        content=payload,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Report-Truncated": str(truncated).lower(),
        },
    )


@router.get("/executive.pdf")
async def executive_pdf(
    dataset_id: UUID = Query(...),
    severity: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    finding_type: str | None = Query(default=None),
    koatuu: str | None = Query(default=None),
    q: str | None = Query(default=None),
    pii_scope: str = Query(default="masked"),
    principal: Principal = Depends(require_analyst),
    session: Session = Depends(session_dep),
) -> Response:
    scope = _parse_pii_scope(pii_scope, principal)
    filters = ReportFilters(
        dataset_id=dataset_id,
        severity=severity,
        status=status_filter,
        finding_type=finding_type,
        koatuu=koatuu,
        q=q,
    )
    try:
        summary = build_executive_summary(session, filters=filters, pii_scope=scope)
    except ValueError as exc:
        raise NotFoundError(f"Dataset {dataset_id} not found") from exc

    payload = executive_pdf_bytes(summary)
    filename = f"executive_{_safe_label(summary.metadata.dataset_label)}_{datetime.now().strftime('%Y%m%d')}.pdf"
    log_action(
        session,
        actor=principal.subject,
        action="export_report",
        target_table="report",
        target_id=str(dataset_id),
        payload={"kind": "executive-pdf", "pii_scope": scope},
    )
    session.commit()
    return Response(
        content=payload,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
