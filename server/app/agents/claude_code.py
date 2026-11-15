"""Runs Claude Code in the project's folder through the Claude Agent SDK.

The SDK starts the Claude Code CLI as a subprocess (the SDK package ships with
it) and streams back what the agent does: its messages, every tool call, and a
final result with the session id and cost. We turn those into build-log events.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKError,
    CLINotFoundError,
    HookMatcher,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolUseBlock,
    query,
)

from app.agents.base import AgentEvent, BuildOutcome, BuildRequest, Emit
from app.agents.policy import AgentPolicy
from app.agents.prompts import render
from app.core.config import Settings

logger = logging.getLogger(__name__)

# Domains a sandboxed build may reach: npm, so `npm install` works.
SANDBOX_DOMAINS = ["registry.npmjs.org", "registry.yarnpkg.com", "*.npmjs.org"]


class ClaudeCodeBuilder:
    name = "claude_code"

    def __init__(self, settings: Settings, policy: AgentPolicy | None = None) -> None:
        self.settings = settings
        self.policy = policy or AgentPolicy.load()

    def options_for(self, request: BuildRequest) -> ClaudeAgentOptions:
        """Everything Claude Code is allowed to do for one build. Public so tests can check it."""
        s = self.settings
        workspace = request.workspace

        async def guard(hook_input: Any, _tool_use_id: str | None, _context: Any) -> dict:
            reason = self.policy.check(
                hook_input["tool_name"], hook_input.get("tool_input") or {}, workspace
            )
            if reason is None:
                return {}  # no opinion: the allowed_tools list decides
            logger.info("Blocked %s: %s", hook_input["tool_name"], reason)
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }

        env = {"CLAUDE_AGENT_SDK_CLIENT_APP": "prompt-to-app/0.1.0"}
        if s.anthropic_api_key:
            env["ANTHROPIC_API_KEY"] = s.anthropic_api_key

        options = ClaudeAgentOptions(
            model=s.agent_model,
            effort=s.agent_effort,
            cwd=workspace,
            # Keep Claude Code's own system prompt (it knows how to use its tools)
            # and add our brief on what a deployable app looks like.
            system_prompt={
                "type": "preset",
                "preset": "claude_code",
                "append": render(
                    "builder",
                    project_name=request.project_name,
                    slug=workspace.name,
                ),
            },
            tools=self.policy.tools,
            allowed_tools=self.policy.tools,
            # Nobody is there to approve a prompt: anything not allowed is denied.
            permission_mode="dontAsk",
            hooks={"PreToolUse": [HookMatcher(hooks=[guard])]},
            # Ignore settings files on this machine and in the workspace: the
            # workspace is written by the agent, and project settings can run hooks.
            setting_sources=[],
            max_turns=s.agent_max_turns,
            max_budget_usd=s.agent_max_budget_usd,
            resume=request.resume_session_id,
            env=env,
            stderr=lambda line: logger.debug("claude: %s", line.rstrip()),
        )
        if s.agent_sandbox:
            if sys.platform == "win32":
                logger.warning("AGENT_SANDBOX is ignored on Windows (macOS and Linux only).")
            else:
                options.sandbox = {
                    "enabled": True,
                    "autoAllowBashIfSandboxed": True,
                    "allowUnsandboxedCommands": False,
                    "network": {"allowedDomains": SANDBOX_DOMAINS},
                }
        return options

    async def build(self, request: BuildRequest, emit: Emit) -> BuildOutcome:
        prompt = (
            render("followup", prompt=request.prompt) if request.is_followup else request.prompt
        )
        options = self.options_for(request)
        await emit(AgentEvent("status", f"Starting Claude Code ({self.settings.agent_model})"))

        result: ResultMessage | None = None
        last_text = ""
        try:
            async for message in query(prompt=prompt, options=options):
                if isinstance(message, SystemMessage) and message.subtype == "init":
                    session = message.data.get("session_id")
                    await emit(
                        AgentEvent("status", "Claude Code is working", {"session_id": session})
                    )
                elif isinstance(message, AssistantMessage):
                    if message.parent_tool_use_id:  # a subagent's step; the main agent reports
                        continue
                    for block in message.content:
                        if isinstance(block, TextBlock) and block.text.strip():
                            last_text = block.text.strip()
                            await emit(AgentEvent("message", last_text))
                        elif isinstance(block, ToolUseBlock):
                            await emit(describe_tool(block.name, block.input, request.workspace))
                elif isinstance(message, ResultMessage):
                    result = message
        except CLINotFoundError:
            return BuildOutcome(
                ok=False, error="The Claude Code CLI was not found on this machine."
            )
        except ClaudeSDKError as exc:
            # A failed run yields its ResultMessage and then raises; prefer the result.
            if result is None:
                return BuildOutcome(ok=False, error=f"Claude Code failed: {exc}")

        if result is None:
            return BuildOutcome(ok=False, error="Claude Code stopped without a result.")
        outcome = BuildOutcome(
            ok=not result.is_error and result.subtype == "success",
            session_id=result.session_id,
            cost_usd=result.total_cost_usd,
            turns=result.num_turns,
            summary=result.result or last_text or None,
        )
        if not outcome.ok:
            outcome.error = _failure_reason(result)
        return outcome


def describe_tool(name: str, tool_input: dict[str, Any], workspace: Path) -> AgentEvent:
    """Turn a tool call into a short log line: "Write src/App.tsx", "Run npm run build"."""

    def rel(value: Any) -> str:
        path = Path(str(value))
        try:
            return path.resolve().relative_to(workspace.resolve()).as_posix()
        except ValueError:
            return str(value)

    if name in ("Write", "Edit", "Read") and "file_path" in tool_input:
        text = f"{name} {rel(tool_input['file_path'])}"
    elif name == "Bash":
        command = str(tool_input.get("command", "")).strip().splitlines()[0][:160]
        text = f"Run {command}"
    elif name in ("Glob", "Grep"):
        text = f"{name} {tool_input.get('pattern', '')}"
    elif name == "TodoWrite":
        todos = tool_input.get("todos") or []
        text = f"Plan: {len(todos)} steps"
        return AgentEvent("tool", text, {"tool": name, "todos": todos})
    else:
        text = name
    return AgentEvent("tool", text, {"tool": name})


def _failure_reason(result: ResultMessage) -> str:
    reasons = {
        "error_max_turns": "The agent used all its turns (AGENT_MAX_TURNS) before finishing.",
        "error_max_budget_usd": "The build hit its spending cap (AGENT_MAX_BUDGET_USD).",
    }
    if result.subtype in reasons:
        return reasons[result.subtype]
    if result.api_error_status == 401 or "API key" in (result.result or ""):
        return "Claude rejected the API key. Check ANTHROPIC_API_KEY in server/.env."
    if result.api_error_status:
        return f"The Claude API returned HTTP {result.api_error_status}."
    detail = "; ".join(result.errors or []) or result.result or result.subtype
    return f"Claude Code failed: {detail}"
