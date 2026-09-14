from agent.artifacts import generate_artifact, kinds_for
from agent.schemas import Diagnosis, Evidence, InvestigationEvent, ProposedFix


def _diagnosis(**overrides) -> Diagnosis:
    data = {
        "incident_id": "RS-TEST",
        "root_cause": "Inventory renamed available to available_quantity.",
        "confidence": "high",
        "evidence": [
            Evidence(kind="code", path="demo-system/orders/app.py", excerpt="available")
        ],
        "affected_services": ["inventory", "orders"],
        "affected_files": ["demo-system/orders/app.py"],
        "proposed_fix": ProposedFix(
            summary="Accept both field names in orders.",
            files=["demo-system/orders/app.py"],
        ),
        "test_result": None,
        "git_diff": None,
    }
    data.update(overrides)
    return Diagnosis(**data)


def _incident() -> dict:
    return {
        "id": "RS-TEST",
        "title": "Contract Regression",
        "description": "Orders started returning 500.",
    }


def test_kinds_for_omits_decision_brief_unless_low():
    assert kinds_for(_diagnosis()) == ["change_brief", "runbook", "postmortem"]
    assert kinds_for(_diagnosis(confidence="low")) == [
        "change_brief",
        "runbook",
        "postmortem",
        "decision_brief",
    ]


def test_change_brief_marks_sandbox_when_tests_pass():
    before = generate_artifact("change_brief", _incident(), _diagnosis())
    assert before["files"] == ["demo-system/orders/app.py"]
    assert before["sandbox_tested"] is False
    assert before["test_result"] == "not run — Apply Fix first"

    after = generate_artifact(
        "change_brief",
        _incident(),
        _diagnosis(test_result="exit=0\n2 passed", git_diff="diff --git a/orders"),
    )
    assert after["sandbox_tested"] is True
    assert after["diff_present"] is True
    assert "Low" in after["risk"]


def test_runbook_and_postmortem_fields():
    events = [
        InvestigationEvent(
            incident_id="RS-TEST",
            seq=1,
            label="investigate",
            state="done",
            detail="diagnosed",
            created_at="2026-09-13T00:00:00+00:00",
        )
    ]
    runbook = generate_artifact("runbook", _incident(), _diagnosis())
    assert "GET http://127.0.0.1:8001/health" in runbook["checks"]
    assert runbook["affected_services"] == ["inventory", "orders"]

    postmortem = generate_artifact("postmortem", _incident(), _diagnosis(), events)
    assert postmortem["root_cause"].startswith("Inventory renamed")
    assert postmortem["timeline"][0]["label"] == "investigate"
    assert postmortem["action_items"]


def test_decision_brief_recommends_more_investigation():
    brief = generate_artifact("decision_brief", _incident(), _diagnosis(confidence="low"))
    assert brief["recommendation"] == "investigate_more"
    assert {option["id"] for option in brief["options"]} == {"apply", "investigate_more"}
