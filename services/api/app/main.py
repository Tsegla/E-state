"""FastAPI application entrypoint. Wires routers + exception handlers."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.errors import (
    AppError,
    app_error_handler,
    unhandled_error_handler,
    validation_error_handler,
)
from app.api.routers import ALL_ROUTERS
from app.config import get_settings
from app.db.session import init_db


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    app = FastAPI(
        title="E-State API",
        version=__version__,
        description="Data service for the E-State ОТГ asset-audit platform.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        # Hackathon convenience: Vercel deployment URLs change often.
        # Keep explicit origins, plus allow any *.vercel.app origin.
        allow_origin_regex=r"https://.*\.vercel\.app",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)

    for router in ALL_ROUTERS:
        app.include_router(router)

    @app.on_event("startup")
    def _startup() -> None:
        # Dev convenience: create tables if they don't exist. Prod uses Alembic.
        if not settings.is_production:
            init_db()

    return app


app = create_app()
