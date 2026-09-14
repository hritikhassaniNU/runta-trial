import json

from agent.runta_ready import (
    SECRET_PLACEHOLDER,
    check_inspect,
    check_secret_config,
    create_command,
    load_secret_config,
    secret_config_path,
)
from agent.workspace import workspace_root


def test_secret_config_injects_openai_key_and_header():
    errors = check_secret_config(load_secret_config())
    assert errors == []
    data = load_secret_config()
    assert data[0]["secret_id"] == SECRET_PLACEHOLDER


def test_results_copy_has_expected_secret_shape_if_present():
    sibling = workspace_root().parent / "results" / "rootscope" / "secret-config.json"
    if sibling.exists():
        data = json.loads(sibling.read_text())
        assert check_secret_config(data) == []


def test_inspect_example_passes():
    raw = json.loads(
        (workspace_root() / "deploy" / "inspect-ok.example.json").read_text()
    )
    assert check_inspect(raw) == []


def test_inspect_rejects_missing_saving_flags():
    payload = {
        "llm_tool_io_capture_enabled": True,
        "llm_token_saving_policy": {
            "json_array_enabled": False,
            "log_enabled": True,
            "search_results_enabled": True,
            "git_diff_enabled": True,
        },
        "secret_configuration": load_secret_config(),
    }
    errors = check_inspect(payload)
    assert any("json_array_enabled" in item for item in errors)


def test_create_command_uses_explicit_rest_payload():
    command = create_command()
    assert "POST" in command
    assert "deploy/create-runtime.json" in command
    assert "api.runta.com/v2/runtimes" in command


def test_create_runtime_json_has_all_saving_flags_on():
    payload = json.loads(
        (workspace_root() / "deploy" / "create-runtime.json").read_text()
    )
    policy = payload["llm_token_saving_policy"]
    assert payload["llm_tool_io_capture_enabled"] is True
    assert payload["image"]["model_provider_protocol"] == "openai_responses"
    assert payload["image"]["model_provider_model"] == "gpt-4.1"
    assert all(policy[key] is True for key in policy)
    assert check_secret_config(payload["secret_configuration"]) == []


def test_runta_scripts_exist():
    scripts = workspace_root() / "scripts"
    for name in (
        "runta-start.sh",
        "runta-stop.sh",
        "runta-health.sh",
        "runta-inspect-check.py",
        "runta-print-create.sh",
    ):
        assert (scripts / name).is_file(), name
