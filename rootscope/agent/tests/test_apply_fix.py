from agent.fix import run_apply_fix
from agent.schemas import Diagnosis, ProposedFix
from agent.tools.files import write_file
from agent.workspace import ToolError, workspace_root
import pytest


def _diagnosis(incident_id="RS-FIX"):
    return Diagnosis(
        incident_id=incident_id,
        root_cause="Inventory renamed available to available_quantity.",
        confidence="high",
        proposed_fix=ProposedFix(
            summary="Update orders and the contract to the new field.",
            files=["demo-system/orders/app.py"],
        ),
    )


def test_write_file_is_jailed(tmp_path):
    (tmp_path / "demo-system").mkdir()
    write_file("demo-system/ok.txt", "x", root=tmp_path)
    assert (tmp_path / "demo-system" / "ok.txt").read_text() == "x"
    with pytest.raises(ToolError, match="limited"):
        write_file("secrets.txt", "nope", root=tmp_path)
    with pytest.raises(ToolError, match="secret"):
        write_file("demo-system/.env", "OPENAI_API_KEY=x", root=tmp_path)


def test_sandbox_contract_fix_passes_and_does_not_touch_live():
    live = workspace_root() / "demo-system" / "inventory" / "app.py"
    before = live.read_text()
    events = []
    diagnosis = run_apply_fix(
        {
            "id": "RS-FIX",
            "demo_key": "contract",
            "title": "Contract Regression",
        },
        _diagnosis(),
        root=workspace_root(),
        on_event=lambda label, state, detail: events.append(label),
    )
    assert live.read_text() == before
    assert diagnosis.test_result.startswith("exit=0")
    assert "available_quantity" in (diagnosis.git_diff or "")
    assert "orders/app.py" in (diagnosis.git_diff or "")
    assert "write_file" in events
    assert "run_tests" in events


def test_sandbox_config_and_noisy_produce_results():
    root = workspace_root()
    config = run_apply_fix(
        {"id": "RS-CFG", "demo_key": "config", "title": "Configuration Failure"},
        Diagnosis(
            incident_id="RS-CFG",
            root_cause="Orders pointed at :9001.",
            confidence="high",
            proposed_fix=ProposedFix(summary="Point INVENTORY_URL at :8001."),
        ),
        root=root,
    )
    assert config.test_result.startswith("exit=0")
    assert ":8001" in (config.git_diff or "") or "INVENTORY_URL" in (config.git_diff or "")

    noisy = run_apply_fix(
        {"id": "RS-LOG", "demo_key": "noisy", "title": "Noisy Logs"},
        Diagnosis(
            incident_id="RS-LOG",
            root_cause="One ERROR is buried in heartbeats.",
            confidence="medium",
            proposed_fix=ProposedFix(summary="Extract the ERROR line."),
        ),
        root=root,
    )
    assert noisy.test_result.startswith("exit=0")
    assert "FINDINGS.md" in (noisy.git_diff or "")
    assert "KeyError" in (noisy.git_diff or "")
