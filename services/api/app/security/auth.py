"""Minimal JWT helper for the hackathon demo.

Production deployments should swap this for an OIDC integration (Дія.Підпис,
Azure AD, Keycloak). The ``Principal`` type is what the rest of the code sees.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from app.config import get_settings


@dataclass(frozen=True, slots=True)
class Principal:
    subject: str
    role: str
    community: str | None = None

    @property
    def is_analyst(self) -> bool:
        return self.role in {"analyst", "admin"}

    @property
    def is_inspector(self) -> bool:
        return self.role in {"inspector", "admin"}

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


def create_access_token(principal: Principal, expires_in_minutes: int | None = None) -> str:
    settings = get_settings()
    expire = datetime.now(tz=timezone.utc) + timedelta(
        minutes=expires_in_minutes or settings.jwt_expire_minutes
    )
    payload: dict[str, Any] = {
        "sub": principal.subject,
        "role": principal.role,
        "community": principal.community,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> Principal:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:  # pragma: no cover - exercised via deps
        raise ValueError("invalid token") from exc
    subject = payload.get("sub")
    role = payload.get("role")
    if not subject or not role:
        raise ValueError("invalid token payload")
    return Principal(subject=str(subject), role=str(role), community=payload.get("community"))
