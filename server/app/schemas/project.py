"""Request and response models for projects and builds."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.common import ApiModel, UtcDatetime

BuildStatus = Literal["queued", "building", "deploying", "live", "failed", "cancelled"]
ProjectStatus = Literal["draft", "building", "live", "failed"]


class CreateProject(BaseModel):
    prompt: str = Field(min_length=8, max_length=4000, examples=["A web app to track my workouts"])
    name: str | None = Field(default=None, max_length=80)


class CreateBuild(BaseModel):
    """A follow-up change to an existing app."""

    prompt: str = Field(min_length=3, max_length=4000, examples=["Add a weekly chart"])


class BuildOut(ApiModel):
    id: int
    project_id: int
    number: int
    prompt: str
    status: BuildStatus
    builder: str
    cost_usd: float | None
    turns: int | None
    error: str | None
    created_at: UtcDatetime
    started_at: UtcDatetime | None
    finished_at: UtcDatetime | None


class ProjectOut(ApiModel):
    id: int
    slug: str
    name: str
    prompt: str
    status: ProjectStatus
    url: str | None
    created_at: UtcDatetime
    updated_at: UtcDatetime
    latest_build: BuildOut | None = None


class ProjectDetail(ProjectOut):
    builds: list[BuildOut]


class BuildEventOut(ApiModel):
    """One line of a build log, as sent on the SSE stream."""

    seq: int
    type: Literal["status", "message", "tool", "error", "done"]
    text: str
    data: dict[str, Any] | None = None
    created_at: UtcDatetime
