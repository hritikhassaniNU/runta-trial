"""Resolve and jail paths to the RootScope workspace."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

SECRET_NAMES = {".env", ".env.local"}
SECRET_SUFFIXES = {".pem", ".key"}


class ToolError(Exception):
    """Raised when a tool refuses a call. The string is model-visible."""


def workspace_root() -> Path:
    override = os.environ.get("ROOTSCOPE_ROOT")
    if override:
        return Path(override).resolve()
    return Path(__file__).resolve().parents[1]


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


def resolve_in_workspace(raw: str, root: Optional[Path] = None) -> Path:
    if not raw or raw.startswith("~"):
        raise ToolError("path is outside the workspace")
    root = (root or workspace_root()).resolve()
    candidate = Path(raw)
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        raise ToolError("path is outside the workspace") from None
    return resolved


def refuse_secret(path: Path) -> None:
    if path.name in SECRET_NAMES or path.suffix in SECRET_SUFFIXES:
        raise ToolError("refusing to read a secret file")
