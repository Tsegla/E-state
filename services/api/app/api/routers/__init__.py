from app.api.routers.citizen import router as citizen_router
from app.api.routers.datasets import router as datasets_router
from app.api.routers.findings import router as findings_router
from app.api.routers.health import router as health_router
from app.api.routers.inspector import router as inspector_router
from app.api.routers.matcher import router as matcher_router
from app.api.routers.reports import router as reports_router
from app.api.routers.upload import router as upload_router

ALL_ROUTERS = [
    health_router,
    upload_router,
    datasets_router,
    matcher_router,
    findings_router,
    inspector_router,
    citizen_router,
    reports_router,
]

__all__ = ["ALL_ROUTERS"]
