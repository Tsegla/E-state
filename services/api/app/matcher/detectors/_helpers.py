"""Shared helpers for detectors. Keep pure: no DB, no HTTP."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import pandas as pd

from app.matcher.draft import EvidenceRef


def land_evidence(row: pd.Series) -> EvidenceRef:
    return EvidenceRef(
        kind="land_parcel",
        ref_id=UUID(str(row["id"])) if not isinstance(row["id"], UUID) else row["id"],
        snapshot={
            "cadastral_no": row.get("cadastral_no"),
            "intended_use_code": row.get("intended_use_code"),
            "intended_use_label": row.get("intended_use_label"),
            "area_m2": float(row.get("area_m2") or 0.0),
            "location_admin": row.get("location_admin"),
        },
    )


def real_estate_evidence(row: pd.Series) -> EvidenceRef:
    return EvidenceRef(
        kind="real_estate",
        ref_id=UUID(str(row["id"])) if not isinstance(row["id"], UUID) else row["id"],
        snapshot={
            "object_type_norm": row.get("object_type_norm"),
            "object_type_raw": row.get("object_type_raw"),
            "address_raw": row.get("address_raw"),
            "area_m2": float(row.get("area_m2") or 0.0),
            "terminated_at": row.get("terminated_at").isoformat()
            if row.get("terminated_at") is not None and not pd.isna(row.get("terminated_at"))
            else None,
        },
    )


def to_python_scalar(v: Any) -> Any:
    """Best-effort conversion for dict metrics (JSON-friendly)."""
    if v is None:
        return None
    if isinstance(v, float | int | str | bool):
        return v
    if hasattr(v, "item"):
        try:
            return v.item()
        except Exception:
            return v
    if hasattr(v, "isoformat"):
        try:
            return v.isoformat()
        except Exception:
            return str(v)
    return str(v)
