"""A builder that needs no API key: it writes a small starter app from a template.

It walks through the same steps a real build reports (plan, write files, build),
so the whole pipeline — queue, log stream, deploy, URL — runs for real, offline,
in tests and in demo mode (BUILDER=fake).
"""

from __future__ import annotations

import asyncio
import html
import json
import uuid
from pathlib import Path

from app.agents.base import AgentEvent, BuildOutcome, BuildRequest, Emit

TEMPLATE = Path(__file__).resolve().parents[1] / "data" / "starter" / "index.html"
HISTORY_FILE = "prompts.json"


class FakeBuilder:
    name = "fake"

    def __init__(self, step_delay: float = 0.0, fail_on: str | None = None) -> None:
        self.step_delay = step_delay
        # Tests set this to make a build fail when the prompt contains the text.
        self.fail_on = fail_on

    async def _step(self, emit: Emit, event: AgentEvent) -> None:
        await emit(event)
        if self.step_delay:
            await asyncio.sleep(self.step_delay)

    async def build(self, request: BuildRequest, emit: Emit) -> BuildOutcome:
        session_id = request.resume_session_id or str(uuid.uuid4())
        await self._step(emit, AgentEvent("status", "Starting the fake builder (no API key used)"))
        await self._step(
            emit, AgentEvent("message", "I'll make a small app that saves entries in the browser.")
        )
        await self._step(emit, AgentEvent("tool", "Plan: 3 steps", {"tool": "TodoWrite"}))

        if self.fail_on and self.fail_on in request.prompt:
            return BuildOutcome(ok=False, session_id=session_id, error="Fake failure for tests.")

        history_path = request.workspace / HISTORY_FILE
        history = json.loads(history_path.read_text("utf-8")) if history_path.exists() else []
        history.append(request.prompt)
        history_path.write_text(json.dumps(history, indent=2), "utf-8")
        await self._step(emit, AgentEvent("tool", f"Write {HISTORY_FILE}", {"tool": "Write"}))

        dist = request.workspace / "dist"
        dist.mkdir(parents=True, exist_ok=True)
        page = (
            TEMPLATE.read_text("utf-8")
            .replace("{{TITLE}}", html.escape(request.project_name))
            .replace("{{PROMPT}}", html.escape(history[0]))
            .replace("{{CHANGES}}", "".join(f"<li>{html.escape(p)}</li>" for p in history[1:]))
            .replace("{{STORAGE_KEY}}", f"app:{request.workspace.name}")
        )
        (dist / "index.html").write_text(page, "utf-8")
        await self._step(emit, AgentEvent("tool", "Write dist/index.html", {"tool": "Write"}))
        await self._step(emit, AgentEvent("tool", "Run ls dist", {"tool": "Bash"}))

        verb = "Updated" if request.is_followup else "Built"
        summary = (
            f"{verb} {request.project_name}. Add entries with the form; they are saved in "
            "your browser. (This is the fake builder: set BUILDER=claude_code for real apps.)"
        )
        await self._step(emit, AgentEvent("message", summary))
        return BuildOutcome(
            ok=True, session_id=session_id, cost_usd=0.0, turns=len(history), summary=summary
        )
