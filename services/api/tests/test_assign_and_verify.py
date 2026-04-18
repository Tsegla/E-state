"""Integration tests for analyst assign + inspector verify flow."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import current_user, require_analyst, require_inspector, session_dep
from app.api.errors import (
    AppError,
    app_error_handler,
    unhandled_error_handler,
    validation_error_handler,
)
from app.api.routers import ALL_ROUTERS
from app.db.models import (
    Base,
    DatasetRow,
    FindingEvidenceRow,
    FindingRow,
    LandParcelRow,
    PersonRow,
    RealEstateRow,
    VerifiedAssetRow,
)
from app.security.auth import Principal


ANALYST = Principal(subject="analyst@example.com", role="analyst")
INSPECTOR = Principal(subject="inspector-1", role="inspector")


@pytest.fixture()
def client():
    """Minimal test app wired to a shared in-memory SQLite DB."""
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
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
    app.dependency_overrides[current_user] = lambda: ANALYST
    app.dependency_overrides[require_analyst] = lambda: ANALYST
    app.dependency_overrides[require_inspector] = lambda: INSPECTOR

    with TestClient(app, raise_server_exceptions=False) as c:
        c.session_factory = SessionLocal  # type: ignore[attr-defined]
        yield c

    engine.dispose()


def _seed_finding(
    session_factory,
    *,
    status: str = "open",
) -> tuple[UUID, UUID, UUID]:
    """Returns (finding_id, dzk_evidence_id, drrp_evidence_id)."""
    s = session_factory()
    try:
        ds = DatasetRow(label="test", status="matched")
        s.add(ds)
        s.flush()

        person = PersonRow(
            tax_id="1234567890",
            full_name_raw="Тест Тест Тест",
            full_name_norm="тест тест тест",
            sources=["dzk", "drrp"],
        )
        s.add(person)

        land = LandParcelRow(
            dataset_id=ds.id,
            cadastral_no="00:00:000:0001",
            area_m2=500.0,
            owner_tax_id=person.tax_id,
            intended_use_label="Для будівництва",
        )
        estate = RealEstateRow(
            dataset_id=ds.id,
            area_m2=5000.0,
            owner_tax_id=person.tax_id,
            object_type_raw="ресторан",
            object_type_norm="commercial",
            address_raw="вул. Тестова, 1",
        )
        s.add_all([land, estate])
        s.flush()

        finding = FindingRow(
            dataset_id=ds.id,
            person_tax_id=person.tax_id,
            finding_type="AREA_PORTFOLIO_DELTA",
            severity="critical",
            status=status,
            computed_metrics={"land_m2": 500, "re_m2": 5000, "ratio": 10.0},
        )
        s.add(finding)
        s.flush()

        ev_dzk = FindingEvidenceRow(
            finding_id=finding.id,
            kind="land_parcel",
            ref_id=land.id,
            snapshot={
                "cadastral_no": "00:00:000:0001",
                "area_m2": 500.0,
                "intended_use_label": "Для будівництва",
                "owner_name_raw": "Тест Тест Тест",
            },
        )
        ev_drrp = FindingEvidenceRow(
            finding_id=finding.id,
            kind="real_estate",
            ref_id=estate.id,
            snapshot={
                "address_raw": "вул. Тестова, 1",
                "area_m2": 5000.0,
                "object_type_raw": "ресторан",
                "object_type_norm": "commercial",
            },
        )
        s.add_all([ev_dzk, ev_drrp])
        s.commit()
        return finding.id, ev_dzk.id, ev_drrp.id
    finally:
        s.close()


def test_inspector_queue_only_shows_assigned_findings(client) -> None:
    """Інспектор має бачити лише ті findings, які явно передав землевпорядник.

    Без цього фільтра один призначений запис губиться серед тисяч непризначених
    `open`-findings того ж датасету.
    """
    assigned_finding_id, _, _ = _seed_finding(client.session_factory, status="open")

    s = client.session_factory()
    try:
        assigned_row = s.get(FindingRow, assigned_finding_id)
        dataset_id = assigned_row.dataset_id
        person_tax_id = assigned_row.person_tax_id
        sibling = FindingRow(
            dataset_id=dataset_id,
            person_tax_id=person_tax_id,
            finding_type="LAND_NO_REAL_ESTATE",
            severity="warning",
            status="open",
            computed_metrics={"total_residential_m2": 0},
        )
        s.add(sibling)
        s.commit()
        sibling_id = sibling.id
    finally:
        s.close()

    resp = client.post(
        f"/api/findings/{assigned_finding_id}/assign",
        json={"note": "На місце"},
    )
    assert resp.status_code == 200, resp.text

    resp = client.get("/api/inspector/findings", params={"dataset_id": str(dataset_id)})
    assert resp.status_code == 200, resp.text
    items = resp.json()["data"]
    ids = [item["id"] for item in items]
    assert str(assigned_finding_id) in ids
    assert str(sibling_id) not in ids
    assert all(item["status"] == "in_review" for item in items)


def test_assign_transitions_open_to_in_review_and_saves_note(client) -> None:
    finding_id, _, _ = _seed_finding(client.session_factory)

    resp = client.post(
        f"/api/findings/{finding_id}/assign",
        json={"note": "Перевірити фактичне використання"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["status"] == "in_review"
    assert data["assignment_note"] == "Перевірити фактичне використання"
    assert data["assigned_at"] is not None


def test_assign_rejects_when_not_open(client) -> None:
    finding_id, _, _ = _seed_finding(client.session_factory, status="resolved")

    resp = client.post(f"/api/findings/{finding_id}/assign", json={"note": None})
    assert resp.status_code == 409


def test_visit_with_drrp_truth_copies_snapshot_to_verified_asset(client) -> None:
    finding_id, _, ev_drrp_id = _seed_finding(client.session_factory)

    resp = client.post(
        "/api/inspector/visits",
        json={
            "finding_id": str(finding_id),
            "resolution": "resolved",
            "source_of_truth": "drrp",
            "truth_evidence_id": str(ev_drrp_id),
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    verified = data["verified_asset"]
    assert verified is not None
    assert verified["source_of_truth"] == "drrp"
    assert verified["chosen_ref_kind"] == "real_estate"
    assert verified["area_m2"] == 5000.0
    assert verified["address"] == "вул. Тестова, 1"
    assert verified["object_type"] == "ресторан"


def test_visit_with_field_override_uses_actual_fields(client) -> None:
    finding_id, _, _ = _seed_finding(client.session_factory)

    resp = client.post(
        "/api/inspector/visits",
        json={
            "finding_id": str(finding_id),
            "resolution": "resolved",
            "source_of_truth": "field_override",
            "actual_object_type": "кафе",
            "actual_area_m2": 210.5,
            "actual_use": "громадське харчування",
        },
    )
    assert resp.status_code == 200, resp.text
    verified = resp.json()["data"]["verified_asset"]
    assert verified["source_of_truth"] == "field_override"
    assert verified["chosen_ref_kind"] is None
    assert verified["area_m2"] == 210.5
    assert verified["object_type"] == "кафе"


def test_visit_rejects_mismatched_evidence_kind(client) -> None:
    finding_id, ev_dzk_id, _ = _seed_finding(client.session_factory)

    resp = client.post(
        "/api/inspector/visits",
        json={
            "finding_id": str(finding_id),
            "resolution": "resolved",
            "source_of_truth": "drrp",
            "truth_evidence_id": str(ev_dzk_id),
        },
    )
    assert resp.status_code == 400


def test_visit_upsert_overwrites_previous_verdict(client) -> None:
    finding_id, ev_dzk_id, ev_drrp_id = _seed_finding(client.session_factory)

    first = client.post(
        "/api/inspector/visits",
        json={
            "finding_id": str(finding_id),
            "resolution": "resolved",
            "source_of_truth": "dzk",
            "truth_evidence_id": str(ev_dzk_id),
        },
    )
    assert first.status_code == 200

    second = client.post(
        "/api/inspector/visits",
        json={
            "finding_id": str(finding_id),
            "resolution": "resolved",
            "source_of_truth": "drrp",
            "truth_evidence_id": str(ev_drrp_id),
        },
    )
    assert second.status_code == 200
    verified = second.json()["data"]["verified_asset"]
    assert verified["source_of_truth"] == "drrp"

    s = client.session_factory()
    try:
        rows = (
            s.query(VerifiedAssetRow)
            .filter(VerifiedAssetRow.finding_id == finding_id)
            .all()
        )
        assert len(rows) == 1
        assert rows[0].source_of_truth == "drrp"
    finally:
        s.close()


def test_inspector_detail_returns_note_and_hides_resolved(client) -> None:
    finding_id, _, _ = _seed_finding(client.session_factory, status="in_review")

    s = client.session_factory()
    try:
        row = s.get(FindingRow, finding_id)
        assert row is not None
        row.assignment_note = "Уточнити межі"
        row.assigned_at = datetime.now(tz=timezone.utc)
        s.commit()
    finally:
        s.close()

    resp = client.get(f"/api/inspector/findings/{finding_id}")
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["assignment_note"] == "Уточнити межі"
    assert len(data["evidence"]) == 2

    # Resolved findings are hidden from the inspector detail view.
    s = client.session_factory()
    try:
        row = s.get(FindingRow, finding_id)
        assert row is not None
        row.status = "resolved"
        s.commit()
    finally:
        s.close()

    resp = client.get(f"/api/inspector/findings/{finding_id}")
    assert resp.status_code == 404
