"""The build queue: runs the agent, deploys the result, records every step.

One VM runs MAX_CONCURRENT_BUILDS builds at a time (1 by default: Claude Code
plus `npm install` is heavy for a small machine). Each build:

1. queued    -> waits for a free worker
2. building  -> the Builder writes the app into var/workspaces/<slug>
3. deploying -> the Deployer publishes dist/ and returns the URL
4. live      -> the project's URL now serves the new version
   (or failed / cancelled, with the reason saved on the build)

Every log line is saved to the database and published on the EventBus, so the
browser can follow a build live and replay it after a reload.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.agents.base import AgentEvent, Builder, BuildOutcome, BuildRequest
from app.core.config import Settings
from app.core.errors import AppError, BuildError
from app.core.events import EventBus
from app.db.base import utcnow
from app.deploy.base import Deployer, find_build_output
from app.repositories.projects import BuildRepository

logger = logging.getLogger(__name__)


class BuildLog:
    """Numbers, saves and publishes the log lines of one build."""

    def __init__(self, build_id: int, session_factory: async_sessionmaker, bus: EventBus) -> None:
        self.build_id = build_id
        self.session_factory = session_factory
        self.bus = bus
        self.seq = 0

    async def emit(self, event: AgentEvent) -> None:
        await self._write(event.type, event.text, event.data)

    async def done(self, status: str, text: str, **data: Any) -> None:
        await self._write("done", text, {"status": status, **data})

    async def _write(self, type_: str, text: str, data: dict[str, Any] | None) -> None:
        self.seq += 1
        async with self.session_factory() as session:
            row = await BuildRepository(session).add_event(
                self.build_id, self.seq, type_, text, data
            )
            await session.commit()
        self.bus.publish(
            self.build_id,
            {
                "seq": row.seq,
                "type": row.type,
                "text": row.text,
                "data": row.data,
                "created_at": row.created_at.isoformat(),
            },
        )


class BuildRunner:
    def __init__(
        self,
        *,
        settings: Settings,
        session_factory: async_sessionmaker,
        builder: Builder,
        deployer: Deployer,
        bus: EventBus,
    ) -> None:
        self.settings = settings
        self.session_factory = session_factory
        self.builder = builder
        self.deployer = deployer
        self.bus = bus
        self._queue: asyncio.Queue[int] = asyncio.Queue()
        self._workers: list[asyncio.Task[None]] = []
        self._running: dict[int, asyncio.Task[None]] = {}
        self._cancel_requested: set[int] = set()

    # --- lifecycle -------------------------------------------------------------

    async def start(self) -> None:
        async with self.session_factory() as session:
            repo = BuildRepository(session)
            interrupted = await repo.fail_interrupted()
            queued = await repo.ids_with_status("queued")
            await session.commit()
        if interrupted:
            logger.warning("Marked %d interrupted build(s) as failed.", interrupted)
        for build_id in queued:
            self.enqueue(build_id)
        self._workers = [
            asyncio.create_task(self._worker(), name=f"build-worker-{i}")
            for i in range(self.settings.max_concurrent_builds)
        ]

    async def stop(self) -> None:
        for worker in self._workers:
            worker.cancel()
        for worker in self._workers:
            with contextlib.suppress(asyncio.CancelledError):
                await worker
        self._workers = []

    async def wait_idle(self) -> None:
        """Wait until every queued build has finished (tests use this)."""
        await self._queue.join()

    # --- public API ------------------------------------------------------------

    def enqueue(self, build_id: int) -> None:
        self._queue.put_nowait(build_id)

    def is_running(self, build_id: int) -> bool:
        return build_id in self._running

    async def cancel(self, build_id: int) -> bool:
        """Cancel a queued or running build. Returns False if it had already finished."""
        task = self._running.get(build_id)
        if task is not None:
            self._cancel_requested.add(build_id)
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await asyncio.wait({task})
            return True
        async with self.session_factory() as session:
            build = await BuildRepository(session).get(build_id)
            if build is None or build.status != "queued":
                return False
            build.status = "cancelled"
            build.finished_at = utcnow()
            await session.commit()
        await BuildLog(build_id, self.session_factory, self.bus).done(
            "cancelled", "Cancelled before it started."
        )
        self.bus.close(build_id)
        return True

    # --- the work --------------------------------------------------------------

    async def _worker(self) -> None:
        while True:
            build_id = await self._queue.get()
            task = asyncio.create_task(self._run(build_id), name=f"build-{build_id}")
            self._running[build_id] = task
            try:
                await asyncio.wait({task})
            finally:
                self._running.pop(build_id, None)
                if not task.done():  # the worker itself was cancelled (shutdown)
                    task.cancel()
                self._queue.task_done()

    async def _run(self, build_id: int) -> None:
        log = BuildLog(build_id, self.session_factory, self.bus)
        outcome: BuildOutcome | None = None
        try:
            request, slug = await self._claim(build_id)
            if request is None:
                return
            async with asyncio.timeout(self.settings.build_timeout_seconds):
                outcome = await self.builder.build(request, log.emit)
            if not outcome.ok:
                raise BuildError(outcome.error or "The build failed.")
            output = find_build_output(request.workspace)
            if output is None:
                raise BuildError("The agent finished, but there is no index.html to deploy.")

            await self._update(build_id, status="deploying")
            await log.emit(AgentEvent("status", "Deploying"))
            url = await self.deployer.deploy(slug, output)
            await self._finish(build_id, "live", outcome, url=url)
            await log.done("live", f"Live at {url}", url=url, summary=outcome.summary)
            logger.info("Build %d live at %s", build_id, url)
        except asyncio.CancelledError:
            if build_id not in self._cancel_requested:
                raise  # server shutdown; start() marks it failed next time
            self._cancel_requested.discard(build_id)
            await self._finish(build_id, "cancelled", outcome, error="Cancelled.")
            await log.done("cancelled", "Build cancelled.")
        except TimeoutError:
            message = f"The build took longer than {self.settings.build_timeout_seconds}s."
            await self._fail(build_id, log, outcome, message)
        except AppError as exc:
            await self._fail(build_id, log, outcome, exc.message)
        except Exception as exc:
            logger.exception("Build %d crashed", build_id)
            await self._fail(build_id, log, outcome, f"Unexpected error: {exc}")
        finally:
            self.bus.close(build_id)

    async def _claim(self, build_id: int) -> tuple[BuildRequest | None, str]:
        """Mark a queued build as building and gather what the builder needs."""
        async with self.session_factory() as session:
            repo = BuildRepository(session)
            build = await repo.get(build_id)
            if build is None or build.status != "queued":
                return None, ""
            project = build.project
            build.status = "building"
            build.started_at = utcnow()
            project.status = "building"
            resume = await repo.last_session_id(project.id) if build.number > 1 else None
            workspace = self.settings.workspaces_dir / project.slug
            workspace.mkdir(parents=True, exist_ok=True)
            request = BuildRequest(
                prompt=build.prompt,
                workspace=workspace,
                project_name=project.name,
                resume_session_id=resume,
                is_followup=build.number > 1,
            )
            await session.commit()
            return request, project.slug

    async def _update(self, build_id: int, **values: Any) -> None:
        async with self.session_factory() as session:
            build = await BuildRepository(session).get(build_id)
            if build is not None:
                for key, value in values.items():
                    setattr(build, key, value)
                await session.commit()

    async def _finish(
        self,
        build_id: int,
        status: str,
        outcome: BuildOutcome | None,
        *,
        url: str | None = None,
        error: str | None = None,
    ) -> None:
        async with self.session_factory() as session:
            build = await BuildRepository(session).get(build_id)
            if build is None:
                return
            build.status = status
            build.error = error
            build.finished_at = utcnow()
            if outcome is not None:
                build.session_id = outcome.session_id
                build.cost_usd = outcome.cost_usd
                build.turns = outcome.turns
            project = build.project
            if status == "live":
                project.status, project.url = "live", url
            else:
                # A failed follow-up leaves the previous version online.
                project.status = "live" if project.url else "failed"
            project.updated_at = utcnow()
            await session.commit()

    async def _fail(
        self, build_id: int, log: BuildLog, outcome: BuildOutcome | None, message: str
    ) -> None:
        logger.warning("Build %d failed: %s", build_id, message)
        await self._finish(build_id, "failed", outcome, error=message)
        await log.emit(AgentEvent("error", message))
        await log.done("failed", message)
