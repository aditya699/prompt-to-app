"""FastAPI entry point: ``uv run uvicorn app.main:app --reload``."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import builds, health, projects
from app.container import Container, build_container
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.logging import configure_logging
from app.db.session import init_db

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None, container: Container | None = None) -> FastAPI:
    """Build the app. Tests pass their own ``container`` (fake builder, temp folders)."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    settings.sites_dir.mkdir(parents=True, exist_ok=True)
    settings.workspaces_dir.mkdir(parents=True, exist_ok=True)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.container = container or build_container(settings)
        await init_db(app.state.container.engine)
        await app.state.container.runner.start()
        logger.info(
            "%s ready (builder=%s, deployer=%s, apps at %s)",
            settings.app_name,
            app.state.container.builder.name,
            app.state.container.deployer.name,
            settings.app_url("<slug>"),
        )
        yield
        await app.state.container.runner.stop()
        await app.state.container.engine.dispose()

    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    for module in (health, projects, builds):
        app.include_router(module.router, prefix="/api")

    # Deployed apps. On a VM, Caddy serves this folder on subdomains instead.
    app.mount("/apps", StaticFiles(directory=settings.sites_dir, html=True), name="apps")
    return app


app = create_app()
