"""Report builders and file renderers for exports."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from sqlalchemy import Select, exists, func, select
from sqlalchemy.orm import Session

from app.api.schemas import BudgetImpactDTO, ExecutiveSummaryDTO, ReportMetaDTO
from app.db.models import (
    DatasetRow,
    FieldVisitRow,
    FindingRow,
    LandParcelRow,
    PersonRow,
    VerifiedAssetRow,
)
from app.domain.enums import FindingType
from app.matcher.config import default_config
from app.security.pii import mask_name, mask_tax_id

EXPORT_ROW_LIMIT = 50_000
PDF_FONT_NAME = "EStateUnicode"
REPORT_TIME_FORMAT = "%d.%m.%Y %H:%M UTC"
PDF_FONT_CANDIDATES = (
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
)
EXPORT_COLUMNS = [
    "ID кейсу",
    "Тип розбіжності",
    "Критичність",
    "Статус",
    "РНОКПП",
    "Власник",
    "КОАТУУ",
    "Виявлено",
    "Призначено інспектору",
    "Коротко про розбіжність",
    "К-сть виїздів",
    "Підтверджене джерело",
    "Підтверджена площа, м²",
    "Орієнтовний вплив на бюджет, грн/рік",
    "Нотатка для інспектора",
]
UPLIFT_COLUMN_UK = "Орієнтовний вплив на бюджет, грн/рік"

FINDING_TYPE_LABELS_UK = {
    FindingType.LAND_NO_REAL_ESTATE.value: "Земля без відповідної нерухомості",
    FindingType.REAL_ESTATE_NO_LAND.value: "Нерухомість без земельної ділянки",
    FindingType.USE_VS_OBJECT_MISMATCH.value: "Невідповідність використання об'єкта",
    FindingType.AREA_PORTFOLIO_DELTA.value: "Суттєва розбіжність площ",
    FindingType.OWNER_NAME_MISMATCH.value: "Невідповідність ПІБ/назви власника",
    FindingType.TERMINATED_BUT_ACTIVE.value: "Припинене право, але ознаки активного використання",
    FindingType.TERMINATED_RIGHTS_MISMATCH.value: "Невідповідність стану припинених прав",
    FindingType.MISSING_OWNER.value: "Відсутні дані про власника",
    FindingType.DUPLICATE_REGISTRATION.value: "Ймовірне дублювання реєстрації",
}

SEVERITY_LABELS_UK = {
    "critical": "Критично",
    "warning": "Попередження",
    "info": "Інформаційно",
}

STATUS_LABELS_UK = {
    "open": "Відкрито",
    "in_review": "На перевірці",
    "resolved": "Вирішено",
    "dismissed": "Відхилено",
}

SOURCE_LABELS_UK = {
    "dzk": "ДЗК",
    "drrp": "ДРРП",
    "field_override": "Польовий огляд",
}


def _normalize_to_utc(value: datetime) -> datetime:
    # SQLite may return naive datetimes even for timezone-aware columns; treat them as UTC.
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _format_report_timestamp(value: datetime | None) -> str:
    if value is None:
        return ""
    return _normalize_to_utc(value).strftime(REPORT_TIME_FORMAT)


@dataclass(frozen=True, slots=True)
class ReportFilters:
    dataset_id: UUID
    severity: str | None = None
    status: str | None = None
    finding_type: str | None = None
    koatuu: str | None = None
    q: str | None = None


@dataclass(frozen=True, slots=True)
class ReportContext:
    generated_at: datetime
    dataset_id: UUID
    dataset_label: str
    filters: dict[str, str]
    pii_scope: str


def _apply_filters(base: Select[tuple[FindingRow]], filters: ReportFilters) -> Select[tuple[FindingRow]]:
    stmt = base.where(FindingRow.dataset_id == filters.dataset_id)
    if filters.severity:
        stmt = stmt.where(FindingRow.severity == filters.severity)
    if filters.status:
        stmt = stmt.where(FindingRow.status == filters.status)
    if filters.finding_type:
        stmt = stmt.where(FindingRow.finding_type == filters.finding_type)
    if filters.q:
        q_norm = f"%{filters.q.strip().lower()}%"
        matching_people = select(PersonRow.tax_id).where(PersonRow.full_name_norm.like(q_norm))
        stmt = stmt.where(FindingRow.person_tax_id.in_(matching_people))
    if filters.koatuu:
        land_exists = (
            select(LandParcelRow.id)
            .where(
                LandParcelRow.dataset_id == filters.dataset_id,
                LandParcelRow.owner_tax_id == FindingRow.person_tax_id,
                LandParcelRow.koatuu.is_not(None),
                LandParcelRow.koatuu.like(f"{filters.koatuu}%"),
            )
            .limit(1)
        )
        stmt = stmt.where(exists(land_exists))
    return stmt


def _estimated_uplift_uah(
    finding: FindingRow,
    *,
    verified_asset: VerifiedAssetRow | None,
) -> float:
    cfg = default_config()
    metrics = finding.computed_metrics or {}
    finding_type = finding.finding_type

    if finding_type == FindingType.LAND_NO_REAL_ESTATE.value:
        m2 = float(verified_asset.area_m2 if verified_asset and verified_asset.area_m2 else metrics.get("total_residential_m2") or 0.0)
        return m2 * cfg.housing_rate_uah_per_m2_per_year
    if finding_type == FindingType.AREA_PORTFOLIO_DELTA.value:
        if verified_asset and verified_asset.area_m2:
            land_m2 = float(metrics.get("land_m2") or 0.0)
            delta = max(float(verified_asset.area_m2) - land_m2, 0.0)
        else:
            delta = max(float(metrics.get("delta_m2") or 0.0), 0.0)
        return delta * cfg.commercial_rate_uah_per_m2_per_year
    if finding_type in {FindingType.MISSING_OWNER.value, FindingType.TERMINATED_BUT_ACTIVE.value}:
        m2 = float(verified_asset.area_m2 if verified_asset and verified_asset.area_m2 else metrics.get("total_m2") or metrics.get("active_area_m2") or 0.0)
        return m2 * cfg.agri_rate_uah_per_m2_per_year
    return 0.0


def _metadata(filters: ReportFilters, *, dataset: DatasetRow, pii_scope: str) -> ReportContext:
    details: dict[str, str] = {"dataset_id": str(filters.dataset_id)}
    if filters.severity:
        details["severity"] = filters.severity
    if filters.status:
        details["status"] = filters.status
    if filters.finding_type:
        details["finding_type"] = filters.finding_type
    if filters.koatuu:
        details["koatuu"] = filters.koatuu
    if filters.q:
        details["q"] = filters.q
    return ReportContext(
        generated_at=datetime.now(tz=timezone.utc),
        dataset_id=dataset.id,
        dataset_label=dataset.label,
        filters=details,
        pii_scope=pii_scope,
    )


def _get_dataset(session: Session, dataset_id: UUID) -> DatasetRow | None:
    return session.get(DatasetRow, dataset_id)


def _fetch_filtered_findings(session: Session, filters: ReportFilters) -> list[FindingRow]:
    severity_rank = {
        "critical": 0,
        "warning": 1,
        "info": 2,
    }
    rows = (
        session.execute(_apply_filters(select(FindingRow), filters).limit(EXPORT_ROW_LIMIT))
        .scalars()
        .all()
    )
    return sorted(
        rows,
        key=lambda row: (
            severity_rank.get(row.severity, 99),
            _normalize_to_utc(row.detected_at),
            str(row.id),
        ),
        reverse=False,
    )


def _related_maps(
    session: Session,
    *,
    dataset_id: UUID,
    findings: list[FindingRow],
) -> tuple[dict[str, str], dict[UUID, VerifiedAssetRow], dict[str, str], dict[UUID, int]]:
    finding_ids = [row.id for row in findings]
    person_ids = list({row.person_tax_id for row in findings})
    people = (
        session.execute(select(PersonRow).where(PersonRow.tax_id.in_(person_ids))).scalars().all()
        if person_ids
        else []
    )
    people_map = {row.tax_id: row.full_name_raw for row in people}

    lands = session.execute(
        select(LandParcelRow.owner_tax_id, LandParcelRow.koatuu).where(
            LandParcelRow.dataset_id == dataset_id,
            LandParcelRow.owner_tax_id.in_(person_ids),
        )
    ).all() if person_ids else []
    koatuu_map: dict[str, str] = {}
    for owner_tax_id, koatuu in lands:
        if owner_tax_id and koatuu and owner_tax_id not in koatuu_map:
            koatuu_map[owner_tax_id] = koatuu

    verified_rows = (
        session.execute(select(VerifiedAssetRow).where(VerifiedAssetRow.finding_id.in_(finding_ids)))
        .scalars()
        .all()
        if finding_ids
        else []
    )
    verified_map = {row.finding_id: row for row in verified_rows}

    visit_counts = (
        dict(
            session.execute(
                select(FieldVisitRow.finding_id, func.count(FieldVisitRow.id))
                .where(FieldVisitRow.finding_id.in_(finding_ids))
                .group_by(FieldVisitRow.finding_id)
            ).all()
        )
        if finding_ids
        else {}
    )

    return people_map, verified_map, koatuu_map, visit_counts


def _report_rows(
    findings: list[FindingRow],
    *,
    context: ReportContext,
    people_map: dict[str, str],
    verified_map: dict[UUID, VerifiedAssetRow],
    koatuu_map: dict[str, str],
    visit_counts: dict[UUID, int],
) -> list[dict[str, str | int | float]]:
    rows: list[dict[str, str | int | float]] = []
    for finding in findings:
        person_name = people_map.get(finding.person_tax_id, "")
        verified = verified_map.get(finding.id)
        uplift = round(_estimated_uplift_uah(finding, verified_asset=verified), 2)
        if context.pii_scope == "full":
            person_tax_id = finding.person_tax_id
            person_display = person_name
        else:
            person_tax_id = mask_tax_id(finding.person_tax_id)
            person_display = mask_name(person_name)

        rows.append(
            {
                "ID кейсу": str(finding.id),
                "Тип розбіжності": FINDING_TYPE_LABELS_UK.get(finding.finding_type, finding.finding_type),
                "Критичність": SEVERITY_LABELS_UK.get(finding.severity, finding.severity),
                "Статус": STATUS_LABELS_UK.get(finding.status, finding.status),
                "РНОКПП": person_tax_id,
                "Власник": person_display,
                "КОАТУУ": koatuu_map.get(finding.person_tax_id, ""),
                "Виявлено": _format_report_timestamp(finding.detected_at),
                "Призначено інспектору": _format_report_timestamp(finding.assigned_at),
                "Коротко про розбіжність": _metrics_summary_uk(finding),
                "К-сть виїздів": int(visit_counts.get(finding.id, 0)),
                "Підтверджене джерело": (
                    SOURCE_LABELS_UK.get(verified.source_of_truth, verified.source_of_truth)
                    if verified
                    else ""
                ),
                "Підтверджена площа, м²": (
                    round(float(verified.area_m2), 2)
                    if verified and verified.area_m2 is not None
                    else ""
                ),
                UPLIFT_COLUMN_UK: uplift,
                "Нотатка для інспектора": (
                    finding.assignment_note or ""
                    if context.pii_scope == "full"
                    else ""
                ),
            }
        )
    return rows


def _render_csv(rows: list[dict[str, str | int | float]]) -> bytes:
    output = io.StringIO()
    fieldnames = list(rows[0].keys()) if rows else EXPORT_COLUMNS
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    if rows:
        writer.writerows(rows)
    # UTF-8 BOM makes Ukrainian text open correctly in Excel by default.
    return output.getvalue().encode("utf-8-sig")


def _render_xlsx(rows: list[dict[str, str | int | float]], summary: dict[str, float | int]) -> bytes:
    workbook = Workbook()
    details_sheet = workbook.active
    details_sheet.title = "розбіжності"
    if rows:
        headers = list(rows[0].keys())
        details_sheet.append(headers)
        for row in rows:
            details_sheet.append([row[h] for h in headers])
    else:
        details_sheet.append(["Розбіжностей за обраними фільтрами не знайдено."])

    summary_sheet = workbook.create_sheet("зведення")
    summary_sheet.append(["Показник", "Значення"])
    for key, value in summary.items():
        summary_sheet.append([_summary_label_uk(key), value])

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _pdf_font_name() -> str:
    if PDF_FONT_NAME in pdfmetrics.getRegisteredFontNames():
        return PDF_FONT_NAME
    for candidate in PDF_FONT_CANDIDATES:
        path = Path(candidate)
        if path.exists():
            pdfmetrics.registerFont(TTFont(PDF_FONT_NAME, str(path)))
            return PDF_FONT_NAME
    return "Helvetica"


def _report_pdf(lines: list[str]) -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    left = 40
    top = height - 40
    bottom = 40
    line_height = 14
    current_y = top
    font_name = _pdf_font_name()
    pdf.setFont(font_name, 10)

    for line in lines:
        chunks = [line] if line else [""]
        for chunk in chunks:
            if current_y < bottom:
                pdf.showPage()
                pdf.setFont(font_name, 10)
                current_y = top
            pdf.drawString(left, current_y, chunk)
            current_y -= line_height

    pdf.save()
    return buffer.getvalue()


def _summary_metrics(
    findings: list[FindingRow],
    *,
    rows: list[dict[str, str | int | float]],
) -> dict[str, float | int]:
    status_counter = Counter(row.status for row in findings)
    severity_counter = Counter(row.severity for row in findings)
    type_counter = Counter(row.finding_type for row in findings)
    return {
        "total_findings": len(findings),
        "critical_count": int(severity_counter.get("critical", 0)),
        "open_count": int(status_counter.get("open", 0)),
        "in_review_count": int(status_counter.get("in_review", 0)),
        "resolved_count": int(status_counter.get("resolved", 0)),
        "dismissed_count": int(status_counter.get("dismissed", 0)),
        "unique_finding_types": len(type_counter),
        "estimated_uplift_uah_per_year": round(
            sum(float(r.get(UPLIFT_COLUMN_UK) or 0.0) for r in rows), 2
        ),
    }


def _metrics_summary_uk(finding: FindingRow) -> str:
    metrics = finding.computed_metrics or {}
    if finding.finding_type == FindingType.LAND_NO_REAL_ESTATE.value:
        return (
            "У реєстрі нерухомості є площа "
            f"{float(metrics.get('total_residential_m2') or 0.0):,.1f} м², "
            "але відповідних земельних записів недостатньо."
        )
    if finding.finding_type == FindingType.AREA_PORTFOLIO_DELTA.value:
        return (
            "Площа нерухомості перевищує площу землі на "
            f"{float(metrics.get('delta_m2') or 0.0):,.1f} м² "
            f"(коефіцієнт {float(metrics.get('ratio') or 0.0):.2f})."
        )
    if finding.finding_type == FindingType.MISSING_OWNER.value:
        return (
            "Виявлено записи без належно вказаного власника, "
            f"орієнтовна площа {float(metrics.get('total_m2') or 0.0):,.1f} м²."
        )
    if finding.finding_type == FindingType.TERMINATED_BUT_ACTIVE.value:
        return (
            "Право зазначене як припинене, але система бачить "
            f"{int(metrics.get('active_parcels') or 0)} активних ділянок."
        )
    if finding.finding_type == FindingType.OWNER_NAME_MISMATCH.value:
        return (
            "ПІБ/назва власника відрізняється між реєстрами "
            f"(схожість {float(metrics.get('similarity') or 0.0):.2f})."
        )
    if finding.finding_type == FindingType.DUPLICATE_REGISTRATION.value:
        return (
            "Можливе дублювання права: виявлено "
            f"{int(metrics.get('distinct_owners') or 0)} різних власників для одного кейсу."
        )
    if finding.finding_type == FindingType.REAL_ESTATE_NO_LAND.value:
        return "Є об'єкт нерухомості, але не знайдено відповідного земельного запису."
    if finding.finding_type == FindingType.USE_VS_OBJECT_MISMATCH.value:
        return "Цільове призначення землі не відповідає типу об'єкта нерухомості."
    if finding.finding_type == FindingType.TERMINATED_RIGHTS_MISMATCH.value:
        return "Статус припинення прав у реєстрах не узгоджується."
    return "Виявлено неузгодженість між реєстрами, потрібна додаткова перевірка."


def _summary_label_uk(key: str) -> str:
    labels = {
        "total_findings": "Усього розбіжностей",
        "critical_count": "Критичних",
        "open_count": "Відкритих",
        "in_review_count": "На перевірці",
        "resolved_count": "Вирішених",
        "dismissed_count": "Відхилених",
        "unique_finding_types": "Унікальних типів розбіжностей",
        "estimated_uplift_uah_per_year": "Орієнтовний вплив на бюджет, грн/рік",
        "export_truncated": "Експорт обрізано (1=так, 0=ні)",
    }
    return labels.get(key, key)


def build_findings_export(
    session: Session,
    *,
    filters: ReportFilters,
    pii_scope: str,
) -> tuple[
    ReportContext,
    list[dict[str, str | int | float]],
    dict[str, float | int],
    bool,
]:
    dataset = _get_dataset(session, filters.dataset_id)
    if dataset is None:
        raise ValueError("dataset not found")

    findings = _fetch_filtered_findings(session, filters)
    people_map, verified_map, koatuu_map, visit_counts = _related_maps(
        session,
        dataset_id=filters.dataset_id,
        findings=findings,
    )
    context = _metadata(filters, dataset=dataset, pii_scope=pii_scope)
    rows = _report_rows(
        findings,
        context=context,
        people_map=people_map,
        verified_map=verified_map,
        koatuu_map=koatuu_map,
        visit_counts=visit_counts,
    )
    truncated = len(findings) >= EXPORT_ROW_LIMIT
    summary = _summary_metrics(findings, rows=rows)
    summary["export_truncated"] = int(truncated)
    return context, rows, summary, truncated


def findings_csv_bytes(rows: list[dict[str, str | int | float]]) -> bytes:
    return _render_csv(rows)


def findings_xlsx_bytes(
    rows: list[dict[str, str | int | float]],
    summary: dict[str, float | int],
) -> bytes:
    return _render_xlsx(rows, summary)


def build_budget_impact(
    session: Session,
    *,
    dataset_id: UUID,
) -> BudgetImpactDTO:
    dataset = _get_dataset(session, dataset_id)
    if dataset is None:
        raise ValueError("dataset not found")

    rows = (
        session.query(FindingRow)
        .filter(FindingRow.dataset_id == dataset_id, FindingRow.status.in_(["open", "in_review", "resolved"]))
        .all()
    )
    verified_rows = (
        session.query(VerifiedAssetRow).filter(VerifiedAssetRow.dataset_id == dataset_id).all()
    )
    verified_map = {row.finding_id: row for row in verified_rows}
    by_type: dict[str, float] = defaultdict(float)
    total = 0.0
    unresolved = 0
    resolved = 0
    used_verified = 0
    for finding in rows:
        verified = verified_map.get(finding.id)
        if verified is not None:
            used_verified += 1
        amount = _estimated_uplift_uah(finding, verified_asset=verified)
        if amount > 0:
            by_type[finding.finding_type] += amount
            total += amount
        if finding.status in {"open", "in_review"}:
            unresolved += 1
        if finding.status == "resolved":
            resolved += 1

    return BudgetImpactDTO(
        total_uah_per_year=round(total, 2),
        by_type={k: round(v, 2) for k, v in by_type.items()},
        unresolved_findings=unresolved,
        resolved_findings=resolved,
        used_verified_assets=used_verified,
        caveats=[
            "Оцінка є прогнозом на основі конфігурації matcher/config.py.",
            "Після польової верифікації використовуються дані verified_asset, якщо доступні.",
        ],
        generated_at=datetime.now(tz=timezone.utc),
        dataset_id=dataset_id,
    )


def build_executive_summary(
    session: Session,
    *,
    filters: ReportFilters,
    pii_scope: str,
) -> ExecutiveSummaryDTO:
    dataset = _get_dataset(session, filters.dataset_id)
    if dataset is None:
        raise ValueError("dataset not found")

    findings = _fetch_filtered_findings(session, filters)
    impact = build_budget_impact(session, dataset_id=filters.dataset_id)
    koatuu_counter: Counter[str] = Counter()
    person_ids = {row.person_tax_id for row in findings}
    locality_rows = (
        session.execute(
            select(LandParcelRow.owner_tax_id, LandParcelRow.koatuu).where(
                LandParcelRow.dataset_id == filters.dataset_id,
                LandParcelRow.owner_tax_id.in_(person_ids),
            )
        ).all()
        if person_ids
        else []
    )
    for owner_tax_id, koatuu in locality_rows:
        if owner_tax_id and koatuu:
            koatuu_counter[koatuu] += 1

    status_counts: Counter[str] = Counter(row.status for row in findings)
    top_localities = [
        {"koatuu": key, "findings": value}
        for key, value in koatuu_counter.most_common(5)
    ]
    return ExecutiveSummaryDTO(
        budget_impact=impact,
        top_localities=top_localities,
        by_status={k: int(v) for k, v in status_counts.items()},
        metadata=ReportMetaDTO(
            generated_at=datetime.now(tz=timezone.utc),
            dataset_id=dataset.id,
            dataset_label=dataset.label,
            filters=_metadata(filters, dataset=dataset, pii_scope=pii_scope).filters,
            pii_scope=pii_scope,
        ),
    )


def executive_pdf_bytes(summary: ExecutiveSummaryDTO) -> bytes:
    lines = [
        "E-State: Підсумковий звіт для керівництва громади",
        f"Набір даних: {summary.metadata.dataset_label}",
        f"Дата формування: {_format_report_timestamp(summary.metadata.generated_at)}",
        "",
        "1) Орієнтовний вплив на бюджет",
        f"  Очікувані додаткові надходження: {summary.budget_impact.total_uah_per_year:,.2f} грн/рік",
        f"  Відкриті кейси: {summary.budget_impact.unresolved_findings}",
        f"  Вирішені кейси: {summary.budget_impact.resolved_findings}",
        f"  Кейсів з підтвердженим польовим джерелом: {summary.budget_impact.used_verified_assets}",
        "",
        "2) Розподіл впливу за типом розбіжності",
    ]
    for finding_type, amount in summary.budget_impact.by_type.items():
        label = FINDING_TYPE_LABELS_UK.get(finding_type, finding_type)
        lines.append(f"  - {label}: {amount:,.2f} грн")
    lines.append("")
    lines.append("3) Пріоритетні локальності (за кількістю кейсів)")
    for item in summary.top_localities:
        lines.append(f"  - КОАТУУ {item['koatuu']}: {item['findings']} кейсів")
    lines.append("")
    lines.append("4) Важливо врахувати")
    for caveat in summary.budget_impact.caveats:
        lines.append(f"  - {caveat}")
    return _report_pdf(lines)
