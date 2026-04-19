from __future__ import annotations

from app.pricing.engine import compute_quote


def test_compute_quote_clips_negatives_and_normalizes_missing_owner() -> None:
    quote = compute_quote(
        [
            {
                "cadastral_no": "1000:11:111:1111",
                "owner_id": "null",
                "area_ha": "-5,2",
                "ngo_uah_per_ha": "-12000",
                "intended_use_code": "03.07",
            }
        ]
    )
    assert quote.total_parcels == 1
    assert quote.total_owners == 0
    assert quote.total_area_ha == 0.0
    assert quote.projected_recoverable_revenue_uah == 0.0
    assert quote.yearly_price_uah == 12_000.0


def test_compute_quote_dedupes_by_cadastral_when_present() -> None:
    quote = compute_quote(
        [
            {
                "cadastral_no": "1000:11:111:1111",
                "owner_id": "123",
                "area_ha": 10,
                "ngo_uah_per_ha": 10000,
                "intended_use_code": "01.01",
            },
            {
                "cadastral_no": "1000:11:111:1111",
                "owner_id": "123",
                "area_ha": 10,
                "ngo_uah_per_ha": 10000,
                "intended_use_code": "01.01",
            },
            {
                "cadastral_no": "2000:11:111:1111",
                "owner_id": "123",
                "area_ha": 2,
                "ngo_uah_per_ha": 10000,
                "intended_use_code": "01.01",
            },
        ]
    )
    assert quote.total_parcels == 2


def test_compute_quote_dedupes_mixed_cadastral_with_composite_fallback() -> None:
    quote = compute_quote(
        [
            {
                "cadastral_no": "1000:11:111:1111",
                "owner_id": "123",
                "area_ha": 1,
                "ngo_uah_per_ha": 10000,
                "intended_use_code": "01.01",
            },
            {
                "cadastral_no": None,
                "owner_id": "A",
                "area_ha": 2,
                "ngo_uah_per_ha": 15000,
                "intended_use_code": "01.01",
            },
            {
                "cadastral_no": None,
                "owner_id": "B",
                "area_ha": 3,
                "ngo_uah_per_ha": 17000,
                "intended_use_code": "03.07",
            },
        ]
    )
    assert quote.total_parcels == 3


def test_compute_quote_uses_concentration_tiers_and_cap() -> None:
    rows = [
        {
            "cadastral_no": "1000:11:111:1111",
            "owner_id": "big-owner",
            "area_ha": 80,
            "ngo_uah_per_ha": 200_000_000,
            "intended_use_code": "03.07",
        }
    ]
    for i in range(1, 10):
        rows.append(
            {
                "cadastral_no": f"1000:11:111:{i+1111}",
                "owner_id": f"owner-{i}",
                "area_ha": 2.2222,
                "ngo_uah_per_ha": 100_000,
                "intended_use_code": "01.01",
            }
        )

    quote = compute_quote(rows)
    assert quote.concentration_multiplier == 1.6
    assert quote.tier == "premium"
    assert quote.top10_percent_area_share > 0.7
    assert quote.yearly_price_uah == 1_000_000.0
