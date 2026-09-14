"""Copy demo-system into an isolated git sandbox. The live workspace is not written."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from agent.workspace import workspace_root
from incidents.apply import apply

SKIP_NAMES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    ".next",
    "__pycache__",
    ".active",
    ".env.local",
    "app.py.happy",
}


def create_sandbox(source: Path, demo_key: Optional[str] = None) -> Path:
    dest = Path(tempfile.mkdtemp(prefix="rootscope-fix-"))
    _copy_tree(source / "demo-system", dest / "demo-system")
    if (source / "tests").is_dir():
        _copy_tree(source / "tests", dest / "tests")
    pytest_ini = source / "pytest.ini"
    if pytest_ini.exists():
        shutil.copy2(pytest_ini, dest / "pytest.ini")
    if demo_key:
        apply(demo_key, root=dest)
    _git_init(dest)
    return dest


def _copy_tree(src: Path, dest: Path) -> None:
    if not src.exists():
        return
    shutil.copytree(src, dest, ignore=_ignore)


def _ignore(_directory: str, names):
    return [name for name in names if name in SKIP_NAMES or name.endswith(".pyc")]


def _git_init(dest: Path) -> None:
    extra = {"start_new_session": True}
    subprocess.run(["git", "init"], cwd=dest, check=True, capture_output=True, **extra)
    subprocess.run(["git", "add", "-A"], cwd=dest, check=True, capture_output=True, **extra)
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=rootscope@local",
            "-c",
            "user.name=rootscope",
            "commit",
            "-m",
            "incident",
            "--allow-empty",
        ],
        cwd=dest,
        check=True,
        capture_output=True,
        **extra,
    )


def sandbox_diff(dest: Path) -> str:
    extra = {"start_new_session": True}
    subprocess.run(["git", "add", "-A"], cwd=dest, check=True, capture_output=True, **extra)
    result = subprocess.run(
        ["git", "diff", "--cached"],
        cwd=dest,
        capture_output=True,
        text=True,
        timeout=15,
        **extra,
    )
    return result.stdout or "(no diff)"


def sandbox_tests(dest: Path) -> str:
    project_python = workspace_root() / ".venv" / "bin" / "python"
    exe = str(project_python) if project_python.exists() else "python3"
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{dest}:{dest / 'demo-system'}"
    result = subprocess.run(
        [
            exe,
            "-m",
            "pytest",
            "demo-system/inventory/tests",
            "demo-system/orders/tests",
            "-q",
        ],
        cwd=dest,
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
        start_new_session=True,
    )
    out = (result.stdout + "\n" + result.stderr).strip()
    return f"exit={result.returncode}\n{out[-1500:]}"
