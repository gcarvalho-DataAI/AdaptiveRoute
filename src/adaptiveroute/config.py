from __future__ import annotations

import os
from pathlib import Path


def load_project_env(path: str | Path | None = None) -> None:
    """Load a simple .env file without overriding already exported variables."""

    env_path = Path(path) if path is not None else _default_env_path()
    if env_path is None or not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        os.environ[key] = _strip_env_value(value.strip())


def _default_env_path() -> Path | None:
    cwd_env = Path.cwd() / ".env"
    if cwd_env.exists():
        return cwd_env

    project_env = Path(__file__).resolve().parents[2] / ".env"
    if project_env.exists():
        return project_env

    return None


def _strip_env_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value
