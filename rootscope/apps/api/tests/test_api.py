import time

from fastapi.testclient import TestClient


def test_health_and_create_incident(tmp_path, monkeypatch):
    monkeypatch.setenv("ROOTSCOPE_DATABASE", str(tmp_path / "test.db"))
    monkeypatch.setenv("ROOTSCOPE_ROOT", str(tmp_path))
    from main import app, init_db

    init_db()
    client = TestClient(app)

    assert client.get("/health").json()["service"] == "rootscope-api"

    created = client.post("/api/incidents", json={"demo_key": "contract"})
    assert created.status_code == 201
    body = created.json()
    assert body["id"].startswith("RS-")
    assert body["demo_key"] == "contract"
    assert body["status"] == "created"

    fetched = client.get(f"/api/incidents/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["title"] == "Contract Regression"

    catalog = client.get("/api/demos")
    assert catalog.status_code == 200
    keys = {demo["key"] for demo in catalog.json()["demos"]}
    assert keys == {"contract", "config", "noisy"}
    assert catalog.json()["active"] is None


def test_freeform_requires_description(tmp_path, monkeypatch):
    monkeypatch.setenv("ROOTSCOPE_DATABASE", str(tmp_path / "test.db"))
    from main import app, init_db

    init_db()
    client = TestClient(app)
    assert client.post("/api/incidents", json={}).status_code == 422


def test_investigate_with_scripted_client(tmp_path, monkeypatch):
    monkeypatch.setenv("ROOTSCOPE_DATABASE", str(tmp_path / "test.db"))
    from agent.client import ScriptedResponses
    from agent.tests.test_scripted_investigation import SCRIPT
    import main

    main.init_db()
    monkeypatch.setattr(main, "get_client", lambda: ScriptedResponses(SCRIPT))
    client = TestClient(main.app)

    created = client.post("/api/incidents", json={"demo_key": "contract"})
    incident_id = created.json()["id"]
    started = client.post(f"/api/incidents/{incident_id}/investigate")
    assert started.status_code == 200
    assert started.json()["status"] == "investigating"

    detail = client.get(f"/api/incidents/{incident_id}")
    body = detail.json()
    assert body["status"] == "diagnosed"
    assert "available_quantity" in body["diagnosis"]["root_cause"]
    assert body["events"]

    streamed = []
    with client.stream("GET", f"/api/incidents/{incident_id}/events") as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        streamed.append(response.read().decode())
    payload = streamed[0]
    assert "read_file" in payload
    assert '"done": true' in payload or '"done":true' in payload

    diff = client.get("/api/diff")
    assert diff.status_code == 200
    assert "diff" in diff.json()

    applied = client.post(f"/api/incidents/{incident_id}/apply-fix")
    assert applied.status_code == 200
    assert applied.json()["status"] == "applying"
    after = None
    for _ in range(40):
        after = client.get(f"/api/incidents/{incident_id}").json()
        if after["status"] in {"fix_applied", "failed"}:
            break
        time.sleep(0.1)
    assert after["status"] == "fix_applied"
    assert after["diagnosis"]["test_result"].startswith("exit=0")
    assert "available_quantity" in after["diagnosis"]["git_diff"]


def test_apply_fix_requires_diagnosis(tmp_path, monkeypatch):
    monkeypatch.setenv("ROOTSCOPE_DATABASE", str(tmp_path / "test.db"))
    from main import app, init_db

    init_db()
    client = TestClient(app)
    created = client.post("/api/incidents", json={"demo_key": "contract"})
    blocked = client.post(f"/api/incidents/{created.json()['id']}/apply-fix")
    assert blocked.status_code == 409


def test_artifacts_require_diagnosis(tmp_path, monkeypatch):
    monkeypatch.setenv("ROOTSCOPE_DATABASE", str(tmp_path / "test.db"))
    from main import app, init_db

    init_db()
    client = TestClient(app)
    created = client.post("/api/incidents", json={"demo_key": "contract"})
    incident_id = created.json()["id"]
    assert client.post(f"/api/incidents/{incident_id}/artifacts").status_code == 409
    assert client.post(f"/api/incidents/{incident_id}/change-brief").status_code == 409


def test_artifacts_after_scripted_investigate(tmp_path, monkeypatch):
    monkeypatch.setenv("ROOTSCOPE_DATABASE", str(tmp_path / "test.db"))
    from agent.client import ScriptedResponses
    from agent.tests.test_scripted_investigation import SCRIPT
    import main

    main.init_db()
    monkeypatch.setattr(main, "get_client", lambda: ScriptedResponses(SCRIPT))
    client = TestClient(main.app)

    created = client.post("/api/incidents", json={"demo_key": "contract"})
    incident_id = created.json()["id"]
    client.post(f"/api/incidents/{incident_id}/investigate")

    generated = client.post(f"/api/incidents/{incident_id}/artifacts")
    assert generated.status_code == 200
    kinds = {item["kind"] for item in generated.json()["artifacts"]}
    assert kinds == {"change_brief", "runbook", "postmortem"}
    brief = next(
        item for item in generated.json()["artifacts"] if item["kind"] == "change_brief"
    )
    assert brief["body"]["incident_id"] == incident_id
    assert "orders" in brief["body"]["summary"].lower() or "available" in brief["body"]["why"]
    assert brief["body"]["sandbox_tested"] is False

    runbook = client.post(f"/api/incidents/{incident_id}/runbook")
    assert runbook.status_code == 200
    assert "8001/health" in runbook.json()["body"]["checks"][0]

    decision = client.post(f"/api/incidents/{incident_id}/decision-brief")
    assert decision.status_code == 409


def test_decision_brief_when_confidence_is_low(tmp_path, monkeypatch):
    monkeypatch.setenv("ROOTSCOPE_DATABASE", str(tmp_path / "test.db"))
    from agent.schemas import Diagnosis, ProposedFix
    from db import save_diagnosis
    from main import app, init_db

    init_db()
    client = TestClient(app)
    created = client.post("/api/incidents", json={"demo_key": "noisy"})
    incident_id = created.json()["id"]
    save_diagnosis(
        Diagnosis(
            incident_id=incident_id,
            root_cause="One ERROR is buried in a noisy log; evidence is thin.",
            confidence="low",
            proposed_fix=ProposedFix(summary="Extract the ERROR line into FINDINGS.md."),
        )
    )

    generated = client.post(f"/api/incidents/{incident_id}/artifacts")
    assert generated.status_code == 200
    kinds = {item["kind"] for item in generated.json()["artifacts"]}
    assert "decision_brief" in kinds
    decision = next(
        item for item in generated.json()["artifacts"] if item["kind"] == "decision_brief"
    )
    assert decision["body"]["recommendation"] == "investigate_more"

