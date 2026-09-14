"""read_logs. The noisy incident is large; results are still capped."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from agent.workspace import ToolError, workspace_root

MAX_RETURN_LINES = 500
DEFAULT_TAIL = 80


def log_paths(root: Optional[Path] = None) -> Dict[str, Path]:
    root = root or workspace_root()
    return {
        "orders": root / "demo-system" / "logs" / "orders.log",
        "inventory_uvicorn": Path("/tmp/inventory.log"),
        "orders_uvicorn": Path("/tmp/orders.log"),
        "api_uvicorn": Path("/tmp/rootscope-api.log"),
    }


def read_logs(
    name: str,
    query: Optional[str] = None,
    tail_lines: int = DEFAULT_TAIL,
    root: Optional[Path] = None,
) -> str:
    paths = log_paths(root)
    if name not in paths:
        raise ToolError(
            f"unknown log {name!r}; allowed: {', '.join(sorted(paths))}"
        )
    path = paths[name]
    if not path.is_file():
        raise ToolError(f"log not found: {path}")
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    total = len(lines)
    needle = (query or "").strip()
    if needle:
        matched = [line for line in lines if needle in line]
        chosen = matched[:MAX_RETURN_LINES]
        header = f"{path} total={total} matches={len(matched)} showing={len(chosen)}"
        return header + "\n" + "\n".join(chosen)
    tail = max(1, min(int(tail_lines or DEFAULT_TAIL), MAX_RETURN_LINES))
    # Noisy-log / X-Ray path: if the file is huge and they asked for a large tail,
    # return up to MAX_RETURN_LINES so compression has something to chew on.
    chosen = lines[-tail:]
    header = f"{path} total={total} showing_last={len(chosen)}"
    note = ""
    if total > tail:
        note = (
            "\n# file is longer than this tail; search with query to find buried lines"
        )
    return header + "\n" + "\n".join(chosen) + note
