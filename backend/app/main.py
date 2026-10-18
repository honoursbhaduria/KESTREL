"""Main FastAPI application factory and router composition."""

from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import setup_logging
from app.modules.auth.router import router as auth_router
from app.modules.jobs.router import router as jobs_router
from app.modules.plans.router import router as plans_router
from app.modules.projects.router import router as projects_router
from app.modules.rules.router import router as rules_router
from app.modules.system_router import router as system_router

settings = get_settings()
setup_logging()

app = FastAPI(
    title="Haron API",
    version="0.1.0",
    description="AI Home Design Platform for Architects Backend API",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# Register exception handlers on the app
register_error_handlers(app)

# Middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(CorrelationIdMiddleware)

# Include routers with /api/v1 prefix
app.include_router(system_router)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(projects_router, prefix="/api/v1")
app.include_router(plans_router, prefix="/api/v1")
app.include_router(rules_router, prefix="/api/v1")
app.include_router(jobs_router, prefix="/api/v1")


@app.get("/metrics", tags=["system"])
async def metrics() -> Response:
    """Expose Prometheus formatted application metrics."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
