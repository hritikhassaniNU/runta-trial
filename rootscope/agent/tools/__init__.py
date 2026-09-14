"""Tool schemas for the Responses API and a local dispatcher."""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, Optional

from agent.tools import files, git, logs, services, shell, tests
from agent.workspace import ToolError

MAX_TOOL_OUTPUT = 24_000


def _fn(name: str, description: str, properties: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "type": "function",
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": list(properties.keys()),
            "additionalProperties": False,
        },
        "strict": True,
    }


NULLABLE_STRING = {"type": ["string", "null"]}

TOOL_SCHEMAS = [
    _fn(
        "read_file",
        "Read a file under the workspace. Secrets (.env) are refused.",
        {"path": {"type": "string", "description": "Path relative to the workspace"}},
    ),
    _fn(
        "search_repo",
        "Search workspace files for a string. Results are capped.",
        {"query": {"type": "string"}},
    ),
    _fn(
        "read_logs",
        "Read a named service log. Use query to find buried lines in noisy logs.",
        {
            "name": {
                "type": "string",
                "enum": ["orders", "inventory_uvicorn", "orders_uvicorn", "api_uvicorn"],
            },
            "query": {**NULLABLE_STRING, "description": "Substring filter, or null"},
            "tail_lines": {
                "type": ["integer", "null"],
                "description": "Lines from the end when query is null. Max 500.",
            },
        },
    ),
    _fn(
        "run_command",
        "Run an allowlisted command: pytest, curl (demo hosts), git status|diff|log, ls, sed -n.",
        {"command": {"type": "string"}},
    ),
    _fn(
        "check_service",
        "HTTP GET a demo service health/URL. No arbitrary egress.",
        {
            "name": {
                "type": ["string", "null"],
                "description": "inventory | orders | api | inventory_sku",
            },
            "url": {**NULLABLE_STRING, "description": "Optional localhost URL on :8000-8002 or :9001"},
        },
    ),
    _fn(
        "run_tests",
        "Run pytest on a named target.",
        {
            "target": {
                "type": "string",
                "enum": ["inventory", "orders", "incidents", "api", "integration"],
            }
        },
    ),
    _fn(
        "git_diff",
        "Show git diff in the workspace. Does not commit.",
        {"path": {**NULLABLE_STRING, "description": "Optional path relative to the workspace"}},
    ),
    _fn(
        "submit_diagnosis",
        "Submit the final diagnosis. Call this once when evidence is enough. Do not modify files.",
        {
            "root_cause": {"type": "string"},
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
            "evidence": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "kind": {"type": "string"},
                        "path": {"type": "string"},
                        "excerpt": {"type": "string"},
                    },
                    "required": ["kind", "path", "excerpt"],
                    "additionalProperties": False,
                },
            },
            "affected_services": {"type": "array", "items": {"type": "string"}},
            "affected_files": {"type": "array", "items": {"type": "string"}},
            "proposed_fix_summary": {"type": "string"},
            "proposed_fix_files": {"type": "array", "items": {"type": "string"}},
        },
    ),
]


def dispatch(name: str, arguments: Dict[str, Any], root=None) -> str:
    if name == "submit_diagnosis":
        raise ToolError("submit_diagnosis is handled by the agent loop")
    handlers: Dict[str, Callable[..., str]] = {
        "read_file": lambda **kw: files.read_file(kw["path"], root=root),
        "search_repo": lambda **kw: files.search_repo(kw["query"], root=root),
        "read_logs": lambda **kw: logs.read_logs(
            kw["name"],
            query=kw.get("query"),
            tail_lines=kw.get("tail_lines") or logs.DEFAULT_TAIL,
            root=root,
        ),
        "run_command": lambda **kw: shell.run_command(kw["command"], root=root),
        "check_service": lambda **kw: services.check_service(
            name=kw.get("name"), url=kw.get("url")
        ),
        "run_tests": lambda **kw: tests.run_tests(kw["target"], root=root),
        "git_diff": lambda **kw: git.git_diff(path=kw.get("path"), root=root),
    }
    if name not in handlers:
        raise ToolError(f"unknown tool: {name}")
    try:
        output = handlers[name](**arguments)
    except ToolError:
        raise
    except Exception as exc:  # noqa: BLE001 — model-visible, not a crash
        raise ToolError(f"{name} failed: {exc}") from exc
    if len(output) > MAX_TOOL_OUTPUT:
        output = output[:MAX_TOOL_OUTPUT] + "\n... truncated"
    return output


def format_tool_error(exc: ToolError) -> str:
    return json.dumps({"error": str(exc)})
