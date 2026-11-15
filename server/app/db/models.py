"""Database tables: a project has many builds, a build has many log events."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utcnow


class Project(Base):
    """One app a user asked for. Its slug is its address: /apps/<slug>/."""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    prompt: Mapped[str] = mapped_column(Text)
    # draft -> building -> live | failed. A live app stays live while a follow-up builds.
    status: Mapped[str] = mapped_column(String(16), default="draft")
    url: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    builds: Mapped[list[Build]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="Build.id"
    )


class Build(Base):
    """One run of the agent: the first build, or a follow-up change."""

    __tablename__ = "builds"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    number: Mapped[int] = mapped_column(Integer)
    prompt: Mapped[str] = mapped_column(Text)
    # queued -> building -> deploying -> live | failed | cancelled
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    builder: Mapped[str] = mapped_column(String(32))
    # The Claude Code session, so a follow-up can resume the same conversation.
    session_id: Mapped[str | None] = mapped_column(String(64))
    cost_usd: Mapped[float | None] = mapped_column(Float)
    turns: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    project: Mapped[Project] = relationship(back_populates="builds")


class BuildEvent(Base):
    """One line of a build's log, kept so a page reload can replay it."""

    __tablename__ = "build_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    build_id: Mapped[int] = mapped_column(ForeignKey("builds.id", ondelete="CASCADE"), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(16))
    text: Mapped[str] = mapped_column(Text, default="")
    data: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
