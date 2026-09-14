"""Checks that RootScope is configured for a Runta runtime. Does not create one."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent.workspace import workspace_root

SECRET_PLACEHOLDER = "REPLACE_WITH_RUNTA_SECRET_ID"
SAVING_FLAGS = (
    "json_array_enabled",
    "log_enabled",
    "search_results_enabled",
    "git_diff_enabled",
)


def secret_config_path() -> Path:
    return workspace_root() / "deploy" / "secret-config.json"


def load_secret_config(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    target = path or secret_config_path()
    return json.loads(target.read_text())


def check_secret_config(data: List[Dict[str, Any]]) -> List[str]:
    errors: List[str] = []
    if not data:
        return ["secret-config is empty"]

    first = data[0]
    if not first.get("secret_id"):
        errors.append("secret_id is missing")

    names = [item.get("name") for item in first.get("environment") or []]
    if "OPENAI_API_KEY" not in names:
        errors.append("OPENAI_API_KEY is not injected as env")

    rules = first.get("egress_rules") or []
    if not any(
        rule.get("host_pattern") == "api.openai.com"
        and rule.get("path_pattern") == "/v1/*"
        and rule.get("name") == "Authorization"
        for rule in rules
    ):
        errors.append("Authorization header is not set on api.openai.com/v1/*")

    return errors


def unwrap_inspect(data: Dict[str, Any]) -> Dict[str, Any]:
    runtime = data.get("runtime")
    if isinstance(runtime, dict):
        return runtime
    return data


def check_inspect(data: Dict[str, Any]) -> List[str]:
    runtime = unwrap_inspect(data)
    errors: List[str] = []

    if runtime.get("llm_tool_io_capture_enabled") is not True:
        errors.append("llm_tool_io_capture_enabled is not true")

    policy = runtime.get("llm_token_saving_policy") or {}
    for flag in SAVING_FLAGS:
        if policy.get(flag) is not True:
            errors.append(f"llm_token_saving_policy.{flag} is not true")

    secrets = runtime.get("secret_configuration") or []
    if not secrets:
        errors.append("secret_configuration is empty")
    else:
        errors.extend(check_secret_config(secrets))

    return errors


def create_command() -> str:
    return """curl -sS \\
  -X POST \\
  -H \"Authorization: Bearer $RUNTA_TOKEN\" \\
  -H \"Content-Type: application/json\" \\
  --data-binary @deploy/create-runtime.json \\
  https://api.runta.com/v2/runtimes"""
