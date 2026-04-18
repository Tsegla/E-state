"""Pure detector functions. Each accepts a ``MatcherContext`` and returns a list of drafts."""

from collections.abc import Callable

from app.matcher.context import MatcherContext
from app.matcher.detectors.area_portfolio_delta import detect_area_portfolio_delta
from app.matcher.detectors.duplicate_registration import detect_duplicate_registration
from app.matcher.detectors.land_no_real_estate import detect_land_no_real_estate
from app.matcher.detectors.missing_owner import detect_missing_owner
from app.matcher.detectors.owner_name_mismatch import detect_owner_name_mismatch
from app.matcher.detectors.real_estate_no_land import detect_real_estate_no_land
from app.matcher.detectors.terminated_but_active import detect_terminated_but_active
from app.matcher.detectors.use_vs_object_mismatch import detect_use_vs_object_mismatch
from app.matcher.draft import FindingDraft

DetectorFn = Callable[[MatcherContext], list[FindingDraft]]

REGISTRY: dict[str, DetectorFn] = {
    "LAND_NO_REAL_ESTATE": detect_land_no_real_estate,
    "REAL_ESTATE_NO_LAND": detect_real_estate_no_land,
    "USE_VS_OBJECT_MISMATCH": detect_use_vs_object_mismatch,
    "AREA_PORTFOLIO_DELTA": detect_area_portfolio_delta,
    "OWNER_NAME_MISMATCH": detect_owner_name_mismatch,
    "TERMINATED_BUT_ACTIVE": detect_terminated_but_active,
    "MISSING_OWNER": detect_missing_owner,
    "DUPLICATE_REGISTRATION": detect_duplicate_registration,
}

__all__ = ["REGISTRY", "DetectorFn"]
