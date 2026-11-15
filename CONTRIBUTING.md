# Contributing

Thanks for building on this. Forks, experiments and pull requests are all welcome.

## Setup

See the [Quickstart](README.md#quickstart-your-laptop). For work that doesn't need real builds, set `BUILDER=fake` in `server/.env`.

## Before you open a pull request

```bash
cd server
uv run ruff format .
uv run ruff check .
uv run pytest

cd ../client
npm run lint
npm run build
```

CI runs the same checks.

## Conventions

- **Server.** Routes stay thin; work goes in `services/`, SQL in `repositories/`. Type hints on everything, a docstring on anything public, `logging` instead of `print`. New settings go in `core/config.py` *and* `server/.env.example`.
- **Agent prompts** live in `server/app/agents/prompts/` as Markdown, and rules in `server/app/data/agent_policy.json`, not inside Python.
- **Tests** must run offline and free. Use the `FakeBuilder`, or replace the SDK's `query` as `tests/test_claude_code.py` does; never call the real API from a test.
- **Client.** Components never call `fetch` directly; add an endpoint to `src/api/endpoints.ts` and a hook in `src/hooks/`. Keep `src/api/types.ts` in sync with the server schemas.
- **Commits.** Small and focused, with a message that says why.

## Reporting bugs

Open an issue with what you did, what you expected, what happened, and the relevant server log lines. Never paste API keys.
