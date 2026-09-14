from agent.agent import run_investigation
from agent.client import ScriptedResponses
from agent.workspace import workspace_root

SCRIPT = [
    ("read_file", {"path": "demo-system/inventory/app.py"}),
    ("read_file", {"path": "demo-system/orders/app.py"}),
    ("read_file", {"path": "demo-system/contracts/inventory-contract.json"}),
    (
        "submit_diagnosis",
        {
            "root_cause": (
                "Inventory renamed available to available_quantity; "
                "orders still reads available."
            ),
            "confidence": "high",
            "evidence": [
                {
                    "kind": "code",
                    "path": "demo-system/inventory/app.py",
                    "excerpt": "available",
                }
            ],
            "affected_services": ["inventory", "orders"],
            "affected_files": [
                "demo-system/inventory/app.py",
                "demo-system/orders/app.py",
            ],
            "proposed_fix_summary": (
                "Keep one field name in inventory, orders, and the contract."
            ),
            "proposed_fix_files": [
                "demo-system/orders/app.py",
                "demo-system/contracts/inventory-contract.json",
            ],
        },
    ),
]


def test_scripted_investigation_returns_diagnosis():
    events = []
    diagnosis = run_investigation(
        {
            "id": "RS-TEST",
            "title": "Contract Regression",
            "description": "Orders started returning 500.",
            "demo_key": "contract",
        },
        client=ScriptedResponses(SCRIPT),
        root=workspace_root(),
        on_event=lambda label, state, detail: events.append((label, state)),
    )
    assert diagnosis.confidence == "high"
    assert "available_quantity" in diagnosis.root_cause
    assert "orders" in diagnosis.affected_services
    labels = [label for label, _state in events]
    assert labels.count("read_file") >= 3
    assert "submit_diagnosis" in labels
