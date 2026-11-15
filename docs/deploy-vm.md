# Deploying to a cloud VM

The point of this project: one VM that you rent, with Claude Code on it, building and hosting apps.

## 1. Get a VM

Any provider works (AWS EC2, Google Compute Engine, Azure, DigitalOcean, Hetzner, …).

- **Image:** Ubuntu 24.04 LTS
- **Size:** 2 vCPU, 4 GB RAM, 30 GB disk to start. `npm install` is the heavy part; add RAM before you raise `MAX_CONCURRENT_BUILDS`.
- **Firewall:** allow 22 (SSH, ideally only from your IP), 80 and 443.

Use this VM for nothing else. The agent runs code that users asked for.

## 2. DNS (optional, recommended)

With a domain you get HTTPS and a separate subdomain per app, which keeps apps isolated from each other and from the builder UI. Add two A records pointing at the VM's IP:

| Name | Points to |
|---|---|
| `app.example.com` | the VM |
| `*.apps.example.com` | the VM |

Without a domain everything runs on `http://<ip>/`, and apps live at `http://<ip>/apps/<slug>/`. That's fine for trying it out, but read the note in [security.md](security.md) before sharing it.

## 3. Run the setup script

```bash
ssh ubuntu@<ip>
sudo git clone https://github.com/aditya699/prompt-to-app.git /opt/prompt-to-app
sudo DOMAIN=example.com bash /opt/prompt-to-app/deploy/setup.sh
```

Leave out `DOMAIN=example.com` for the IP-only setup. The script:

1. installs Node 22, Caddy, `bubblewrap` and `socat` (for Claude Code's sandbox), and uv;
2. creates a `builder` user with no sudo rights; the server and Claude Code run as this user;
3. installs the server's Python packages and writes `server/.env` with production values (`AGENT_SANDBOX=true`, the sites folder, your URLs);
4. builds the client into `client/dist`;
5. installs and starts the `prompt-to-app` systemd service (uvicorn on 127.0.0.1:8000);
6. writes `/etc/caddy/Caddyfile` from `deploy/Caddyfile.domain` or `deploy/Caddyfile.ip` and reloads Caddy.

## 4. Add your key

```bash
sudo -u builder nano /opt/prompt-to-app/server/.env     # set ANTHROPIC_API_KEY=
sudo systemctl restart prompt-to-app
```

Open `https://app.example.com` (or `http://<ip>/`) and build something.

## Updating

```bash
cd /opt/prompt-to-app && sudo git pull
sudo bash deploy/setup.sh          # same DOMAIN= as before; it keeps your .env
```

## Where things live on the VM

| Path | What |
|---|---|
| `/opt/prompt-to-app` | the code |
| `/opt/prompt-to-app/server/.env` | settings and your API key |
| `/opt/prompt-to-app/server/var/app.db` | the database |
| `/home/builder/workspaces/<slug>` | each project's source, where Claude Code works |
| `/home/builder/.claude/` | Claude Code's session history (needed for follow-ups) |
| `/srv/prompt-to-app/sites/<slug>` | each deployed app, served by Caddy |

## Logs

```bash
journalctl -u prompt-to-app -f      # the API and every build
journalctl -u caddy -f              # web server and certificates
```

## Troubleshooting

- **Certificates fail for app subdomains.** Check that `*.apps.example.com` resolves to the VM, and that `curl "http://127.0.0.1:8000/api/tls-check?domain=<slug>.apps.example.com"` returns 200 for an app that exists.
- **Builds fail at `npm install` with the sandbox on.** The sandbox only lets the agent reach the npm registry. If an app needs another host at build time, add it to `SANDBOX_DOMAINS` in `server/app/agents/claude_code.py`.
- **The VM runs out of memory during builds.** Add a swap file or a bigger VM, and keep `MAX_CONCURRENT_BUILDS=1`.
- **Apps 404 on the subdomain.** Caddy maps `<slug>.apps.example.com` to `/srv/prompt-to-app/sites/<slug>` using `{labels.3}`. If your domain has more parts (`example.co.in`), change it to `{labels.4}` in `/etc/caddy/Caddyfile`.
