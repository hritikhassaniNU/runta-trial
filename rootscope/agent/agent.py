"""Responses API investigation loop. Tools run locally; the model only chooses them."""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional

from agent.prompts import SYSTEM_PROMPT, user_prompt
from agent.schemas import Diagnosis, Evidence, ProposedFix
from agent.tools import TOOL_SCHEMAS, dispatch
from agent.workspace import ToolError, workspace_root
from incidents.apply import read_active

MAX_TURNS = 12
EventFn = Callable[[str, str, Optional[str]], None]


def run_investigation(
    incident: Dict[str, Any],
    client: Any,
    root=None,
    on_event: Optional[EventFn] = None,
) -> Diagnosis:
    root = root or workspace_root()
    incident_id = incident["id"]

    def emit(label: str, state: str, detail: Optional[str] = None) -> None:
        if on_event:
            on_event(label, state, detail)

    emit("investigate", "running", f"model={getattr(client, 'model', 'scripted')}")
    payload_input: Any = [
        {
            "role": "user",
            "content": user_prompt(incident, active_fixture=read_active(root)),
        }
    ]
    previous_id = None
    nudged = False

    for _turn in range(MAX_TURNS):
        request: Dict[str, Any] = {
            "instructions": SYSTEM_PROMPT,
            "input": payload_input,
            "tools": TOOL_SCHEMAS,
            "tool_choice": "auto",
        }
        if previous_id:
            request["previous_response_id"] = previous_id
        response = client.create(**request)
        previous_id = response.get("id") or previous_id
        calls = [
            item
            for item in response.get("output") or []
            if item.get("type") == "function_call"
        ]
        if not calls:
            if not nudged:
                nudged = True
                payload_input = (
                    "You must call submit_diagnosis now. Do not reply in prose."
                )
                continue
            raise RuntimeError("model stopped without submit_diagnosis")

        outputs = []
        for item in calls:
            name = item["name"]
            raw_args = item.get("arguments") or "{}"
            args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            emit(name, "running", _short(raw_args if isinstance(raw_args, str) else json.dumps(args)))
            if name == "submit_diagnosis":
                diagnosis = _diagnosis_from_args(incident_id, args)
                emit("submit_diagnosis", "done", diagnosis.root_cause[:240])
                emit("investigate", "done", diagnosis.confidence)
                return diagnosis
            try:
                result = dispatch(name, args, root=root)
                emit(name, "done", result[:240])
                output = result
            except ToolError as exc:
                output = json.dumps({"error": str(exc)})
                emit(name, "error", str(exc))
            outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": item.get("call_id") or name,
                    "output": output,
                }
            )
        payload_input = outputs

    raise RuntimeError(f"agent stopped after {MAX_TURNS} turns without a diagnosis")


def _diagnosis_from_args(incident_id: str, args: Dict[str, Any]) -> Diagnosis:
    evidence = [Evidence(**item) for item in args.get("evidence") or []]
    return Diagnosis(
        incident_id=incident_id,
        root_cause=args["root_cause"],
        confidence=args["confidence"],
        evidence=evidence,
        affected_services=list(args.get("affected_services") or []),
        affected_files=list(args.get("affected_files") or []),
        proposed_fix=ProposedFix(
            summary=args.get("proposed_fix_summary") or "",
            files=list(args.get("proposed_fix_files") or []),
        ),
    )


def _short(text: str, limit: int = 180) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit] + "…"
