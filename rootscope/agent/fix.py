"""Apply a proposed fix in a sandbox. Investigate never calls this."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from agent.sandbox import create_sandbox, sandbox_diff, sandbox_tests
from agent.schemas import Diagnosis
from agent.tools.files import write_file
from agent.workspace import workspace_root

EventFn = Callable[[str, str, Optional[str]], None]


def remediation_key(incident: Dict[str, Any], diagnosis: Diagnosis) -> Optional[str]:
    if incident.get("demo_key"):
        return incident["demo_key"]
    text = f"{diagnosis.root_cause} {diagnosis.proposed_fix.summary}".lower()
    if "available_quantity" in text:
        return "contract"
    if "9001" in text or "inventory_url" in text:
        return "config"
    if "noisy" in text or "heartbeat" in text:
        return "noisy"
    return None


def run_apply_fix(
    incident: Dict[str, Any],
    diagnosis: Diagnosis,
    root=None,
    on_event: Optional[EventFn] = None,
) -> Diagnosis:
    root = Path(root or workspace_root()).resolve()
    key = remediation_key(incident, diagnosis)

    def emit(label: str, state: str, detail: Optional[str] = None) -> None:
        if on_event:
            on_event(label, state, detail)

    emit("apply_fix", "running", f"sandbox key={key or 'none'}")
    sandbox = create_sandbox(root, demo_key=key)
    emit("sandbox", "done", str(sandbox))
    try:
        if key == "contract":
            _fix_contract(sandbox, emit)
        elif key == "config":
            _fix_config(sandbox, emit)
        elif key == "noisy":
            _fix_noisy(sandbox, emit)
        else:
            emit("apply_fix", "error", "no automatic remediation for this ticket")
            diagnosis.test_result = "skipped: no automatic remediation"
            diagnosis.git_diff = "(no diff)"
            return diagnosis

        emit("run_tests", "running", "inventory + orders")
        test_result = sandbox_tests(sandbox)
        emit("run_tests", "done" if test_result.startswith("exit=0") else "error", test_result[:240])
        diff = sandbox_diff(sandbox)
        emit("git_diff", "done", diff[:240])
        diagnosis.test_result = test_result
        diagnosis.git_diff = diff
        emit("apply_fix", "done", "sandbox only; live workspace unchanged")
        return diagnosis
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)


def _fix_contract(sandbox: Path, emit: EventFn) -> None:
    orders = sandbox / "demo-system" / "orders" / "app.py"
    text = orders.read_text()
    old = "    available = inventory[\"available\"]\n"
    new = (
        "    if \"available\" in inventory:\n"
        "        available = inventory[\"available\"]\n"
        "    elif \"available_quantity\" in inventory:\n"
        "        available = inventory[\"available_quantity\"]\n"
        "    else:\n"
        "        raise KeyError(\"available\")\n"
    )
    if old not in text:
        raise RuntimeError("orders app.py did not match the expected availability read")
    write_file("demo-system/orders/app.py", text.replace(old, new, 1), root=sandbox)
    emit("write_file", "done", "demo-system/orders/app.py")

    contract_path = sandbox / "demo-system" / "contracts" / "inventory-contract.json"
    contract = json.loads(contract_path.read_text())
    response = contract["response"]
    response["required"] = ["sku", "available_quantity"]
    response["properties"] = {
        "sku": {"type": "string"},
        "available_quantity": {"type": "integer"},
    }
    write_file(
        "demo-system/contracts/inventory-contract.json",
        json.dumps(contract, indent=2) + "\n",
        root=sandbox,
    )
    emit("write_file", "done", "demo-system/contracts/inventory-contract.json")

    test_path = sandbox / "demo-system" / "inventory" / "tests" / "test_inventory.py"
    test_text = test_path.read_text().replace(
        '{"sku": "ABC", "available": 10}',
        '{"sku": "ABC", "available_quantity": 10}',
    )
    write_file("demo-system/inventory/tests/test_inventory.py", test_text, root=sandbox)
    emit("write_file", "done", "demo-system/inventory/tests/test_inventory.py")


def _fix_config(sandbox: Path, emit: EventFn) -> None:
    env_path = sandbox / "demo-system" / "incidents" / ".env.local"
    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text("INVENTORY_URL=http://127.0.0.1:8001\n")
    emit("write_file", "done", "demo-system/incidents/.env.local -> :8001")


def _fix_noisy(sandbox: Path, emit: EventFn) -> None:
    log = sandbox / "demo-system" / "logs" / "orders.log"
    error_lines = []
    if log.exists():
        error_lines = [line for line in log.read_text().splitlines() if line.startswith("ERROR ")]
    body = "# Extracted from the noisy orders log\n\n"
    body += "\n".join(error_lines) or "(no ERROR line found)\n"
    write_file("demo-system/logs/FINDINGS.md", body + "\n", root=sandbox)
    emit("write_file", "done", "demo-system/logs/FINDINGS.md")
