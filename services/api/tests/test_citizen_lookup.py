"""Integration tests for citizen lookup snapshots."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import session_dep
from app.api.errors import (
    AppError,
    app_error_handler,
    unhandled_error_handler,
    validation_error_handler,
)
from app.api.routers import citizen as citizen_router
from app.api.routers import ALL_ROUTERS
from app.db.models import DatasetRow, FindingRow, LandParcelRow, PersonRow, RealEstateRow


@pytest.fixture(autouse=True)
def reset_citizen_rate_limit_state() -> None:
    citizen_router._IP_TIMESTAMPS.clear()


@pytest.fixture()
def client():
    """Minimal app with in-memory DB for citizen endpoint tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    app = FastAPI()
    for router in ALL_ROUTERS:
        app.include_router(router)
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)

    def _override_session():
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[session_dep] = _override_session

    with TestClient(app, raise_server_exceptions=False) as c:
        from app.db.models import Base

        Base.metadata.create_all(bind=engine)
        c.session_factory = SessionLocal  # type: ignore[attr-defined]
        yield c
    engine.dispose()


def test_lookup_uses_latest_matched_dataset_only(client) -> None:
    """Citizen lookup should not merge historical dataset duplicates."""
    s = client.session_factory()
    try:
        person = PersonRow(
            tax_id="1234567890",
            full_name_raw="Тест Тест Тест",
            full_name_norm="тест тест тест",
            sources=["dzk", "drrp"],
        )
        old_ds = DatasetRow(
            label="old",
            status="matched",
            uploaded_at=datetime(2026, 1, 10, tzinfo=timezone.utc),
        )
        new_ds = DatasetRow(
            label="new",
            status="matched",
            uploaded_at=datetime(2026, 2, 10, tzinfo=timezone.utc),
        )
        s.add_all([person, old_ds, new_ds])
        s.flush()

        # Same person appears in both uploads; only newest snapshot should be shown.
        s.add_all(
            [
                LandParcelRow(
                    dataset_id=old_ds.id,
                    cadastral_no="00:00:000:0001",
                    owner_tax_id=person.tax_id,
                    intended_use_label="old parcel",
                    area_m2=100.0,
                ),
                RealEstateRow(
                    dataset_id=old_ds.id,
                    owner_tax_id=person.tax_id,
                    object_type_raw="old estate",
                    area_m2=200.0,
                ),
                LandParcelRow(
                    dataset_id=new_ds.id,
                    cadastral_no="00:00:000:0002",
                    owner_tax_id=person.tax_id,
                    intended_use_label="new parcel",
                    area_m2=150.0,
                ),
                FindingRow(
                    dataset_id=old_ds.id,
                    person_tax_id=person.tax_id,
                    finding_type="LAND_NO_REAL_ESTATE",
                    severity="warning",
                    status="open",
                    computed_metrics={},
                ),
                FindingRow(
                    dataset_id=new_ds.id,
                    person_tax_id=person.tax_id,
                    finding_type="REAL_ESTATE_NO_LAND",
                    severity="critical",
                    status="in_review",
                    computed_metrics={},
                ),
            ]
        )
        s.commit()
    finally:
        s.close()

    resp = client.post(
        "/api/citizen/lookup",
        json={"tax_id": "1234567890", "captcha_token": "demo", "consent": True},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert len(data["assets"]) == 1
    assert data["assets"][0]["label"] == "new parcel"
    assert data["unresolved_findings"] == 1


def test_lookup_no_datasets_returns_empty_assets(client) -> None:
    s = client.session_factory()
    try:
        s.add(
            PersonRow(
                tax_id="9999999999",
                full_name_raw="No Data Test",
                full_name_norm="no data test",
                sources=[],
            )
        )
        s.commit()
    finally:
        s.close()

    resp = client.post(
        "/api/citizen/lookup",
        json={"tax_id": "9999999999", "captcha_token": "demo", "consent": True},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["assets"] == []
    assert data["unresolved_findings"] == 0


def test_lookup_ignores_non_matched_dataset(client) -> None:
    s = client.session_factory()
    try:
        person = PersonRow(
            tax_id="1111111111",
            full_name_raw="Інгест Тест",
            full_name_norm="інгест тест",
            sources=["dzk"],
        )
        ingesting_ds = DatasetRow(
            label="in-flight",
            status="ingesting",
            uploaded_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        )
        s.add_all([person, ingesting_ds])
        s.flush()
        s.add(
            LandParcelRow(
                dataset_id=ingesting_ds.id,
                cadastral_no="00:00:000:9999",
                owner_tax_id=person.tax_id,
                area_m2=999.0,
            )
        )
        s.commit()
    finally:
        s.close()

    resp = client.post(
        "/api/citizen/lookup",
        json={"tax_id": "1111111111", "captcha_token": "demo", "consent": True},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["assets"] == []
