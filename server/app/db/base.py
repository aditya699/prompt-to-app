"""SQLAlchemy declarative base shared by every model."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import DeclarativeBase


def utcnow() -> datetime:
    """Timezone-aware 'now'. Use this instead of ``datetime.utcnow`` (deprecated)."""
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass
