"""Deploy by copying files into a folder that a web server serves.

Locally, FastAPI serves SITES_DIR at /apps/<slug>/. On a VM, Caddy serves the
same folder on a subdomain per app (see deploy/Caddyfile).

The copy goes to a temp folder first and then replaces the live one, so
visitors never see a half-copied app.
"""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from app.core.config import Settings
from app.core.errors import DeployError

# Never publish these, even if the agent left them in the output folder.
SKIP = shutil.ignore_patterns("node_modules", ".env", ".env.*", ".git", "*.map")
MAX_SITE_BYTES = 50 * 1024 * 1024


class StaticDeployer:
    name = "static"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.sites_dir = Path(settings.sites_dir)

    async def deploy(self, slug: str, build_dir: Path) -> str:
        await asyncio.to_thread(self._publish, slug, build_dir)
        return self.settings.app_url(slug)

    async def remove(self, slug: str) -> None:
        await asyncio.to_thread(shutil.rmtree, self.sites_dir / slug, True)

    def _publish(self, slug: str, build_dir: Path) -> None:
        self.sites_dir.mkdir(parents=True, exist_ok=True)
        staging = self.sites_dir / f".{slug}.staging"
        old = self.sites_dir / f".{slug}.old"
        live = self.sites_dir / slug
        for leftover in (staging, old):
            shutil.rmtree(leftover, ignore_errors=True)

        # When the agent wrote the site at the workspace root, skip its sources too.
        ignore = SKIP if build_dir.name in ("dist", "build") else _root_ignore
        shutil.copytree(build_dir, staging, ignore=ignore)
        size = sum(f.stat().st_size for f in staging.rglob("*") if f.is_file())
        if size > MAX_SITE_BYTES:
            shutil.rmtree(staging, ignore_errors=True)
            raise DeployError(f"The built app is {size // 1_000_000} MB; the limit is 50 MB.")

        if live.exists():
            live.rename(old)
        staging.rename(live)
        shutil.rmtree(old, ignore_errors=True)


def _root_ignore(directory: str, names: list[str]) -> set[str]:
    skipped = set(SKIP(directory, names))
    return skipped | {n for n in names if n in ("src", "package.json", "package-lock.json")}
