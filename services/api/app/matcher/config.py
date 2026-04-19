"""Single source of truth for matcher thresholds and rate tables.

Never hardcode these values elsewhere. See [docs/data-matcher-spec.md §4](../../../docs/data-matcher-spec.md).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class MatcherConfig:
    # Fuzzy-matching thresholds (rapidfuzz token_set_ratio / 100)
    name_fuzz_min: float = 0.92
    owner_name_mismatch_max: float = 0.85

    # Area portfolio ratios. Calibrated 2026-04 after false-positives on
    # apartment+garage portfolios: a typical multi-storey house already has
    # ratio > 1 (interior area > plot footprint), so 1.0 was too sensitive.
    area_portfolio_ratio_critical: float = 1.75
    area_portfolio_ratio_warning: float = 1.25

    # Intended-use code taxonomy
    residential_use_codes: tuple[str, ...] = ("02.01", "02.03")
    garage_use_codes: tuple[str, ...] = ("02.05",)
    commercial_use_codes: tuple[str, ...] = ("03.07",)
    industrial_use_codes: tuple[str, ...] = ("11.02", "11.04")
    agri_use_codes: tuple[str, ...] = ("01.01", "01.03", "01.04", "01.05", "01.06")

    # Object-type taxonomy (canonical normalized values)
    residential_object_types: tuple[str, ...] = ("квартира", "житловий_будинок")
    # A house is the only object that legally "closes" a 02.01/02.03 plot —
    # an apartment sits on OSBB land, not on the owner's plot.
    house_object_types: tuple[str, ...] = ("житловий_будинок",)
    garage_object_types: tuple[str, ...] = ("гараж",)
    commercial_object_types: tuple[str, ...] = (
        "нежитлова_будівля",
        "нежитлове_приміщення",
        "торгова_будівля",
        "офісна_будівля",
    )
    industrial_object_types: tuple[str, ...] = ("промислова_будівля",)
    # Objects whose area meaningfully compares to the plot they sit on.
    # Apartments and non-residential premises are excluded because the land
    # under them belongs to the building's common ownership (ОСББ/community),
    # not to the individual owner of the unit.
    area_comparable_object_types: tuple[str, ...] = (
        "житловий_будинок",
        "нежитлова_будівля",
        "гараж",
        "торгова_будівля",
        "офісна_будівля",
        "промислова_будівля",
    )

    # Budget impact rates (UAH / m² / year). Source-linked in docs/roadmap.md.
    housing_rate_uah_per_m2_per_year: float = 6.0
    commercial_rate_uah_per_m2_per_year: float = 72.0
    agri_rate_uah_per_m2_per_year: float = 0.40

    # Enabled detectors (used for partial reruns/tests)
    enabled_detectors: tuple[str, ...] = field(
        default_factory=lambda: (
            "LAND_NO_REAL_ESTATE",
            "LAND_NO_GARAGE",
            "REAL_ESTATE_NO_LAND",
            "USE_VS_OBJECT_MISMATCH",
            "AREA_PORTFOLIO_DELTA",
            "OWNER_NAME_MISMATCH",
            "TERMINATED_BUT_ACTIVE",
            "TERMINATED_RIGHTS_MISMATCH",
            "MISSING_OWNER",
            "DUPLICATE_REGISTRATION",
        )
    )


def default_config() -> MatcherConfig:
    return MatcherConfig()
