"""The Builder interface: anything that can turn a prompt into files in a folder.

``ClaudeCodeBuilder`` runs Claude Code through the Claude Agent SDK.
``FakeBuilder`` copies a starter app so you can run everything with no key.
Write your own (another agent, a template engine) and register it in
``app/agents/factory.py``.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol

EventType = Literal["status", "message", "tool", "error"]


@dataclass(frozen=True)
class AgentEvent:
    """One line for the build log.

    - ``status``: a milestone ("Claude Code started", "Deploying")
    - ``message``: something the agent said
    - ``tool``: the agent used a tool ("Write index.html", "Bash: npm run build")
    - ``error``: something went wrong
    """

    type: EventType
    text: str
    data: dict[str, Any] | None = None


Emit = Callable[[AgentEvent], Awaitable[None]]


@dataclass(frozen=True)
class BuildRequest:
    prompt: str
    workspace: Path
    project_name: str
    # Set for follow-up builds: the agent continues the earlier conversation.
    resume_session_id: str | None = None
    is_followup: bool = False


@dataclass
class BuildOutcome:
    ok: bool
    session_id: str | None = None
    cost_usd: float | None = None
    turns: int | None = None
    summary: str | None = None
    error: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class Builder(Protocol):
    name: str

    async def build(self, request: BuildRequest, emit: Emit) -> BuildOutcome:
        """Write the app into ``request.workspace``, reporting progress through ``emit``."""
        ...
