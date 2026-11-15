"""ClaudeCodeBuilder without calling Claude: the options it sends and how it reads replies."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolUseBlock,
)

from app.agents import claude_code
from app.agents.base import AgentEvent, BuildRequest
from app.agents.claude_code import ClaudeCodeBuilder
from app.core.config import Settings


@pytest.fixture
def builder(tmp_path: Path) -> ClaudeCodeBuilder:
    settings = Settings(_env_file=None, anthropic_api_key="sk-test", agent_max_turns=40)
    return ClaudeCodeBuilder(settings)


@pytest.fixture
def request_(tmp_path: Path) -> BuildRequest:
    ws = tmp_path / "workout-ab12"
    ws.mkdir()
    return BuildRequest(prompt="Track my workouts", workspace=ws, project_name="Workouts")


def test_options(builder: ClaudeCodeBuilder, request_: BuildRequest) -> None:
    options = builder.options_for(request_)
    assert options.cwd == request_.workspace
    assert options.permission_mode == "dontAsk"
    assert options.setting_sources == []
    assert "Bash" in options.allowed_tools and "WebFetch" not in options.tools
    assert options.max_turns == 40
    assert options.resume is None
    assert options.env["ANTHROPIC_API_KEY"] == "sk-test"
    assert "Workouts" in options.system_prompt["append"]
    assert "/apps/workout-ab12/" in options.system_prompt["append"]


async def test_hook_denies_risky_calls(builder: ClaudeCodeBuilder, request_: BuildRequest) -> None:
    guard = builder.options_for(request_).hooks["PreToolUse"][0].hooks[0]
    allowed = await guard(
        {"tool_name": "Bash", "tool_input": {"command": "npm run build"}}, "t1", {}
    )
    assert allowed == {}
    denied = await guard({"tool_name": "Bash", "tool_input": {"command": "curl x"}}, "t2", {})
    assert denied["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "curl" in denied["hookSpecificOutput"]["permissionDecisionReason"]


async def test_build_reads_the_message_stream(
    builder: ClaudeCodeBuilder, request_: BuildRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, Any] = {}

    async def fake_query(*, prompt: str, options: Any) -> AsyncIterator[Any]:
        seen["prompt"] = prompt
        yield SystemMessage(subtype="init", data={"session_id": "sess-1"})
        yield AssistantMessage(
            content=[
                TextBlock(text="I'll build it with plain HTML."),
                ToolUseBlock(
                    id="t1",
                    name="Write",
                    input={"file_path": str(request_.workspace / "dist" / "index.html")},
                ),
                ToolUseBlock(id="t2", name="Bash", input={"command": "ls dist\n"}),
            ],
            model="claude-opus-5-5",
        )
        yield ResultMessage(
            subtype="success",
            duration_ms=10,
            duration_api_ms=8,
            is_error=False,
            num_turns=3,
            session_id="sess-1",
            total_cost_usd=0.42,
            result="Built a workout tracker.",
        )

    monkeypatch.setattr(claude_code, "query", fake_query)
    events: list[AgentEvent] = []

    async def emit(event: AgentEvent) -> None:
        events.append(event)

    outcome = await builder.build(request_, emit)
    assert seen["prompt"] == "Track my workouts"
    assert outcome.ok and outcome.session_id == "sess-1" and outcome.cost_usd == 0.42
    assert outcome.summary == "Built a workout tracker."
    assert [e.text for e in events if e.type == "tool"] == ["Write dist/index.html", "Run ls dist"]


async def test_follow_up_and_budget_failure(
    builder: ClaudeCodeBuilder, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, Any] = {}

    async def fake_query(*, prompt: str, options: Any) -> AsyncIterator[Any]:
        seen["prompt"], seen["resume"] = prompt, options.resume
        yield ResultMessage(
            subtype="error_max_budget_usd",
            duration_ms=1,
            duration_api_ms=1,
            is_error=True,
            num_turns=9,
            session_id="sess-1",
        )

    monkeypatch.setattr(claude_code, "query", fake_query)
    request = BuildRequest(
        prompt="Add dark mode",
        workspace=tmp_path,
        project_name="Workouts",
        resume_session_id="sess-1",
        is_followup=True,
    )

    async def emit(_: AgentEvent) -> None:
        return None

    outcome = await builder.build(request, emit)
    assert seen["resume"] == "sess-1" and "Add dark mode" in seen["prompt"]
    assert not outcome.ok and "AGENT_MAX_BUDGET_USD" in (outcome.error or "")
