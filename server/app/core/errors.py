"""Domain errors. Routes raise these; ``main.py`` turns them into JSON responses."""

from __future__ import annotations


class AppError(Exception):
    """Base class for errors the API reports to the client as ``{"error": {...}}``."""

    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class BuildError(AppError):
    """The agent ran but did not produce something we can deploy."""

    status_code = 500
    code = "build_failed"


class DeployError(AppError):
    status_code = 500
    code = "deploy_failed"
