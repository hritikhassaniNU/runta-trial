"""RootScope API. Milestone 6: investigate, Apply Fix, artifacts."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import threading
import time

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from incidents.apply import read_active
from incidents.catalog import DEMOS

from agent.agent import run_investigation
from agent.artifacts import generate_artifact, kinds_for
from agent.client import get_client
from agent.fix import run_apply_fix
from agent.schemas import Artifact, ArtifactKind
from agent.workspace import load_dotenv, workspace_root
from db import (
    append_event,
    clear_investigation,
    connect,
    init_db,
    list_artifacts,
    list_events,
    load_diagnosis,
    next_incident_id,
    save_artifact,
    save_diagnosis,
    set_status,
)
from models import (
    DemoCatalog,
    DemoFixture,
    Incident,
    IncidentCreate,
    IncidentDetail,
    IncidentList,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    load_dotenv(workspace_root() / ".env")
    init_db()
    yield


app = FastAPI(title="rootscope-api", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "rootscope-api"}


@app.get("/api/demos", response_model=DemoCatalog)
def list_demos():
    return DemoCatalog(
        demos=[DemoFixture(**item) for item in DEMOS.values()],
        active=read_active(),
    )


@app.get("/api/incidents", response_model=IncidentList)
def list_incidents():
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM incidents ORDER BY created_at DESC"
        ).fetchall()
    return IncidentList(incidents=[Incident(**dict(row)) for row in rows])


@app.get("/api/incidents/{incident_id}", response_model=IncidentDetail)
def get_incident(incident_id: str):
    incident = _get_incident(incident_id)
    return IncidentDetail(
        **incident.model_dump(),
        events=list_events(incident_id),
        diagnosis=load_diagnosis(incident_id),
        artifacts=list_artifacts(incident_id),
    )


@app.get("/api/incidents/{incident_id}/events")
def stream_events(incident_id: str):
    _get_incident(incident_id)

    def generate():
        last = 0
        idle = 0
        while idle < 150:
            rows = list_events(incident_id)
            new = [event for event in rows if event.seq > last]
            for event in new:
                yield f"data: {event.model_dump_json()}\n\n"
                last = event.seq
            incident = _get_incident(incident_id)
            if incident.status not in {"investigating", "applying"} and not new:
                yield "data: {\"done\": true}\n\n"
                return
            if not new:
                idle += 1
            else:
                idle = 0
            time.sleep(0.4)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/diff")
def workspace_diff():
    from agent.tools.git import git_diff
    from agent.workspace import ToolError

    try:
        return {"diff": git_diff(path="demo-system")}
    except ToolError as exc:
        return {"diff": "", "error": str(exc)}


@app.post("/api/incidents", response_model=Incident, status_code=201)
def create_incident(body: IncidentCreate):
    if body.demo_key:
        demo = DEMOS[body.demo_key]
        title = demo["title"]
        description = body.description or demo["description"]
        source = "demo"
    else:
        description = body.description.strip()
        if not description:
            raise HTTPException(
                status_code=422, detail="description or demo_key is required"
            )
        title = description.split("\n", 1)[0][:80]
        source = "freeform"

    incident = Incident(
        id=next_incident_id(),
        title=title,
        description=description,
        source=source,
        demo_key=body.demo_key,
        status="created",
        created_at=datetime.now(timezone.utc),
    )
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO incidents
            (id, title, description, source, demo_key, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                incident.id,
                incident.title,
                incident.description,
                incident.source,
                incident.demo_key,
                incident.status,
                incident.created_at.isoformat(),
            ),
        )
    return incident


@app.post("/api/incidents/{incident_id}/investigate", response_model=Incident)
def investigate(incident_id: str, background_tasks: BackgroundTasks):
    incident = _get_incident(incident_id)
    if incident.status == "investigating":
        raise HTTPException(status_code=409, detail="investigation already running")
    clear_investigation(incident_id)
    set_status(incident_id, "investigating")
    append_event(incident_id, "investigate", "pending", "queued")
    background_tasks.add_task(_run_job, incident_id)
    return Incident(**{**incident.model_dump(), "status": "investigating"})


@app.post("/api/incidents/{incident_id}/apply-fix", response_model=Incident)
def apply_fix(incident_id: str):
    incident = _get_incident(incident_id)
    if incident.status not in {"diagnosed", "failed", "fix_applied", "applying"}:
        raise HTTPException(
            status_code=409, detail="diagnose the incident before Apply Fix"
        )
    if load_diagnosis(incident_id) is None:
        raise HTTPException(status_code=409, detail="no diagnosis to apply")
    set_status(incident_id, "applying")
    append_event(incident_id, "apply_fix", "pending", "queued")
    threading.Thread(target=_run_apply, args=(incident_id,), daemon=True).start()
    return Incident(**{**incident.model_dump(), "status": "applying"})


@app.post("/api/incidents/{incident_id}/change-brief", response_model=Artifact)
def post_change_brief(incident_id: str):
    return _write_artifact(incident_id, "change_brief")


@app.post("/api/incidents/{incident_id}/runbook", response_model=Artifact)
def post_runbook(incident_id: str):
    return _write_artifact(incident_id, "runbook")


@app.post("/api/incidents/{incident_id}/postmortem", response_model=Artifact)
def post_postmortem(incident_id: str):
    return _write_artifact(incident_id, "postmortem")


@app.post("/api/incidents/{incident_id}/decision-brief", response_model=Artifact)
def post_decision_brief(incident_id: str):
    return _write_artifact(incident_id, "decision_brief")


@app.post("/api/incidents/{incident_id}/artifacts", response_model=IncidentDetail)
def post_artifacts(incident_id: str):
    incident = _get_incident(incident_id)
    diagnosis = load_diagnosis(incident_id)
    if diagnosis is None:
        raise HTTPException(status_code=409, detail="diagnose the incident first")
    for kind in kinds_for(diagnosis):
        _write_artifact(incident_id, kind)
    append_event(incident_id, "artifacts", "done", ",".join(kinds_for(diagnosis)))
    return IncidentDetail(
        **incident.model_dump(),
        events=list_events(incident_id),
        diagnosis=diagnosis,
        artifacts=list_artifacts(incident_id),
    )


def _write_artifact(incident_id: str, kind: ArtifactKind) -> Artifact:
    incident = _get_incident(incident_id)
    diagnosis = load_diagnosis(incident_id)
    if diagnosis is None:
        raise HTTPException(status_code=409, detail="diagnose the incident first")
    if kind == "decision_brief" and diagnosis.confidence != "low":
        raise HTTPException(
            status_code=409,
            detail="Decision Brief is only generated when confidence is low",
        )
    body = generate_artifact(kind, incident.model_dump(), diagnosis, list_events(incident_id))
    artifact = Artifact(
        incident_id=incident_id,
        kind=kind,
        body=body,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    save_artifact(artifact)
    append_event(incident_id, kind, "done", body.get("title"))
    return artifact


def _get_incident(incident_id: str) -> Incident:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM incidents WHERE id = ?", (incident_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="unknown incident")
    return Incident(**dict(row))


def _run_job(incident_id: str) -> None:
    def on_event(label, state, detail):
        append_event(incident_id, label, state, detail)

    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM incidents WHERE id = ?", (incident_id,)
        ).fetchone()
    if row is None:
        return
    try:
        diagnosis = run_investigation(
            dict(row), client=get_client(), on_event=on_event
        )
        save_diagnosis(diagnosis)
        set_status(incident_id, "diagnosed")
    except Exception as exc:  # noqa: BLE001 — persist failure, do not crash the worker
        append_event(incident_id, "investigate", "error", str(exc)[:500])
        set_status(incident_id, "failed")


def _run_apply(incident_id: str) -> None:
    def on_event(label, state, detail):
        append_event(incident_id, label, state, detail)

    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM incidents WHERE id = ?", (incident_id,)
        ).fetchone()
    diagnosis = load_diagnosis(incident_id)
    if row is None or diagnosis is None:
        set_status(incident_id, "failed")
        return
    try:
        updated = run_apply_fix(dict(row), diagnosis, on_event=on_event)
        save_diagnosis(updated)
        passed = (updated.test_result or "").startswith("exit=0")
        set_status(incident_id, "fix_applied" if passed else "failed")
        if not passed:
            append_event(incident_id, "apply_fix", "error", "sandbox tests failed")
    except Exception as exc:  # noqa: BLE001 — persist failure, do not crash the worker
        append_event(incident_id, "apply_fix", "error", str(exc)[:500])
        set_status(incident_id, "failed")
