"""Audit log helper. Every sensitive operation goes through this."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import AuditLogRow


def _payload_hash(payload: dict[str, Any] | None) -> str:
    encoded = json.dumps(payload or {}, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def log_action(
    session: Session,
    *,
    actor: str,
    action: str,
    target_table: str,
    target_id: str,
    payload: dict[str, Any] | None = None,
) -> None:
    """Append an audit row. Payload is hashed (never stored raw) to avoid PII leakage."""
    session.add(
        AuditLogRow(
            actor=actor,
            action=action,
            target_table=target_table,
            target_id=target_id,
            payload_hash=_payload_hash(payload),
        )
    )
