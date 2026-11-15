"""Pick the deployer. There is one today; add yours here."""

from __future__ import annotations

from app.core.config import Settings
from app.deploy.base import Deployer
from app.deploy.static import StaticDeployer


def build_deployer(settings: Settings) -> Deployer:
    return StaticDeployer(settings)
