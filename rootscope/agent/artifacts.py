"""Build structured incident artifacts from a diagnosis. No extra model call."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from agent.schemas import ArtifactKind, Diagnosis, InvestigationEvent


def generate_artifact(
    kind: ArtifactKind,
    incident: Dict[str, Any],
    diagnosis: Diagnosis,
    events: Optional[List[InvestigationEvent]] = None,
) -> dict:
    events = events or []
    if kind == "change_brief":
        return _change_brief(incident, diagnosis)
    if kind == "runbook":
        return _runbook(incident, diagnosis)
    if kind == "postmortem":
        return _postmortem(incident, diagnosis, events)
    if kind == "decision_brief":
        return _decision_brief(incident, diagnosis)
    raise ValueError(f"unknown artifact: {kind}")


def kinds_for(diagnosis: Diagnosis) -> List[ArtifactKind]:
    kinds: List[ArtifactKind] = ["change_brief", "runbook", "postmortem"]
    if diagnosis.confidence == "low":
        kinds.append("decision_brief")
    return kinds


def _change_brief(incident: Dict[str, Any], diagnosis: Diagnosis) -> dict:
    files = diagnosis.proposed_fix.files or diagnosis.affected_files
    applied = bool(diagnosis.git_diff and diagnosis.git_diff != "(no diff)")
    return {
        "title": f"Change Brief — {incident.get('title')}",
        "incident_id": incident.get("id"),
        "summary": diagnosis.proposed_fix.summary or diagnosis.root_cause,
        "why": diagnosis.root_cause,
        "files": files,
        "sandbox_tested": bool(diagnosis.test_result and diagnosis.test_result.startswith("exit=0")),
        "test_result": diagnosis.test_result or "not run — Apply Fix first",
        "diff_present": applied,
        "risk": (
            "Low. Sandbox tests passed; live workspace was not modified."
            if diagnosis.test_result and diagnosis.test_result.startswith("exit=0")
            else "Medium. Confirm the sandbox patch before touching production."
        ),
        "rollback": (
            "Do not merge the sandbox patch. Live services stay on the current tree; "
            "run ./scripts/apply-incident.sh reset if a demo fixture is still applied."
        ),
    }


def _runbook(incident: Dict[str, Any], diagnosis: Diagnosis) -> dict:
    services = diagnosis.affected_services or ["inventory", "orders"]
    return {
        "title": f"Runbook — {incident.get('title')}",
        "incident_id": incident.get("id"),
        "symptoms": [
            incident.get("description") or incident.get("title"),
            diagnosis.root_cause,
        ],
        "checks": [
            "GET http://127.0.0.1:8001/health",
            "GET http://127.0.0.1:8001/inventory/ABC",
            "GET http://127.0.0.1:8002/health",
            "POST http://127.0.0.1:8002/orders {\"sku\":\"ABC\",\"quantity\":1}",
            "read_logs name=orders query=ERROR",
        ],
        "affected_services": services,
        "mitigation": diagnosis.proposed_fix.summary or "See diagnosis.",
        "escalate_if": "Orders still 5xx after the sandbox patch, or inventory is unreachable on :8001.",
    }


def _postmortem(
    incident: Dict[str, Any],
    diagnosis: Diagnosis,
    events: List[InvestigationEvent],
) -> dict:
    timeline = []
    for event in events:
        if event.state in {"done", "error"} and event.label in {
            "investigate",
            "apply_fix",
            "submit_diagnosis",
            "run_tests",
        }:
            timeline.append(
                {
                    "at": event.created_at,
                    "label": event.label,
                    "state": event.state,
                    "detail": (event.detail or "")[:180],
                }
            )
    return {
        "title": f"Postmortem — {incident.get('title')}",
        "incident_id": incident.get("id"),
        "root_cause": diagnosis.root_cause,
        "impact": (
            f"Services {', '.join(diagnosis.affected_services) or 'unknown'} "
            f"were affected. Confidence: {diagnosis.confidence}."
        ),
        "timeline": timeline,
        "what_went_well": [
            "Investigate and Apply Fix stayed separate.",
            "The sandbox ran tests without writing the live workspace.",
        ],
        "what_to_improve": [
            item.excerpt
            for item in diagnosis.evidence[:3]
        ] or ["Add a contract test that fails when a published field is renamed."],
        "action_items": [
            f"Review {path}" for path in (diagnosis.proposed_fix.files or diagnosis.affected_files)
        ] or ["Record the field rename in the published contract before deploy."],
    }


def _decision_brief(incident: Dict[str, Any], diagnosis: Diagnosis) -> dict:
    return {
        "title": f"Decision Brief — {incident.get('title')}",
        "incident_id": incident.get("id"),
        "question": "Apply the proposed sandbox fix, or gather more evidence first?",
        "why_uncertain": (
            f"Diagnosis confidence is {diagnosis.confidence}. "
            + diagnosis.root_cause
        ),
        "missing_evidence": [
            item.path for item in diagnosis.evidence
        ] or ["A failing live request and a matching contract test."],
        "options": [
            {
                "id": "apply",
                "label": "Apply the sandbox patch",
                "tradeoff": "Fast if the root cause is right; may miss a second failure mode.",
            },
            {
                "id": "investigate_more",
                "label": "Investigate again",
                "tradeoff": "Costs more time and tokens; better if the first pass was thin.",
            },
        ],
        "recommendation": "investigate_more",
    }
