# API reference

Base URL: `http://localhost:8000`. Interactive docs with every schema: `/docs`.

Errors always look like:

```json
{ "error": { "code": "not_found", "message": "Project 12 not found." } }
```

Codes: `not_found` (404), `conflict` (409). Invalid bodies return FastAPI's standard `422`.

## Projects

### `POST /api/projects`

Ask for an app. Creates the project and queues build #1.

```json
{ "prompt": "Create a web app that will help me track my workouts", "name": "Gym log" }
```

`prompt` is 8–4000 characters. `name` is optional; without it a name is made from the prompt ("Track My Workouts").

**202** — the project with `builds: [ {number: 1, status: "queued", ...} ]`. Follow the build at `/api/builds/{id}/events`.

### `GET /api/projects`

All projects, most recently updated first, each with its `latest_build`.

### `GET /api/projects/{id}` and `GET /api/projects/by-slug/{slug}`

One project with every build, oldest first.

```json
{
  "id": 1,
  "slug": "track-my-workouts-k3x9",
  "name": "Track My Workouts",
  "prompt": "Create a web app that will help me track my workouts",
  "status": "live",
  "url": "http://localhost:8000/apps/track-my-workouts-k3x9/",
  "created_at": "2026-11-15T09:30:00Z",
  "updated_at": "2026-11-15T09:34:10Z",
  "latest_build": { "...": "same shape as below" },
  "builds": [
    {
      "id": 1, "project_id": 1, "number": 1,
      "prompt": "Create a web app that will help me track my workouts",
      "status": "live", "builder": "claude_code",
      "cost_usd": 0.61, "turns": 23, "error": null,
      "created_at": "...", "started_at": "...", "finished_at": "..."
    }
  ]
}
```

### `POST /api/projects/{id}/builds`

Ask for a change. **202** with the new build. **409** if a build of this project is queued or running.

```json
{ "prompt": "Add a weekly chart of total weight lifted" }
```

### `DELETE /api/projects/{id}`

Cancels any build, removes the deployed app and the workspace, deletes the records. **204**.

## Builds

### `GET /api/builds/{id}`

One build.

### `GET /api/builds/{id}/events?after=0`

The build log as `text/event-stream`. Saved lines come first, then live ones; the stream ends after the `done` event. Pass `after=<seq>` to resume after a dropped connection. A `: keepalive` comment is sent every 15 seconds while the build is quiet.

Each event:

```
event: tool
data: {"seq":7,"type":"tool","text":"Write src/App.tsx","data":{"tool":"Write"},"created_at":"..."}
```

| `type` | Meaning |
|---|---|
| `status` | A milestone: "Starting Claude Code", "Deploying" |
| `message` | Something the agent said |
| `tool` | A tool call: "Write src/App.tsx", "Run npm run build", "Plan: 4 steps" |
| `error` | Why the build failed |
| `done` | The end. `data.status` is `live`, `failed` or `cancelled`; `data.url` is set when live |

### `POST /api/builds/{id}/cancel`

Stops a queued or running build. **200** with the build (`status: "cancelled"`), or **409** if it had already finished.

## Other

| Path | |
|---|---|
| `GET /api/health` | `{"status":"ok","builder":"claude_code","model":"claude-opus-5-5","deployer":"static","sandbox":true,"max_concurrent_builds":1}` |
| `GET /api/examples` | Starter prompts for the home page, from `data/examples.json` |
| `GET /api/tls-check?domain=<host>` | 200 if the host's first label is a project slug. Caddy calls this before issuing a certificate |
| `GET /apps/{slug}/` | A deployed app, served from `SITES_DIR` |
