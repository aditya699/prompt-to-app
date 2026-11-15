"""Use cases for projects: create one, ask for a change, list, delete."""

from __future__ import annotations

import asyncio
import shutil
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import Settings
from app.core.errors import ConflictError, NotFoundError
from app.db.models import Build, Project
from app.deploy.base import Deployer
from app.repositories.projects import BuildRepository, ProjectRepository
from app.services.build_runner import BuildRunner
from app.services.naming import project_name, slugify, with_suffix


class ProjectService:
    def __init__(
        self,
        *,
        settings: Settings,
        session_factory: async_sessionmaker,
        runner: BuildRunner,
        deployer: Deployer,
        builder_name: str,
    ) -> None:
        self.settings = settings
        self.session_factory = session_factory
        self.runner = runner
        self.deployer = deployer
        self.builder_name = builder_name

    async def create(self, prompt: str, name: str | None = None) -> Project:
        name = (name or "").strip() or project_name(prompt)
        async with self.session_factory() as session:
            projects = ProjectRepository(session)
            slug = with_suffix(slugify(name))
            while await projects.slug_exists(slug):
                slug = with_suffix(slugify(name))
            project = await projects.add(
                Project(slug=slug, name=name, prompt=prompt.strip(), status="building")
            )
            build = Build(
                project_id=project.id, number=1, prompt=prompt.strip(), builder=self.builder_name
            )
            session.add(build)
            await session.commit()
            build_id, project_id = build.id, project.id
        self.runner.enqueue(build_id)
        return await self.get(project_id)

    async def request_change(self, project_id: int, prompt: str) -> Build:
        async with self.session_factory() as session:
            project = await ProjectRepository(session).get(project_id)
            if project is None:
                raise NotFoundError(f"Project {project_id} not found.")
            builds = BuildRepository(session)
            if await builds.active_for_project(project_id):
                raise ConflictError("A build is already running for this project.")
            build = Build(
                project_id=project_id,
                number=await builds.next_number(project_id),
                prompt=prompt.strip(),
                builder=self.builder_name,
            )
            session.add(build)
            await session.commit()
        self.runner.enqueue(build.id)
        return build

    async def get(self, project_id: int) -> Project:
        async with self.session_factory() as session:
            project = await ProjectRepository(session).get(project_id, with_builds=True)
        if project is None:
            raise NotFoundError(f"Project {project_id} not found.")
        return project

    async def get_by_slug(self, slug: str) -> Project:
        async with self.session_factory() as session:
            project = await ProjectRepository(session).get_by_slug(slug)
        if project is None:
            raise NotFoundError(f"Project {slug} not found.")
        return project

    async def list(self) -> Sequence[Project]:
        async with self.session_factory() as session:
            return await ProjectRepository(session).list_recent()

    async def delete(self, project_id: int) -> None:
        project = await self.get(project_id)
        for build in project.builds:
            if build.status in ("queued", "building", "deploying"):
                await self.runner.cancel(build.id)
        await self.deployer.remove(project.slug)
        workspace = self.settings.workspaces_dir / project.slug
        await asyncio.to_thread(shutil.rmtree, workspace, True)
        async with self.session_factory() as session:
            repo = ProjectRepository(session)
            row = await repo.get(project_id, with_builds=True)
            if row is not None:
                await repo.delete(row)
                await session.commit()
