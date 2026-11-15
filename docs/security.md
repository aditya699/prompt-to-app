# Security

This app runs an AI agent that writes and executes code based on what users type. Treat every build as untrusted code, and set the VM up so that is fine.

## The layers, from strongest to weakest

1. **A VM that holds nothing else.** No other services, no cloud credentials with wide permissions, no data you care about. If a build goes wrong, you rebuild the VM.
2. **An unprivileged user.** `deploy/setup.sh` runs the server, and so Claude Code, as `builder`, which has no sudo and can only write its home folder and the sites folder.
3. **Claude Code's OS sandbox** (`AGENT_SANDBOX=true`, Linux and macOS). Shell commands run under bubblewrap, which by default only lets them write inside the working folder, and network access is limited to the npm registry. `allowUnsandboxedCommands` is off, so the agent can't opt out.
4. **The tool policy** (`server/app/data/agent_policy.json`). The agent only has Read, Write, Edit, Glob, Grep, Bash and TodoWrite: no web fetching, no subagents, no MCP servers. A PreToolUse hook rejects file paths outside the workspace and shell commands that use blocked programs (`curl`, `sudo`, `ssh`, `git`, `docker`, package managers…) or blocked patterns (system folders, `.env`, global installs, dev servers). A pattern list can be talked around; it is a guardrail and a way to keep the agent on task, not a sandbox.
5. **Limits per build.** `AGENT_MAX_TURNS`, `AGENT_MAX_BUDGET_USD` and `BUILD_TIMEOUT_SECONDS` stop runaway builds and runaway bills.
6. **Isolated settings.** `setting_sources=[]` means no settings file on the machine or in the workspace (which the agent itself writes) can add hooks or permissions.

## Apps are untrusted too

A deployed app is JavaScript that the agent wrote from a user's prompt. With the **domain setup**, each app is on its own subdomain (`<slug>.apps.example.com`), a different origin from the builder at `app.example.com`, so an app can't call your API or read another app's storage.

With the **IP-only setup**, apps are served from the same origin as the API (`http://<ip>/apps/<slug>/`). An app could then call `/api/...` in the visitor's browser. That is acceptable while you are the only user, and the reason to use a domain before you share it.

## Things this starter does not do yet

- **No login.** Anyone who can reach the UI can start builds that spend your API credit. Put it behind authentication (or at least Caddy `basic_auth`) before sharing the address.
- **No per-user limits.** Add a daily budget per user once you have accounts.
- **No content checks** on what users ask for or what the apps contain.
- **One shared machine for all builds.** For many untrusted users, run each build in its own container or micro-VM (see "Build on top of this" in the README).

## Secrets

`server/.env` holds your API key and is git-ignored. It is outside every workspace, so the agent's file tools can't open it, and the policy also rejects shell commands that mention a `.env` file. Claude Code receives the key only through its process environment. Never commit `.env`, and rotate the key if you think it leaked.
