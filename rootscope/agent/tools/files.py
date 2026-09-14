"""read_file and search_repo. Capped, workspace-jailed."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import List

from agent.workspace import ToolError, refuse_secret, resolve_in_workspace, workspace_root

READ_FILE_LIMIT = 32_000
SEARCH_MAX_HITS = 12
SEARCH_LINE_LIMIT = 160
SKIP_DIR_NAMES = {".git", ".venv", "venv", "node_modules", ".next", "__pycache__", "data"}


WRITE_ROOTS = {"demo-system", "tests"}


def write_file(path: str, content: str, root: Path = None) -> str:
    target = resolve_in_workspace(path, root)
    refuse_secret(target)
    root = (root or workspace_root()).resolve()
    rel = target.relative_to(root)
    if rel.parts[0] not in WRITE_ROOTS:
        raise ToolError("write is limited to demo-system/ and tests/")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    return f"wrote {path} ({len(content)} bytes)"


def read_file(path: str, root: Path = None) -> str:
    target = resolve_in_workspace(path, root)
    refuse_secret(target)
    if not target.is_file():
        raise ToolError(f"not a file: {path}")
    data = target.read_bytes()
    text = data[:READ_FILE_LIMIT].decode("utf-8", errors="replace")
    if len(data) > READ_FILE_LIMIT:
        text += f"\n... truncated after {READ_FILE_LIMIT} bytes"
    return text


def search_repo(query: str, root: Path = None) -> str:
    if not query:
        raise ToolError("query is required")
    root = (root or workspace_root()).resolve()
    rg = shutil.which("rg")
    if rg:
        result = subprocess.run(
            [
                rg,
                "-n",
                "--max-count",
                str(SEARCH_MAX_HITS),
                "-g",
                "!.git",
                "-g",
                "!.venv",
                "-g",
                "!node_modules",
                "-g",
                "!.next",
                "-g",
                "!.env",
                "-g",
                "!*.happy",
                "-g",
                "!*.md",
                query,
                str(root),
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        lines = [line for line in result.stdout.splitlines() if line]
    else:
        lines = _walk_search(root, query)
    clipped = [_clip(line) for line in lines[:SEARCH_MAX_HITS]]
    if not clipped:
        return f"no matches for {query!r}"
    suffix = ""
    if len(lines) > SEARCH_MAX_HITS:
        suffix = f"\n... capped at {SEARCH_MAX_HITS} matches"
    return "\n".join(clipped) + suffix


def _clip(line: str) -> str:
    if len(line) <= SEARCH_LINE_LIMIT:
        return line
    return line[:SEARCH_LINE_LIMIT] + "…"


def _walk_search(root: Path, query: str) -> List[str]:
    hits: List[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        if path.suffix == ".md":
            continue
        try:
            refuse_secret(path)
        except ToolError:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            if query in line:
                rel = path.relative_to(root)
                hits.append(f"{rel}:{i}:{line}")
                if len(hits) >= SEARCH_MAX_HITS + 1:
                    return hits
    return hits
