"""git_diff. Read-only."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

from agent.workspace import ToolError, resolve_in_workspace, workspace_root

OUTPUT_CAP = 16_000


def git_diff(path: Optional[str] = None, root: Optional[Path] = None) -> str:
    root = (root or workspace_root()).resolve()
    argv = ["git", "diff"]
    if path:
        argv.append("--")
        argv.append(str(resolve_in_workspace(path, root)))
    result = subprocess.run(
        argv,
        cwd=root,
        capture_output=True,
        text=True,
        timeout=15,
    )
    if result.returncode != 0 and not result.stdout:
        raise ToolError(result.stderr.strip() or "git diff failed")
    out = result.stdout or "(no diff)"
    if len(out) > OUTPUT_CAP:
        out = out[:OUTPUT_CAP] + "\n... truncated"
    return out
