"""Apply or reset a demo incident without committing the broken state.

contract — overlay inventory/app.py with the renamed-field service
config   — write .env.local so orders starts pointed at :9001
noisy    — write demo-system/logs/orders.log
reset    — restore happy-path files and delete generated state
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

from incidents.catalog import CONFIG_INVENTORY_URL, DEMOS
from incidents.noisy import generate_log

ACTIVE_NAME = ".active"
ENV_LOCAL_NAME = ".env.local"
HAPPY_BACKUP_NAME = "app.py.happy"


def repo_root() -> Path:
    override = os.environ.get("ROOTSCOPE_ROOT")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2]


def _paths(root: Path) -> dict:
    incidents = root / "demo-system" / "incidents"
    inventory = root / "demo-system" / "inventory"
    return {
        "active": incidents / ACTIVE_NAME,
        "env_local": incidents / ENV_LOCAL_NAME,
        "live_inventory": inventory / "app.py",
        "happy_backup": inventory / HAPPY_BACKUP_NAME,
        "overlay": incidents / "contract" / "inventory_app.py",
        "orders_log": root / "demo-system" / "logs" / "orders.log",
    }


def read_active(root: Optional[Path] = None) -> Optional[str]:
    active = _paths(root or repo_root())["active"]
    if not active.exists():
        return None
    key = active.read_text().strip()
    return key if key in DEMOS else None


def reset(root: Optional[Path] = None) -> None:
    paths = _paths(root or repo_root())
    backup = paths["happy_backup"]
    live = paths["live_inventory"]
    if backup.exists():
        live.write_text(backup.read_text())
        backup.unlink()
    for name in ("active", "env_local", "orders_log"):
        path = paths[name]
        if path.exists():
            path.unlink()


def apply(key: str, root: Optional[Path] = None) -> str:
    if key not in DEMOS:
        raise ValueError(f"unknown incident: {key}")
    root = root or repo_root()
    paths = _paths(root)
    reset(root)

    if key == "contract":
        live = paths["live_inventory"]
        if not paths["happy_backup"].exists():
            paths["happy_backup"].write_text(live.read_text())
        live.write_text(paths["overlay"].read_text())
    elif key == "config":
        paths["env_local"].write_text(f"INVENTORY_URL={CONFIG_INVENTORY_URL}\n")
    elif key == "noisy":
        generate_log(paths["orders_log"])

    paths["active"].write_text(key + "\n")
    return key


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Apply or reset a RootScope demo incident")
    parser.add_argument("action", choices=["contract", "config", "noisy", "reset", "status"])
    args = parser.parse_args(argv)
    if args.action == "status":
        print(read_active() or "none")
        return 0
    if args.action == "reset":
        reset()
        print("reset")
        return 0
    apply(args.action)
    print(args.action)
    return 0


if __name__ == "__main__":
    sys.exit(main())
