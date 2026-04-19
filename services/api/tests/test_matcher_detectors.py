"""Golden-set tests for the matcher detectors.

These use tiny in-memory frames to keep tests fast and deterministic.
"""

from __future__ import annotations

from uuid import uuid4

import pandas as pd
import pytest

from app.domain.enums import FindingType, Severity
from app.matcher.config import default_config
from app.matcher.context import MatcherContext
from app.matcher.detectors import REGISTRY


def _ctx(zem_rows: list[dict], ner_rows: list[dict]) -> MatcherContext:
    return MatcherContext(
        dataset_id=uuid4(),
        zem=pd.DataFrame(zem_rows),
        ner=pd.DataFrame(ner_rows),
        persons=pd.DataFrame(),
        config=default_config(),
    )


def _land_row(**overrides) -> dict:
    row = {
        "id": uuid4(),
        "cadastral_no": "1234567890:01:002:0003",
        "owner_tax_id": "1234567890",
        "owner_name_raw": "Хоцевич Григорій",
        "intended_use_code": "02.01",
        "intended_use_label": "Для будівництва і обслуговування жилого будинку",
        "area_m2": 1500.0,
        "location_admin": "с. Лисятичі",
    }
    row.update(overrides)
    return row


def _estate_row(**overrides) -> dict:
    row = {
        "id": uuid4(),
        "owner_tax_id": "1234567890",
        "owner_name_raw": "Хоцевич Григорій",
        "object_type_raw": "Житловий будинок",
        "object_type_norm": "житловий_будинок",
        "address_raw": "с. Лисятичі",
        "area_m2": 120.0,
        "terminated_at": pd.NaT,
    }
    row.update(overrides)
    return row


def test_land_no_real_estate_fires_when_no_residential_object() -> None:
    ctx = _ctx([_land_row()], [])
    drafts = REGISTRY["LAND_NO_REAL_ESTATE"](ctx)
    assert len(drafts) == 1
    assert drafts[0].finding_type is FindingType.LAND_NO_REAL_ESTATE
    assert drafts[0].severity is Severity.WARNING
    assert drafts[0].computed_metrics["residential_parcels"] == 1


def test_land_no_real_estate_suppressed_when_house_present() -> None:
    ctx = _ctx([_land_row()], [_estate_row()])
    drafts = REGISTRY["LAND_NO_REAL_ESTATE"](ctx)
    assert drafts == []


def test_land_no_real_estate_not_satisfied_by_apartment() -> None:
    """An apartment sits on OSBB land, not on the owner's 02.01 plot."""
    ctx = _ctx(
        [_land_row()],
        [
            _estate_row(
                object_type_raw="Квартира",
                object_type_norm="квартира",
                address_raw="м. Львів, вул. Шевченка 150, кв. 9",
            )
        ],
    )
    drafts = REGISTRY["LAND_NO_REAL_ESTATE"](ctx)
    assert len(drafts) == 1
    assert drafts[0].finding_type is FindingType.LAND_NO_REAL_ESTATE


def test_area_portfolio_delta_flags_critical_over_ratio() -> None:
    """100 м² plot + 500 м² ``житловий_будинок`` → ratio 5 > critical=1.75."""
    ctx = _ctx(
        [_land_row(area_m2=100.0)],
        [_estate_row(area_m2=500.0)],
    )
    drafts = REGISTRY["AREA_PORTFOLIO_DELTA"](ctx)
    assert len(drafts) == 1
    assert drafts[0].severity is Severity.CRITICAL
    assert drafts[0].computed_metrics["ratio"] == 5.0


def test_area_portfolio_delta_ignores_apartments() -> None:
    """Garage plot (27 m²) + flat (95.8 m²) was the canonical false-positive.

    Flats live on OSBB/community land, so they must not count against the
    owner's personal land portfolio.
    """
    ctx = _ctx(
        [_land_row(intended_use_code="02.05", area_m2=27.0)],
        [
            _estate_row(
                object_type_raw="Квартира",
                object_type_norm="квартира",
                area_m2=95.8,
            )
        ],
    )
    drafts = REGISTRY["AREA_PORTFOLIO_DELTA"](ctx)
    assert drafts == []


def test_area_portfolio_delta_ignores_non_residential_premises() -> None:
    ctx = _ctx(
        [_land_row(area_m2=100.0)],
        [
            _estate_row(
                object_type_raw="Нежитлове приміщення",
                object_type_norm="нежитлове_приміщення",
                area_m2=400.0,
            )
        ],
    )
    drafts = REGISTRY["AREA_PORTFOLIO_DELTA"](ctx)
    assert drafts == []


def test_terminated_but_active_requires_no_active_record() -> None:
    ctx = _ctx(
        [_land_row()],
        [_estate_row(terminated_at=pd.Timestamp("2020-01-01"))],
    )
    drafts = REGISTRY["TERMINATED_BUT_ACTIVE"](ctx)
    assert len(drafts) == 1
    assert drafts[0].severity is Severity.CRITICAL


def test_terminated_but_active_suppressed_when_active_record_also_exists() -> None:
    ctx = _ctx(
        [_land_row()],
        [
            _estate_row(terminated_at=pd.Timestamp("2020-01-01")),
            _estate_row(id=uuid4()),  # active
        ],
    )
    drafts = REGISTRY["TERMINATED_BUT_ACTIVE"](ctx)
    assert drafts == []


def test_missing_owner_flags_orphan_parcel() -> None:
    ctx = _ctx(
        [_land_row(owner_tax_id=None, owner_name_raw=None)],
        [],
    )
    drafts = REGISTRY["MISSING_OWNER"](ctx)
    assert len(drafts) == 1
    assert drafts[0].severity is Severity.WARNING


def test_duplicate_registration_flags_same_cad_different_owners() -> None:
    ctx = _ctx(
        [
            _land_row(owner_tax_id="1111111111", id=uuid4()),
            _land_row(owner_tax_id="2222222222", id=uuid4()),
        ],
        [],
    )
    drafts = REGISTRY["DUPLICATE_REGISTRATION"](ctx)
    assert len(drafts) == 1
    assert drafts[0].severity is Severity.CRITICAL
    assert drafts[0].computed_metrics["distinct_owners"] == 2


def test_owner_name_mismatch_flags_large_delta() -> None:
    ctx = _ctx(
        [_land_row(owner_name_raw="ТОВ Альфа")],
        [_estate_row(owner_name_raw="ПП Beta Inc.")],
    )
    drafts = REGISTRY["OWNER_NAME_MISMATCH"](ctx)
    assert len(drafts) == 1
    assert drafts[0].computed_metrics["similarity"] < 0.85


def test_owner_name_mismatch_suppressed_on_near_match() -> None:
    ctx = _ctx(
        [_land_row(owner_name_raw="Хоцевич Григорій Іванович")],
        [_estate_row(owner_name_raw="Хоцевич Григорій")],
    )
    drafts = REGISTRY["OWNER_NAME_MISMATCH"](ctx)
    assert drafts == []


def test_use_vs_object_mismatch_fires_on_industrial_object_on_residential_land() -> None:
    ctx = _ctx(
        [_land_row()],  # residential
        [_estate_row(object_type_norm="промислова_будівля")],  # industrial, active
    )
    drafts = REGISTRY["USE_VS_OBJECT_MISMATCH"](ctx)
    assert len(drafts) == 1


def test_terminated_rights_mismatch_one_per_owner() -> None:
    """Aggregate all terminated rows for one owner into a single finding.

    The pre-April-2026 version emitted one finding per terminated row, which
    swamped inspectors when a person had e.g. three sold flats.
    """
    ctx = _ctx(
        [_land_row()],
        [
            _estate_row(terminated_at=pd.Timestamp("2022-03-01")),
            _estate_row(id=uuid4(), terminated_at=pd.Timestamp("2023-05-01")),
            _estate_row(id=uuid4(), terminated_at=pd.Timestamp("2024-07-01")),
            _estate_row(id=uuid4()),  # still active — must not affect the count
        ],
    )
    drafts = REGISTRY["TERMINATED_RIGHTS_MISMATCH"](ctx)
    assert len(drafts) == 1
    draft = drafts[0]
    assert draft.severity is Severity.WARNING
    assert draft.computed_metrics["terminated_count"] == 3
    assert draft.computed_metrics["last_termination_at"] == "2024-07-01T00:00:00"
    assert draft.computed_metrics["land_status"] == "active"


def test_land_no_garage_fires_when_no_garage_object() -> None:
    ctx = _ctx(
        [_land_row(intended_use_code="02.05", area_m2=27.0)],
        [],
    )
    drafts = REGISTRY["LAND_NO_GARAGE"](ctx)
    assert len(drafts) == 1
    assert drafts[0].finding_type is FindingType.LAND_NO_GARAGE
    assert drafts[0].severity is Severity.WARNING
    assert drafts[0].computed_metrics["garage_parcels"] == 1
    assert drafts[0].computed_metrics["total_garage_m2"] == 27.0


def test_land_no_garage_suppressed_when_garage_present() -> None:
    ctx = _ctx(
        [_land_row(intended_use_code="02.05", area_m2=27.0)],
        [
            _estate_row(
                object_type_raw="Гараж",
                object_type_norm="гараж",
                area_m2=24.0,
            )
        ],
    )
    drafts = REGISTRY["LAND_NO_GARAGE"](ctx)
    assert drafts == []


def test_land_no_garage_ignored_when_only_flat_present() -> None:
    """A flat does not satisfy the "garage on this plot" requirement."""
    ctx = _ctx(
        [_land_row(intended_use_code="02.05", area_m2=27.0)],
        [_estate_row(object_type_raw="Квартира", object_type_norm="квартира")],
    )
    drafts = REGISTRY["LAND_NO_GARAGE"](ctx)
    assert len(drafts) == 1


def test_real_estate_no_land_fires_when_no_matching_parcel() -> None:
    ctx = _ctx(
        [],
        [_estate_row()],
    )
    drafts = REGISTRY["REAL_ESTATE_NO_LAND"](ctx)
    assert len(drafts) == 1
    assert drafts[0].severity is Severity.WARNING
