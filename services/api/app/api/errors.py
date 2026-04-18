"""Domain error types + global handler."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.envelope import err

_LOG = logging.getLogger("e_state.api")


class AppError(Exception):
    code: str = "INTERNAL"
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationError(AppError):
    code = "VALIDATION"
    status_code = status.HTTP_400_BAD_REQUEST


class NotFoundError(AppError):
    code = "NOT_FOUND"
    status_code = status.HTTP_404_NOT_FOUND


class ConflictError(AppError):
    code = "CONFLICT"
    status_code = status.HTTP_409_CONFLICT


class UnauthorizedError(AppError):
    code = "UNAUTHENTICATED"
    status_code = status.HTTP_401_UNAUTHORIZED


class ForbiddenError(AppError):
    code = "FORBIDDEN"
    status_code = status.HTTP_403_FORBIDDEN


class RateLimitError(AppError):
    code = "RATE_LIMIT"
    status_code = status.HTTP_429_TOO_MANY_REQUESTS


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    _LOG.info("app_error %s: %s", exc.code, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content=err(exc.code, exc.message, details=exc.details).model_dump(),
    )


async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=err(
            "VALIDATION",
            "Invalid request payload",
            details={"errors": exc.errors()},
        ).model_dump(),
    )


async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:  # pragma: no cover
    _LOG.exception("unhandled error")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=err("INTERNAL", "Internal server error").model_dump(),
    )
