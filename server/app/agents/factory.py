"""Pick the builder named by the BUILDER setting."""

from __future__ import annotations

from app.agents.base import Builder
from app.agents.claude_code import ClaudeCodeBuilder
from app.agents.fake import FakeBuilder
from app.core.config import Settings


def build_builder(settings: Settings) -> Builder:
    if settings.builder == "fake":
        return FakeBuilder(step_delay=settings.fake_step_delay)
    return ClaudeCodeBuilder(settings)
