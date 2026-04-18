"""Canonical enumerations used across the system.

Mirrored in [docs/data-model.md](../../../docs/data-model.md). When extending,
update the doc and the web ``types.ts`` in the same commit.
"""

from __future__ import annotations

from enum import StrEnum


class Severity(StrEnum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class FindingStatus(StrEnum):
    OPEN = "open"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class FindingType(StrEnum):
    LAND_NO_REAL_ESTATE = "LAND_NO_REAL_ESTATE"
    REAL_ESTATE_NO_LAND = "REAL_ESTATE_NO_LAND"
    USE_VS_OBJECT_MISMATCH = "USE_VS_OBJECT_MISMATCH"
    AREA_PORTFOLIO_DELTA = "AREA_PORTFOLIO_DELTA"
    OWNER_NAME_MISMATCH = "OWNER_NAME_MISMATCH"
    TERMINATED_BUT_ACTIVE = "TERMINATED_BUT_ACTIVE"
    MISSING_OWNER = "MISSING_OWNER"
    DUPLICATE_REGISTRATION = "DUPLICATE_REGISTRATION"


class DatasetStatus(StrEnum):
    INGESTING = "ingesting"
    MATCHED = "matched"
    FAILED = "failed"
