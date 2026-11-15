"""The Deployer interface: take a built folder, put it online, return its URL.

``StaticDeployer`` copies the files to SITES_DIR, which this server (or Caddy
on a VM) serves. To deploy somewhere else — an S3 bucket, Cloudflare Pages, a
container per app — implement this and register it in ``deploy/factory.py``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class Deployer(Protocol):
    name: str

    async def deploy(self, slug: str, build_dir: Path) -> str:
        """Publish ``build_dir`` (which holds index.html) and return the public URL."""
        ...

    async def remove(self, slug: str) -> None:
        """Take the app offline."""
        ...


def find_build_output(workspace: Path) -> Path | None:
    """Where the agent left the finished site: ``dist/``, ``build/`` or the folder itself."""
    for candidate in (workspace / "dist", workspace / "build", workspace):
        if (candidate / "index.html").is_file():
            return candidate
    return None
