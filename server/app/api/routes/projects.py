"""Projects: ask for an app, ask for a change, list, look up, delete."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import ContainerDep
from app.db.models import Project
from app.schemas.project import (
    BuildOut,
    CreateBuild,
    CreateProject,
    ProjectDetail,
    ProjectOut,
)

router = APIRouter(prefix="/projects", tags=["projects"])


def to_out(project: Project) -> ProjectOut:
    out = ProjectOut.model_validate(project)
    if project.builds:
        out.latest_build = BuildOut.model_validate(project.builds[-1])
    return out


def to_detail(project: Project) -> ProjectDetail:
    detail = ProjectDetail.model_validate(project)
    if project.builds:
        detail.latest_build = detail.builds[-1]
    return detail


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def create_project(body: CreateProject, container: ContainerDep) -> ProjectDetail:
    """Queue the first build. Follow it on GET /api/builds/{id}/events."""
    project = await container.projects.create(body.prompt, body.name)
    return to_detail(project)


@router.get("")
async def list_projects(container: ContainerDep) -> list[ProjectOut]:
    return [to_out(p) for p in await container.projects.list()]


@router.get("/{project_id}")
async def get_project(project_id: int, container: ContainerDep) -> ProjectDetail:
    return to_detail(await container.projects.get(project_id))


@router.get("/by-slug/{slug}")
async def get_project_by_slug(slug: str, container: ContainerDep) -> ProjectDetail:
    return to_detail(await container.projects.get_by_slug(slug))


@router.post("/{project_id}/builds", status_code=status.HTTP_202_ACCEPTED)
async def request_change(project_id: int, body: CreateBuild, container: ContainerDep) -> BuildOut:
    """Ask for a change. Claude Code resumes the session of the last successful build."""
    build = await container.projects.request_change(project_id, body.prompt)
    return BuildOut.model_validate(build)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: int, container: ContainerDep) -> None:
    """Cancel any running build, take the app offline and delete its files."""
    await container.projects.delete(project_id)
