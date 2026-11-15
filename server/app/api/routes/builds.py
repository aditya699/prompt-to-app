"""Builds: look one up, follow its log live, cancel it."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.api.deps import ContainerDep
from app.container import Container
from app.core.errors import ConflictError, NotFoundError
from app.core.events import CLOSED
from app.core.sse import format_sse, sse_response
from app.repositories.projects import ACTIVE, BuildRepository
from app.schemas.project import BuildEventOut, BuildOut

router = APIRouter(prefix="/builds", tags=["builds"])

# A comment line every so often keeps proxies from closing a quiet stream.
KEEPALIVE_SECONDS = 15


@router.get("/{build_id}")
async def get_build(build_id: int, container: ContainerDep) -> BuildOut:
    async with container.session_factory() as session:
        build = await BuildRepository(session).get(build_id)
    if build is None:
        raise NotFoundError(f"Build {build_id} not found.")
    return BuildOut.model_validate(build)


@router.get("/{build_id}/events")
async def build_events(
    build_id: int,
    container: ContainerDep,
    after: int = Query(default=0, ge=0, description="Only send events after this seq"),
) -> StreamingResponse:
    """The build log as Server-Sent Events: saved lines first, then live ones.

    The stream ends after an event of type ``done``. Reconnect with ``?after=<last seq>``.
    """
    async with container.session_factory() as session:
        if await BuildRepository(session).get(build_id) is None:
            raise NotFoundError(f"Build {build_id} not found.")
    return sse_response(_follow(container, build_id, after))


async def _follow(container: Container, build_id: int, after: int) -> AsyncIterator[str]:
    # Subscribe before reading the saved log, so nothing lands in the gap between.
    async with container.bus.subscribe(build_id) as queue:
        async with container.session_factory() as session:
            repo = BuildRepository(session)
            build = await repo.get(build_id)
            saved = await repo.events_after(build_id, after)
        last = after
        for row in saved:
            yield format_sse(BuildEventOut.model_validate(row))
            last = row.seq
            if row.type == "done":
                return
        if build is None or build.status not in ACTIVE:
            return
        while True:
            try:
                item = await asyncio.wait_for(queue.get(), KEEPALIVE_SECONDS)
            except TimeoutError:
                yield ": keepalive\n\n"
                continue
            if item is CLOSED:
                return
            if item["seq"] <= last:
                continue
            last = item["seq"]
            yield format_sse(BuildEventOut.model_validate(item))
            if item["type"] == "done":
                return


@router.post("/{build_id}/cancel")
async def cancel_build(build_id: int, container: ContainerDep) -> BuildOut:
    if not await container.runner.cancel(build_id):
        raise ConflictError("This build has already finished.")
    return await get_build(build_id, container)
