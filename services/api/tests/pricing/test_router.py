from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO

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
from app.db.models import Base, DatasetRow, LandParcelRow
from app.security.auth import Principal

ANALYST = Principal(subject="analyst@example.com", role="analyst")


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
        yield c

    engine.dispose()


def _seed_dataset(session_factory) -> str:
    s = session_factory()
    try:
        dataset = DatasetRow(
            label="Тестовий набір",
            status="matched",
            uploaded_at=datetime(2026, 4, 18, tzinfo=timezone.utc),
        )
        s.add(dataset)
        s.flush()
        s.add(
            LandParcelRow(
                dataset_id=dataset.id,
                cadastral_no="0000000000:00:000:0001",
                area_m2=100_000,
                valuation_kop=250_000_000,
                owner_tax_id="1234567890",
                intended_use_code="03.07",
                intended_use_label="Комерційне",
            )
        )
        s.commit()
        return str(dataset.id)
    finally:
        s.close()


def test_quote_for_dataset_returns_price(client) -> None:
    dataset_id = _seed_dataset(client.session_factory)
    response = client.get("/api/pricing/quote", params={"dataset_id": dataset_id})
    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    assert payload["dataset_id"] == dataset_id
    assert payload["yearly_price_uah"] >= 12000


def test_quote_upload_csv_works_without_auth_header(client) -> None:
    body = (
        "Кадастровий номер,ЄДРПОУ землекористувача,Площа, га,"
        "Усереднена нормативно грошова оцінка,Цільове призначення\n"
        "0000000000:00:000:0001,1234567890,10,100000,03.07 Комерційне\n"
    ).encode("utf-8")
    files = {"file": ("quote.csv", BytesIO(body), "text/csv")}
    response = client.post("/api/pricing/quote-upload", files=files)
    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    assert payload["dataset_id"] is None
    assert payload["total_parcels"] == 1
    assert payload["tier"] in {"base", "mid", "premium"}
