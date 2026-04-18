from __future__ import annotations

from fastapi import APIRouter

from app.api.envelope import ApiResponse, ok

router = APIRouter(tags=["health"])


@router.get("/health", response_model=ApiResponse[dict])
async def health() -> ApiResponse[dict]:
    return ok({"status": "ok"})
