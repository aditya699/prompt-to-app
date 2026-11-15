# Extending Prompt to App

## Change what the agent is told

The agent's instructions are Markdown files in `server/app/agents/prompts/`:

- `builder.md` is added to Claude Code's system prompt for every build. `{project_name}` and `{slug}` are filled in.
- `followup.md` wraps a change request. `{prompt}` is the user's text.

Edit them and restart the server. A good first experiment: require Tailwind and a specific colour palette, then compare a few builds.

## Change what the agent may do

Edit `server/app/data/agent_policy.json`:

```json
{
  "tools": ["Read", "Write", "Edit", "Glob", "Grep", "Bash", "TodoWrite"],
  "blocked_programs": ["sudo", "curl", "..."],
  "blocked_patterns": [
    { "pattern": "npm\\s+publish", "reason": "publishes to npm" }
  ]
}
```

- `tools` is both the list Claude Code is given and the list it may use without asking.
- `blocked_programs` matches the program at the start of each command in a pipeline or `&&` chain, so `npm run build && curl x` is caught.
- `blocked_patterns` are regular expressions searched anywhere in the command. The `reason` is shown to the agent, so write it as advice ("starts a server that never exits; build with `npm run build` instead").

Add a test case to `server/tests/test_policy.py` for every rule you add.

## Add a builder

A builder is any class with a `name` and an async `build(request, emit)` method (see `server/app/agents/base.py`):

```python
from app.agents.base import AgentEvent, BuildOutcome, BuildRequest, Emit


class TemplateBuilder:
    """Copies a ready-made template instead of calling a model. Handy for demos."""

    name = "template"

    async def build(self, request: BuildRequest, emit: Emit) -> BuildOutcome:
        await emit(AgentEvent("status", "Copying the template"))
        dist = request.workspace / "dist"
        dist.mkdir(parents=True, exist_ok=True)
        (dist / "index.html").write_text("<h1>Hello</h1>", encoding="utf-8")
        return BuildOutcome(ok=True, summary="Copied the template.")
```

Then register it in `server/app/agents/factory.py`, and add its name to the `builder` setting in `core/config.py`. The runner handles queueing, timeouts, logging and deploying; the builder only has to leave an `index.html` in `dist/`, `build/` or the workspace root.

## Add a deployer

A deployer publishes a folder and returns a URL (see `server/app/deploy/base.py`):

```python
class S3Deployer:
    name = "s3"

    async def deploy(self, slug: str, build_dir: Path) -> str:
        # upload every file under build_dir to s3://my-bucket/<slug>/ ...
        return f"https://my-bucket.s3.amazonaws.com/{slug}/index.html"

    async def remove(self, slug: str) -> None:
        # delete s3://my-bucket/<slug>/ ...
        ...
```

Register it in `server/app/deploy/factory.py`. Raise `DeployError` with a readable message when something fails; the build is marked failed with that message and the previous version stays online.

## Add an example prompt

Add a `{label, prompt}` entry to `server/app/data/examples.json`. The home page picks it up after a reload.

## Swap SQLite for Postgres

Install a driver (`uv add asyncpg`), set `DATABASE_URL=postgresql+asyncpg://user:pass@host/db`, and replace `init_db` (which creates tables on startup) with Alembic migrations once the schema settles.
