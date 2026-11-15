"""Shared fixtures: an app wired to temp folders, a temp SQLite file and the fake builder."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest

from app.agents.fake import FakeBuilder
from app.container import Container, build_container
from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        database_url=f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}",
        builder="fake",
        workspaces_dir=tmp_path / "workspaces",
        sites_dir=tmp_path / "sites",
        public_base_url="http://test",
    )


@pytest.fixture
def builder() -> FakeBuilder:
    return FakeBuilder(step_delay=0, fail_on="please fail")


@pytest.fixture
def container(settings: Settings, builder: FakeBuilder) -> Container:
    return build_container(settings, builder=builder)


@pytest.fixture
async def client(settings: Settings, container: Container) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(settings, container)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
            yield http


def parse_sse(body: str) -> list[dict]:
    events = []
    for block in body.strip().split("\n\n"):
        data = [line[6:] for line in block.splitlines() if line.startswith("data: ")]
        if data:
            events.append(json.loads(data[0]))
    return events
