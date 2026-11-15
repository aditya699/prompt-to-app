"""Prompts live next to this file as Markdown, so you can edit them without touching code."""

from __future__ import annotations

from pathlib import Path

PROMPTS_DIR = Path(__file__).parent


def render(name: str, **values: str) -> str:
    """Load ``<name>.md`` and fill ``{key}`` placeholders. Other braces are left alone."""
    text = (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{" + key + "}", value)
    return text
