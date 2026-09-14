"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import type {
  Artifact,
  DemoCatalog,
  Diagnosis,
  IncidentDetail,
  InvestigationEvent,
} from "../../lib/types";

const ARTIFACT_LABELS: Record<Artifact["kind"], string> = {
  change_brief: "Change Brief",
  runbook: "Runbook",
  postmortem: "Postmortem",
  decision_brief: "Decision Brief",
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function ArtifactValue({ value }: { value: unknown }) {
  if (typeof value === "boolean") {
    return <span>{value ? "yes" : "no"}</span>;
  }
  if (typeof value === "string" || typeof value === "number") {
    return <span>{String(value)}</span>;
  }
  if (Array.isArray(value)) {
    if (!value.length) {
      return <span className="meta">none</span>;
    }
    if (value.every((item) => typeof item === "string")) {
      return (
        <ul className="artifact-list">
          {value.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      );
    }
    return (
      <ul className="artifact-list">
        {value.map((item, index) => (
          <li key={index}>
            {isRecord(item) ? (
              <ArtifactFields body={item} />
            ) : (
              <span>{JSON.stringify(item)}</span>
            )}
          </li>
        ))}
      </ul>
    );
  }
  if (isRecord(value)) {
    return <ArtifactFields body={value} />;
  }
  return <span className="meta">—</span>;
}

function ArtifactFields({ body }: { body: Record<string, unknown> }) {
  return (
    <dl className="artifact-fields">
      {Object.entries(body)
        .filter(([key]) => key !== "title" && key !== "incident_id")
        .map(([key, value]) => (
          <div key={key}>
            <dt>{key.replace(/_/g, " ")}</dt>
            <dd>
              <ArtifactValue value={value} />
            </dd>
          </div>
        ))}
    </dl>
  );
}

function mergeEvent(
  events: InvestigationEvent[],
  incoming: InvestigationEvent
): InvestigationEvent[] {
  if (events.some((event) => event.seq === incoming.seq)) {
    return events;
  }
  return [...events, incoming].sort((a, b) => a.seq - b.seq);
}

function statusClass(status: string): string {
  if (status === "diagnosed" || status === "fix_applied") return "badge ok";
  if (status === "investigating" || status === "applying") return "badge warn";
  if (status === "failed") return "badge bad";
  return "badge";
}

export function IncidentWorkspace({
  initial,
  catalog,
}: {
  initial: IncidentDetail;
  catalog: DemoCatalog | null;
}) {
  const [status, setStatus] = useState(initial.status);
  const [events, setEvents] = useState<InvestigationEvent[]>(initial.events || []);
  const [diagnosis, setDiagnosis] = useState<Diagnosis | null>(
    initial.diagnosis || null
  );
  const [diff, setDiff] = useState(initial.diagnosis?.git_diff || "");
  const [artifacts, setArtifacts] = useState<Artifact[]>(initial.artifacts || []);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [streaming, setStreaming] = useState(false);
  const listRef = useRef<HTMLUListElement | null>(null);
  const sourceRef = useRef<EventSource | null>(null);

  const fixture = catalog?.demos?.find((demo) => demo.key === initial.demo_key);

  const loadDetail = useCallback(async () => {
    const response = await fetch(`/api/incidents/${initial.id}`, {
      cache: "no-store",
    });
    if (!response.ok) {
      return;
    }
    const body: IncidentDetail = await response.json();
    setStatus(body.status);
    setEvents(body.events || []);
    setDiagnosis(body.diagnosis || null);
    setArtifacts(body.artifacts || []);
    if (body.diagnosis?.git_diff) {
      setDiff(body.diagnosis.git_diff);
    }
  }, [initial.id]);

  const loadDiff = useCallback(async () => {
    const response = await fetch("/api/diff", { cache: "no-store" });
    if (!response.ok) {
      return;
    }
    const body = await response.json();
    if (!diagnosis?.git_diff) {
      setDiff(body.diff || "");
    }
  }, [diagnosis?.git_diff]);

  const stopStream = useCallback(() => {
    sourceRef.current?.close();
    sourceRef.current = null;
    setStreaming(false);
  }, []);

  const startStream = useCallback(() => {
    stopStream();
    const source = new EventSource(`/stream/incidents/${initial.id}`);
    sourceRef.current = source;
    setStreaming(true);
    source.onmessage = (message) => {
      if (!message.data) {
        return;
      }
      const payload = JSON.parse(message.data) as InvestigationEvent & {
        done?: boolean;
      };
      if (payload.done) {
        stopStream();
        void loadDetail().then(() => void loadDiff());
        setBusy(false);
        return;
      }
      if (typeof payload.seq === "number") {
        setEvents((current) => mergeEvent(current, payload));
        if (payload.label === "investigate" && payload.state === "running") {
          setStatus("investigating");
        }
        if (payload.label === "apply_fix" && payload.state === "running") {
          setStatus("applying");
        }
      }
    };
    source.onerror = () => {
      source.close();
      sourceRef.current = null;
      setStreaming(false);
      void loadDetail();
    };
  }, [initial.id, loadDetail, loadDiff, stopStream]);

  useEffect(() => {
    void loadDiff();
  }, [loadDiff]);

  useEffect(() => {
    if (initial.status === "investigating" || initial.status === "applying") {
      startStream();
    }
    return () => stopStream();
    // Subscribe once per incident. Re-running would drop the live stream.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initial.id]);

  useEffect(() => {
    listRef.current?.lastElementChild?.scrollIntoView({ block: "nearest" });
  }, [events]);

  async function applyFix() {
    setBusy(true);
    setError("");
    try {
      const started = await fetch(`/api/incidents/${initial.id}/apply-fix`, {
        method: "POST",
      });
      if (!started.ok) {
        throw new Error(await started.text());
      }
      setStatus("applying");
      startStream();
    } catch (err) {
      setError(err instanceof Error ? err.message : "apply failed");
      setBusy(false);
    }
  }

  async function generateArtifacts() {
    setBusy(true);
    setError("");
    try {
      const response = await fetch(`/api/incidents/${initial.id}/artifacts`, {
        method: "POST",
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      const body: IncidentDetail = await response.json();
      setEvents(body.events || []);
      setArtifacts(body.artifacts || []);
      setDiagnosis(body.diagnosis || diagnosis);
    } catch (err) {
      setError(err instanceof Error ? err.message : "artifacts failed");
    } finally {
      setBusy(false);
    }
  }

  async function start() {
    setBusy(true);
    setError("");
    setDiagnosis(null);
    setEvents([]);
    setArtifacts([]);
    try {
      const started = await fetch(`/api/incidents/${initial.id}/investigate`, {
        method: "POST",
      });
      if (!started.ok) {
        throw new Error(await started.text());
      }
      setStatus("investigating");
      startStream();
    } catch (err) {
      setError(err instanceof Error ? err.message : "investigate failed");
      setBusy(false);
    }
  }

  const running =
    busy || status === "investigating" || status === "applying" || streaming;
  const canApply =
    !running && (status === "diagnosed" || status === "failed" || status === "fix_applied");
  const canGenerate =
    !running && Boolean(diagnosis) && (status === "diagnosed" || status === "fix_applied" || status === "failed");

  return (
    <div className="workspace-grid">
      <aside className="panel">
        <div className="row">
          <p className="panel-title" style={{ margin: 0 }}>
            Run
          </p>
          <span className={statusClass(status)}>{status}</span>
        </div>
        <div className="progress">
          <span className={status !== "created" ? "on" : ""}>1 Investigate</span>
          <span className={status === "fix_applied" || status === "applying" ? "on" : ""}>
            2 Apply Fix
          </span>
          <span className={artifacts.length ? "on" : ""}>3 Artifacts</span>
        </div>
        {fixture ? (
          <>
            <p className="panel-copy" style={{ marginTop: 16 }}>
              Expected signal: {fixture.expected_signal}
            </p>
            <div className="callout">
              <p>
                A ticket does not apply the break. Run this from rootscope/
                before Investigate if the live stack should match.
              </p>
            </div>
            <pre>
              {fixture.apply_command}
              {fixture.needs_restart
                ? "\n# restarts inventory / orders / api if they are already up"
                : ""}
            </pre>
            <p className="meta" style={{ marginTop: 12 }}>
              Reset
            </p>
            <pre>{fixture.reset_command}</pre>
            <p className="meta" style={{ marginTop: 12 }}>
              Active fixture: {catalog?.active || "none (happy path)"}
            </p>
          </>
        ) : (
          <p className="panel-copy" style={{ marginTop: 16 }}>
            Freeform ticket. Investigate inspects whatever is running.
          </p>
        )}
        <div className="actions" style={{ marginTop: 16 }}>
          <button type="button" onClick={() => void start()} disabled={running}>
            {status === "investigating" ? "Investigating…" : "Investigate"}
          </button>
          <button
            type="button"
            className="copper"
            onClick={() => void applyFix()}
            disabled={!canApply}
          >
            {status === "applying" ? "Applying…" : "Apply Fix"}
          </button>
          <button
            type="button"
            className="secondary"
            onClick={() => void generateArtifacts()}
            disabled={!canGenerate}
          >
            {artifacts.length ? "Regenerate artifacts" : "Generate artifacts"}
          </button>
        </div>
        {error ? <div className="error-box">{error}</div> : null}
      </aside>

      <div>
        <div className="panel">
          <div className="row">
            <p className="panel-title" style={{ margin: 0 }}>
              Activity
            </p>
            {streaming ? <span className="badge warn">live</span> : (
              <span className="meta">{events.length} events</span>
            )}
          </div>
          {events.length ? (
            <ul className="timeline" ref={listRef}>
              {events.map((event) => (
                <li key={event.seq} className={`step ${event.state}`}>
                  <div className="step-head">
                    <strong>{event.label}</strong>
                    <span className="meta">{event.state}</span>
                  </div>
                  {event.detail ? <pre className="excerpt">{event.detail}</pre> : null}
                </li>
              ))}
            </ul>
          ) : (
            <p className="meta">Tool calls appear here as the agent works.</p>
          )}
        </div>

        {diagnosis ? (
          <div className="panel">
            <div className="row">
              <p className="panel-title" style={{ margin: 0 }}>
                Diagnosis
              </p>
              <span className={statusClass("diagnosed")}>{diagnosis.confidence}</span>
            </div>
            <p className="finding">{diagnosis.root_cause}</p>
            {diagnosis.affected_services?.length ? (
              <div className="chips">
                {diagnosis.affected_services.map((service) => (
                  <span className="chip" key={service}>
                    {service}
                  </span>
                ))}
              </div>
            ) : null}
            <p className="panel-title" style={{ marginTop: 20 }}>
              Proposed fix
            </p>
            <p>{diagnosis.proposed_fix?.summary}</p>
            {diagnosis.proposed_fix?.files?.length ? (
              <div className="chips">
                {diagnosis.proposed_fix.files.map((path) => (
                  <span className="chip" key={path}>
                    {path}
                  </span>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}

        {diagnosis?.evidence?.length ? (
          <div className="panel">
            <p className="panel-title">Evidence</p>
            <ul className="timeline">
              {diagnosis.evidence.map((item, index) => (
                <li key={`${item.path}-${index}`} className="step done">
                  <div className="step-head">
                    <strong>{item.path}</strong>
                    <span className="meta">{item.kind}</span>
                  </div>
                  <pre className="excerpt">{item.excerpt}</pre>
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        <div className="panel">
          <p className="panel-title">Sandbox diff</p>
          {diff && diff !== "(no diff)" ? (
            <pre className="diff">{diff}</pre>
          ) : (
            <p className="meta">
              No demo-system diff yet. Apply a fixture to see the overlay, or
              Apply Fix to persist the sandbox patch.
            </p>
          )}
          {diagnosis?.test_result ? (
            <>
              <p className="panel-title" style={{ marginTop: 18 }}>
                Sandbox tests
              </p>
              <pre className="excerpt">{diagnosis.test_result}</pre>
            </>
          ) : null}
          <p className="meta" style={{ marginTop: 16 }}>
            Apply Fix runs in a temp sandbox. The live workspace is not changed.
          </p>
        </div>

        {artifacts.length ? (
          <div className="artifact-grid">
            {artifacts.map((artifact) => (
              <div className="panel" key={artifact.kind} style={{ marginTop: 0 }}>
                <div className="row">
                  <p className="panel-title" style={{ margin: 0 }}>
                    {ARTIFACT_LABELS[artifact.kind]}
                  </p>
                  <span className="badge">{artifact.kind.replace(/_/g, " ")}</span>
                </div>
                {typeof artifact.body.title === "string" ? (
                  <p className="finding" style={{ fontSize: 16 }}>
                    {artifact.body.title}
                  </p>
                ) : null}
                <ArtifactFields body={artifact.body} />
              </div>
            ))}
          </div>
        ) : (
          <div className="panel">
            <p className="panel-title">Artifacts</p>
            <p className="panel-copy">
              After a diagnosis, generate a Change Brief, Runbook, and
              Postmortem. A Decision Brief is added only when confidence is
              low.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
