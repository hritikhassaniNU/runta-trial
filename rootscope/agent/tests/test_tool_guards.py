import pytest

from agent.tools import dispatch
from agent.tools import files, logs, services, shell, tests as test_tool
from agent.workspace import ToolError


def test_read_file_refuses_escape_and_env(tmp_path):
    (tmp_path / "ok.txt").write_text("hello")
    (tmp_path / ".env").write_text("OPENAI_API_KEY=secret")
    assert "hello" in files.read_file("ok.txt", root=tmp_path)
    with pytest.raises(ToolError, match="outside"):
        files.read_file("../ok.txt", root=tmp_path)
    with pytest.raises(ToolError, match="secret"):
        files.read_file(".env", root=tmp_path)


def test_search_repo_caps_results(tmp_path):
    for i in range(80):
        (tmp_path / f"f{i}.txt").write_text("NEEDLE line")
    result = files.search_repo("NEEDLE", root=tmp_path)
    assert result.count("NEEDLE") <= 12
    assert "capped" in result


def test_run_command_rejects_dangerous_argv(tmp_path):
    (tmp_path / "x.txt").write_text("x")
    with pytest.raises(ToolError, match="not allowlisted"):
        shell.run_command("rm -rf /", root=tmp_path)
    with pytest.raises(ToolError, match="status\\|diff\\|log"):
        shell.run_command("git push origin main", root=tmp_path)
    with pytest.raises(ToolError, match="host is not allowed"):
        shell.run_command("curl https://example.com/", root=tmp_path)


def test_check_service_rejects_arbitrary_egress():
    with pytest.raises(ToolError, match="host"):
        services.check_service(url="http://example.com/health")
    with pytest.raises(ToolError, match="port"):
        services.check_service(url="http://127.0.0.1:22/")


def test_run_tests_rejects_unknown_target(tmp_path):
    with pytest.raises(ToolError, match="unknown test target"):
        test_tool.run_tests("../../../etc", root=tmp_path)


def test_read_logs_caps_and_finds_error(tmp_path):
    log = tmp_path / "demo-system" / "logs" / "orders.log"
    log.parent.mkdir(parents=True)
    lines = [f"INFO heartbeat {i}" for i in range(4000)]
    lines[1847] = "ERROR order confirmation failed sku=ABC KeyError: 'available'"
    log.write_text("\n".join(lines) + "\n")
    tail = logs.read_logs("orders", tail_lines=50, root=tmp_path)
    assert "ERROR" not in tail
    assert "longer than this tail" in tail
    found = logs.read_logs("orders", query="ERROR", root=tmp_path)
    assert "KeyError" in found
    assert found.count("\n") < 20


def test_dispatch_unknown_tool():
    with pytest.raises(ToolError, match="unknown tool"):
        dispatch("rm", {})
