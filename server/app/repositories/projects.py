"""Every query on projects, builds and build events lives here."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Build, BuildEvent, Project

ACTIVE = ("queued", "building", "deploying")


class ProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def slug_exists(self, slug: str) -> bool:
        found = await self.session.scalar(select(Project.id).where(Project.slug == slug))
        return found is not None

    async def add(self, project: Project) -> Project:
        self.session.add(project)
        await self.session.flush()
        return project

    async def get(self, project_id: int, *, with_builds: bool = False) -> Project | None:
        stmt = select(Project).where(Project.id == project_id)
        if with_builds:
            stmt = stmt.options(selectinload(Project.builds))
        return await self.session.scalar(stmt)

    async def get_by_slug(self, slug: str) -> Project | None:
        return await self.session.scalar(
            select(Project).where(Project.slug == slug).options(selectinload(Project.builds))
        )

    async def list_recent(self, limit: int = 50) -> Sequence[Project]:
        stmt = (
            select(Project)
            .options(selectinload(Project.builds))
            .order_by(Project.updated_at.desc())
            .limit(limit)
        )
        return (await self.session.scalars(stmt)).all()

    async def delete(self, project: Project) -> None:
        await self.session.delete(project)


class BuildRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, build_id: int) -> Build | None:
        return await self.session.scalar(
            select(Build).where(Build.id == build_id).options(selectinload(Build.project))
        )

    async def next_number(self, project_id: int) -> int:
        current = await self.session.scalar(
            select(func.max(Build.number)).where(Build.project_id == project_id)
        )
        return (current or 0) + 1

    async def active_for_project(self, project_id: int) -> Build | None:
        return await self.session.scalar(
            select(Build).where(Build.project_id == project_id, Build.status.in_(ACTIVE))
        )

    async def last_session_id(self, project_id: int) -> str | None:
        """The Claude Code session of the last build that worked, for follow-ups."""
        return await self.session.scalar(
            select(Build.session_id)
            .where(
                Build.project_id == project_id,
                Build.status == "live",
                Build.session_id.is_not(None),
            )
            .order_by(Build.number.desc())
            .limit(1)
        )

    async def ids_with_status(self, *statuses: str) -> list[int]:
        rows = await self.session.scalars(
            select(Build.id).where(Build.status.in_(statuses)).order_by(Build.id)
        )
        return list(rows)

    async def fail_interrupted(self) -> int:
        """Builds that were running when the server stopped can't be resumed."""
        result = await self.session.execute(
            update(Build)
            .where(Build.status.in_(("building", "deploying")))
            .values(status="failed", error="The server restarted during this build.")
        )
        return result.rowcount or 0

    async def add_event(
        self, build_id: int, seq: int, type_: str, text: str, data: dict[str, Any] | None
    ) -> BuildEvent:
        event = BuildEvent(build_id=build_id, seq=seq, type=type_, text=text, data=data)
        self.session.add(event)
        await self.session.flush()
        return event

    async def events_after(self, build_id: int, after_seq: int) -> Sequence[BuildEvent]:
        stmt = (
            select(BuildEvent)
            .where(BuildEvent.build_id == build_id, BuildEvent.seq > after_seq)
            .order_by(BuildEvent.seq)
        )
        return (await self.session.scalars(stmt)).all()
