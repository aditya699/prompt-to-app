"""Server-Sent Events helpers for the streaming endpoints (research and chat)."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi.responses import StreamingResponse
from pydantic import BaseModel


def format_sse(event: BaseModel, event_name: str | None = None) -> str:
    """Serialise one event in the ``text/event-stream`` wire format."""
    name = event_name or getattr(event, "type", "message")
    return f"event: {name}\ndata: {event.model_dump_json(exclude_none=True)}\n\n"


def sse_response(events: AsyncIterator[str]) -> StreamingResponse:
    """Wrap an iterator of pre-formatted SSE strings in a streaming response."""
    return StreamingResponse(
        events,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
