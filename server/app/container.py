"""Wires the app's objects together once at startup (a tiny dependency container).

Routes get services from here through ``app.api.deps``; tests build a container
with the ``FakeBuilder`` and a temp folder instead.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.agents.base import Builder
from app.agents.factory import build_builder
from app.core.config import Settings
from app.core.events import EventBus
from app.db.session import create_engine, create_session_factory
from app.deploy.base import Deployer
from app.deploy.factory import build_deployer
from app.services.build_runner import BuildRunner
from app.services.projects import ProjectService


@dataclass
class Container:
    settings: Settings
    engine: AsyncEngine
    session_factory: async_sessionmaker
    bus: EventBus
    builder: Builder
    deployer: Deployer
    runner: BuildRunner
    projects: ProjectService


def build_container(
    settings: Settings,
    *,
    builder: Builder | None = None,
    deployer: Deployer | None = None,
) -> Container:
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    bus = EventBus()
    builder = builder or build_builder(settings)
    deployer = deployer or build_deployer(settings)
    runner = BuildRunner(
        settings=settings,
        session_factory=session_factory,
        builder=builder,
        deployer=deployer,
        bus=bus,
    )
    return Container(
        settings=settings,
        engine=engine,
        session_factory=session_factory,
        bus=bus,
        builder=builder,
        deployer=deployer,
        runner=runner,
        projects=ProjectService(
            settings=settings,
            session_factory=session_factory,
            runner=runner,
            deployer=deployer,
            builder_name=builder.name,
        ),
    )
