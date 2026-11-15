"""Guardrails for the builder agent, loaded from ``data/agent_policy.json``.

``ClaudeCodeBuilder`` calls :meth:`AgentPolicy.check` from a PreToolUse hook,
so every tool call is checked before it runs. The checks keep the agent inside
its project folder and away from programs a web-app build never needs.

This is a guardrail, not a sandbox: a determined shell command can get past a
pattern list. Run builds on a throwaway VM as an unprivileged user, and turn on
AGENT_SANDBOX on Linux. See docs/security.md.
"""

from __future__ import annotations

import json
import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any

POLICY_FILE = Path(__file__).resolve().parents[1] / "data" / "agent_policy.json"

# Tool input keys that hold a path.
PATH_KEYS = ("file_path", "path", "notebook_path")
# Shell operators that start a new command.
SEGMENT_SPLIT = re.compile(r"&&|\|\||[;|&\n]|\$\(|`")
ENV_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


@dataclass(frozen=True)
class BlockedPattern:
    regex: re.Pattern[str]
    reason: str


@dataclass(frozen=True)
class AgentPolicy:
    tools: list[str]
    blocked_programs: frozenset[str]
    blocked_patterns: list[BlockedPattern]

    @classmethod
    def load(cls, path: Path = POLICY_FILE) -> AgentPolicy:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            tools=list(raw["tools"]),
            blocked_programs=frozenset(raw["blocked_programs"]),
            blocked_patterns=[
                BlockedPattern(re.compile(p["pattern"]), p["reason"])
                for p in raw["blocked_patterns"]
            ],
        )

    def check(self, tool_name: str, tool_input: dict[str, Any], workspace: Path) -> str | None:
        """Return ``None`` to allow the call, or the reason it is denied."""
        if tool_name not in self.tools:
            return f"{tool_name} is not available to the builder."
        for key in PATH_KEYS:
            value = tool_input.get(key)
            if isinstance(value, str) and value and not _inside(value, workspace):
                return f"{value} is outside the project folder. Work only inside {workspace}."
        if tool_name == "Bash":
            return self.check_command(str(tool_input.get("command", "")))
        return None

    def check_command(self, command: str) -> str | None:
        for program in _programs(command):
            if program in self.blocked_programs:
                return f"`{program}` is not allowed in a build."
        for blocked in self.blocked_patterns:
            if blocked.regex.search(command):
                return f"Command not allowed: it {blocked.reason}."
        return None


def _inside(value: str, workspace: Path) -> bool:
    root = workspace.resolve()
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = root / candidate
    return candidate.resolve().is_relative_to(root)


def _programs(command: str) -> list[str]:
    """The program each segment of a shell command runs: ``a && b | c`` -> a, b, c."""
    programs = []
    for segment in SEGMENT_SPLIT.split(command):
        try:
            words = shlex.split(segment, posix=True)
        except ValueError:
            words = segment.split()
        while words and ENV_ASSIGNMENT.match(words[0]):
            words.pop(0)
        if words:
            programs.append(Path(words[0]).name)
    return programs
