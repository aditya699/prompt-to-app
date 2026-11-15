"""Shared schema helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict


def _assume_utc(value: datetime | None) -> datetime | None:
    # SQLite drops tz info on the way back; every timestamp we store is UTC.
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


UtcDatetime = Annotated[datetime, AfterValidator(_assume_utc)]


class ApiModel(BaseModel):
    """Base for response models that are built from ORM rows."""

    model_config = ConfigDict(from_attributes=True)
