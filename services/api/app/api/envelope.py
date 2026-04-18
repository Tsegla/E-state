"""Consistent response envelope for all endpoints."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Meta(BaseModel):
    total: int
    page: int = 1
    limit: int = 50


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T
    meta: Meta | None = None


class ApiErrorDetails(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None
    trace_id: str | None = None


class ApiErrorResponse(BaseModel):
    success: bool = False
    error: ApiErrorDetails


def ok(data: T, *, meta: Meta | None = None) -> ApiResponse[T]:
    return ApiResponse[T](data=data, meta=meta)


def err(
    code: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
    trace_id: str | None = None,
) -> ApiErrorResponse:
    return ApiErrorResponse(
        error=ApiErrorDetails(code=code, message=message, details=details, trace_id=trace_id)
    )


class Paginated(BaseModel, Generic[T]):
    items: list[T] = Field(default_factory=list)
