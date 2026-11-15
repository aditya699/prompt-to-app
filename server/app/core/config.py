"""Every setting the server reads, in one place. Values come from ``server/.env``."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

SERVER_DIR = Path(__file__).resolve().parents[2]
VAR_DIR = SERVER_DIR / "var"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=SERVER_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "Prompt to App"
    environment: Literal["development", "production", "test"] = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173"
    database_url: str = f"sqlite+aiosqlite:///{(VAR_DIR / 'app.db').as_posix()}"

    # --- Builder: who writes the app -------------------------------------------
    builder: Literal["claude_code", "fake"] = "claude_code"
    anthropic_api_key: str | None = None
    agent_model: str = "claude-opus-5-5"
    agent_effort: Literal["low", "medium", "high", "xhigh", "max"] = "high"
    agent_max_turns: int = Field(default=60, ge=1)
    agent_max_budget_usd: float = Field(default=2.0, gt=0)
    agent_sandbox: bool = False
    build_timeout_seconds: int = Field(default=900, ge=30)
    max_concurrent_builds: int = Field(default=1, ge=1, le=8)
    # Seconds the fake builder waits between steps, so the UI has something to show.
    fake_step_delay: float = Field(default=0.4, ge=0)

    # --- Deployer: where the app goes ------------------------------------------
    workspaces_dir: Path = VAR_DIR / "workspaces"
    sites_dir: Path = VAR_DIR / "sites"
    # Public URL of this server. Used to build app links when APP_URL_TEMPLATE is empty.
    public_base_url: str = "http://localhost:8000"
    # Where a deployed app lives. {slug} is replaced. Empty = {PUBLIC_BASE_URL}/apps/{slug}/.
    # On a VM with wildcard DNS: https://{slug}.apps.example.com
    app_url_template: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def app_url(self, slug: str) -> str:
        template = self.app_url_template or f"{self.public_base_url.rstrip('/')}/apps/{{slug}}/"
        return template.replace("{slug}", slug)


@lru_cache
def get_settings() -> Settings:
    return Settings()
