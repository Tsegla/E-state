"""Integration tests for report downloads and executive summaries."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import current_user, require_analyst, session_dep
from app.api.errors import (
    AppError,
    app_error_handler,
    unhandled_error_handler,
    validation_error_handler,
)
from app.api.routers import ALL_ROUTERS
from app.db.models import Base, DatasetRow, FindingRow, LandParcelRow, PersonRow, VerifiedAssetRow
from app.security.auth import Principal

ANALYST = Principal(subject="analyst@example.com", role="analyst")
ADMIN = Principal(subject="admin@example.com", role="admin")


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    app = FastAPI()
    for router in ALL_ROUTERS:
        app.include_router(router)
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)

    def _override_session():
        s = session_local()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[session_dep] = _override_session
    app.dependency_overrides[current_user] = lambda: ANALYST
    app.dependency_overrides[require_analyst] = lambda: ANALYST

    with TestClient(app, raise_server_exceptions=False) as c:
        c.session_factory = session_local  # type: ignore[attr-defined]
        yield c, app

    engine.dispose()


def _seed_data(session_factory):
    s = session_factory()
    try:
        dataset = DatasetRow(
            label="Сокаль 2026-04-18",
            status="matched",
            uploaded_at=datetime(2026, 4, 18, tzinfo=timezone.utc),
        )
        s.add(dataset)
        s.flush()
        person = PersonRow(
            tax_id="1234567890",
            full_name_raw="Тест Тестович",
            full_name_norm="тест тестович",
            sources=["dzk", "drrp"],
        )
        s.add(person)
        s.flush()
        s.add(
            LandParcelRow(
                dataset_id=dataset.id,
                cadastral_no="00:00:000:0001",
                owner_tax_id=person.tax_id,
                koatuu="4624881201",
                area_m2=500.0,
            )
        )
        finding = FindingRow(
            dataset_id=dataset.id,
            person_tax_id=person.tax_id,
            finding_type="LAND_NO_REAL_ESTATE",
            severity="warning",
            status="open",
            computed_metrics={"total_residential_m2": 250.0},
        )
        s.add(finding)
        s.flush()
        s.add(
            VerifiedAssetRow(
                finding_id=finding.id,
                dataset_id=dataset.id,
                person_tax_id=person.tax_id,
                source_of_truth="field_override",
                chosen_ref_kind=None,
                chosen_ref_id=None,
                object_type="будинок",
                area_m2=300.0,
                use="житловий",
                address="вул. Тестова, 1",
                verified_by="inspector-1",
            )
        )
        s.commit()
        return dataset.id
    finally:
        s.close()


def test_findings_csv_export_masked_by_default(client) -> None:
    c, _ = client
    dataset_id = _seed_data(c.session_factory)

    resp = c.get("/api/reports/findings-export", params={"dataset_id": str(dataset_id)})
    assert resp.status_code == 200, resp.text
    assert "attachment; filename=" in resp.headers.get("content-disposition", "")
    assert "text/csv" in resp.headers.get("content-type", "")
    body = resp.text
    assert "РНОКПП" in body
    assert "Тип розбіжності" in body
    assert "12••••••90" in body
    assert "1234567890" not in body


def test_findings_csv_export_full_requires_admin(client) -> None:
    c, app = client
    dataset_id = _seed_data(c.session_factory)

    denied = c.get(
        "/api/reports/findings-export",
        params={"dataset_id": str(dataset_id), "pii_scope": "full"},
    )
    assert denied.status_code == 403

    app.dependency_overrides[current_user] = lambda: ADMIN
    app.dependency_overrides[require_analyst] = lambda: ADMIN
    allowed = c.get(
        "/api/reports/findings-export",
        params={"dataset_id": str(dataset_id), "pii_scope": "full"},
    )
    assert allowed.status_code == 200
    assert "1234567890" in allowed.text


def test_findings_xlsx_export_works(client) -> None:
    c, _ = client
    dataset_id = _seed_data(c.session_factory)
    resp = c.get("/api/reports/findings-export.xlsx", params={"dataset_id": str(dataset_id)})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert len(resp.content) > 100


def test_executive_summary_and_pdf(client) -> None:
    c, _ = client
    dataset_id = _seed_data(c.session_factory)

    summary_resp = c.get("/api/reports/executive-summary", params={"dataset_id": str(dataset_id)})
    assert summary_resp.status_code == 200
    data = summary_resp.json()["data"]
    assert data["metadata"]["dataset_id"] == str(dataset_id)
    assert "caveats" in data["budget_impact"]
    assert data["budget_impact"]["used_verified_assets"] >= 1

    pdf_resp = c.get("/api/reports/executive.pdf", params={"dataset_id": str(dataset_id)})
    assert pdf_resp.status_code == 200
    assert pdf_resp.content.startswith(b"%PDF-")
