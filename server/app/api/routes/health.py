"""Liveness and configuration check."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter

from app.api.deps import ContainerDep

router = APIRouter(tags=["health"])

EXAMPLES_FILE = Path(__file__).resolve().parents[2] / "data" / "examples.json"


@router.get("/health")
async def health(container: ContainerDep) -> dict:
    s = container.settings
    return {
        "status": "ok",
        "builder": container.builder.name,
        "model": s.agent_model if container.builder.name == "claude_code" else None,
        "deployer": container.deployer.name,
        "sandbox": s.agent_sandbox,
        "max_concurrent_builds": s.max_concurrent_builds,
    }


@router.get("/tls-check", status_code=200)
async def tls_check(domain: str, container: ContainerDep) -> dict:
    """Caddy asks this before getting an HTTPS certificate for ``<slug>.apps.<domain>``.

    Answering 404 for unknown slugs stops strangers from making Caddy request
    certificates for random subdomains. See deploy/Caddyfile.domain.
    """
    slug = domain.split(".", 1)[0].lower()
    await container.projects.get_by_slug(slug)  # raises NotFoundError -> 404
    return {"ok": True}


@router.get("/examples")
async def examples() -> list[dict[str, str]]:
    """Starter prompts for the home page. Edit data/examples.json to change them."""
    return json.loads(EXAMPLES_FILE.read_text(encoding="utf-8"))
