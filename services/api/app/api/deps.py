"""FastAPI dependencies for auth + DB session."""

from __future__ import annotations

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.api.errors import ForbiddenError, UnauthorizedError
from app.db.session import get_session
from app.security.auth import Principal, decode_token


def session_dep() -> Session:  # pragma: no cover - tiny shim
    yield from get_session()


def _decode_bearer(authorization: str | None) -> Principal:
    if not authorization:
        raise UnauthorizedError("Missing Authorization header")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise UnauthorizedError("Invalid Authorization header")
    try:
        return decode_token(parts[1])
    except ValueError as exc:
        raise UnauthorizedError("Invalid or expired token") from exc


def current_user(authorization: str | None = Header(default=None)) -> Principal:
    return _decode_bearer(authorization)


def require_analyst(principal: Principal = Depends(current_user)) -> Principal:
    if not principal.is_analyst:
        raise ForbiddenError("Analyst role required")
    return principal


def require_inspector(principal: Principal = Depends(current_user)) -> Principal:
    if not principal.is_inspector:
        raise ForbiddenError("Inspector role required")
    return principal
