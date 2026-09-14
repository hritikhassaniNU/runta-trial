"""run_command. Allowlisted argv only. Never shell=True."""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

from agent.workspace import ToolError, resolve_in_workspace, workspace_root
from agent.tools.services import ALLOWED_HOSTS, ALLOWED_PORTS

OUTPUT_CAP = 12_000


def run_command(command: str, root: Optional[Path] = None) -> str:
    if not command or command.strip() != command.strip():
        raise ToolError("command is empty")
    argv = shlex.split(command)
    if not argv:
        raise ToolError("command is empty")
    root = (root or workspace_root()).resolve()
    _assert_allowed(argv, root)
    result = subprocess.run(
        argv,
        cwd=root,
        capture_output=True,
        text=True,
        timeout=30,
    )
    out = (result.stdout + result.stderr).strip()
    if len(out) > OUTPUT_CAP:
        out = out[:OUTPUT_CAP] + "\n... truncated"
    return f"exit={result.returncode}\n{out}"


def _assert_allowed(argv: List[str], root: Path) -> None:
    head = Path(argv[0]).name
    if head == "pytest":
        return
    if head == "ls":
        for arg in argv[1:]:
            if arg.startswith("-"):
                continue
            resolve_in_workspace(arg, root)
        return
    if head == "git":
        if len(argv) < 2 or argv[1] not in {"status", "diff", "log"}:
            raise ToolError("only git status|diff|log is allowed")
        if any(tok in {"push", "commit", "reset", "checkout", "rebase"} for tok in argv):
            raise ToolError("git mutation is not allowed")
        return
    if head == "sed":
        if len(argv) < 3 or argv[1] != "-n":
            raise ToolError("only sed -n is allowed")
        resolve_in_workspace(argv[-1], root)
        return
    if head == "curl":
        _assert_curl(argv)
        return
    raise ToolError(f"command {head!r} is not allowlisted")


def _assert_curl(argv: List[str]) -> None:
    url = None
    for arg in argv[1:]:
        if arg.startswith("http://") or arg.startswith("https://"):
            url = arg
            break
    if url is None:
        raise ToolError("curl needs an http URL")
    parsed = urlparse(url)
    if parsed.scheme != "http" or parsed.hostname not in ALLOWED_HOSTS:
        raise ToolError("curl host is not allowed")
    if (parsed.port or 80) not in ALLOWED_PORTS:
        raise ToolError("curl port is not allowed")
