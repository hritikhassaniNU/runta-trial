"""run_tests. Named pytest targets only — no shell passthrough."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from agent.workspace import ToolError, workspace_root

TARGETS: Dict[str, List[str]] = {
    "inventory": ["demo-system/inventory/tests"],
    "orders": ["demo-system/orders/tests"],
    "incidents": ["demo-system/incidents/tests"],
    "api": ["apps/api/tests"],
    "integration": ["tests"],
}


def run_tests(target: str, root: Optional[Path] = None) -> str:
    if target not in TARGETS:
        raise ToolError(
            f"unknown test target {target!r}; allowed: {', '.join(sorted(TARGETS))}"
        )
    root = (root or workspace_root()).resolve()
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{root}:{root / 'demo-system'}:{root / 'apps' / 'api'}"
    python = root / ".venv" / "bin" / "python"
    exe = str(python) if python.exists() else "python3"
    result = subprocess.run(
        [exe, "-m", "pytest", *TARGETS[target], "-q"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )
    out = (result.stdout + "\n" + result.stderr).strip()
    return f"exit={result.returncode}\n{out[-1500:]}"
