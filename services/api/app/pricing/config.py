"""Configuration for yearly OTG subscription pricing."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class PricingConfig:
    """Single source of tunable pricing coefficients."""

    base_land_tax_rate: float = 0.01
    indexation_year_coeff: float = 1.1
    purpose_multipliers: dict[str, float] = field(
        default_factory=lambda: {
            "agri": 1.0,
            "residential": 1.2,
            "commercial": 1.5,
            "industrial": 1.4,
            "other": 1.0,
        }
    )
    concentration_thresholds: tuple[tuple[float, float], ...] = (
        (0.70, 1.6),
        (0.50, 1.3),
        (0.0, 1.0),
    )
    subscription_share: float = 0.05
    subscription_floor_uah: float = 12_000.0
    subscription_cap_uah: float = 1_000_000.0
    fallback_ngo_uah_per_ha: float = 35_000.0
    missing_owner_sentinel: str = "__невідомо__"


def default_config() -> PricingConfig:
    return PricingConfig()
