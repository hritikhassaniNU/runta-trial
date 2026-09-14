"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import type { IncidentSummary } from "./lib/types";

const DEMOS = [
  {
    key: "contract",
    tag: "Regression",
    title: "Contract break",
    blurb: "Inventory renamed a field. Orders still reads the old name and 500s.",
    hint: "POST /orders → 500",
  },
  {
    key: "config",
    tag: "Connectivity",
    title: "Wrong inventory URL",
    blurb: "Orders is pointed at :9001 instead of the live inventory on :8001.",
    hint: "POST /orders → 503",
  },
  {
    key: "noisy",
    tag: "Signal",
    title: "Buried ERROR",
    blurb: "Thousands of repeated log lines. One real error is in the middle.",
    hint: "read_logs query=ERROR",
  },
] as const;

function statusClass(status: string): string {
  if (status === "diagnosed" || status === "fix_applied") return "badge ok";
  if (status === "investigating" || status === "applying") return "badge warn";
  if (status === "failed") return "badge bad";
  return "badge";
}

function when(value?: string): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export default function DashboardPage() {
  const router = useRouter();
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [recent, setRecent] = useState<IncidentSummary[]>([]);
  const [apiUp, setApiUp] = useState<boolean | null>(null);

  useEffect(() => {
    void fetch("/health", { cache: "no-store" })
      .then((response) => {
        setApiUp(response.ok);
        return response.ok ? fetch("/api/incidents", { cache: "no-store" }) : null;
      })
      .then((response) => (response && response.ok ? response.json() : { incidents: [] }))
      .then((body) => setRecent(body.incidents || []))
      .catch(() => setApiUp(false));
  }, []);

  async function createIncident(body: { description?: string; demo_key?: string }) {
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/incidents", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        const text = await response.text();
        if (response.status === 500 && text.includes("Internal Server Error")) {
          throw new Error(
            "API is not running on :8000. From rootscope/: ./scripts/local-services.sh start"
          );
        }
        throw new Error(text);
      }
      const incident = await response.json();
      router.push(`/incidents/${incident.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "request failed");
      setBusy(false);
    }
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    void createIncident({ description });
  }

  return (
    <>
      <div className="hero">
        <div>
          <p className="kicker">AI incident investigation</p>
          <h1>Trace failures from symptom to verified fix.</h1>
          <p className="lede">
            RootScope investigates code, logs, service health, contracts, and
            tests — then explains the root cause, validates a sandboxed fix,
            and generates the operational follow-up.
          </p>
          <div className="hero-pills" aria-label="RootScope capabilities">
            <span>Tool-driven analysis</span>
            <span>Sandboxed remediation</span>
            <span>Evidence-first output</span>
          </div>
        </div>
        <div className="hero-signal">
          <span className={apiUp === false ? "signal-dot bad" : "signal-dot ok"} />
          <div>
            <strong>{apiUp === false ? "Stack unavailable" : "Investigation stack ready"}</strong>
            <span>Next.js · FastAPI · agent tools · demo services</span>
          </div>
        </div>
      </div>

      <div className="grid-2">
        <section className="panel composer">
          <div className="composer-head">
            <div>
              <h2>New investigation</h2>
              <p>
                Describe the production symptom. RootScope will create an investigation workspace without changing the demo stack.
              </p>
            </div>
          </div>
          <form onSubmit={onSubmit}>
            <label className="field-label" htmlFor="ticket-description">
              What happened?
            </label>
            <textarea
              id="ticket-description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Orders started returning 500 after the inventory deployment."
            />
            <div className="composer-examples">
              <span>Try</span>
              {[
                "Orders 500 after inventory deploy",
                "Inventory unreachable from orders",
                "One ERROR buried in orders logs",
              ].map((sample) => (
                <button
                  key={sample}
                  type="button"
                  className="ghost"
                  disabled={busy}
                  onClick={() => setDescription(sample)}
                >
                  {sample}
                </button>
              ))}
            </div>
            <div className="composer-foot">
              <p>
                Use a demo scenario when you want a reproducible failure with known evidence.
              </p>
              <button type="submit" disabled={busy || !description.trim()}>
                {busy ? "Creating…" : "Open investigation"}
              </button>
            </div>
          </form>
          {apiUp === false ? (
            <div className="error-box">
              API is down. In a rootscope/ terminal: ./scripts/local-services.sh start
            </div>
          ) : null}
          {error ? <div className="error-box">{error}</div> : null}
        </section>

        <aside className="panel">
          <p className="panel-title">Investigation workflow</p>
          <div className="steps">
            <div className="step-card">
              <div className="step-num">1</div>
              <div>
                <strong>Investigate</strong>
                <span>The agent reads code, logs, health, and contracts. It does not write files.</span>
              </div>
            </div>
            <div className="step-card">
              <div className="step-num">2</div>
              <div>
                <strong>Apply Fix</strong>
                <span>A temp sandbox patches the demo, runs tests, and stores the diff.</span>
              </div>
            </div>
            <div className="step-card">
              <div className="step-num">3</div>
              <div>
                <strong>Artifacts</strong>
                <span>Change Brief, Runbook, Postmortem. Decision Brief only if confidence is low.</span>
              </div>
            </div>
          </div>
        </aside>
      </div>

      <div className="section-head">
        <h2>Reproducible scenarios</h2>
        <p className="meta">{DEMOS.length} reproducible fixtures</p>
      </div>
      <div className="demos">
        {DEMOS.map((demo) => (
          <button
            key={demo.key}
            type="button"
            className="card"
            disabled={busy}
            onClick={() => void createIncident({ demo_key: demo.key })}
          >
            <span className="tag">{demo.tag}</span>
            <h3>{demo.title}</h3>
            <p>{demo.blurb}</p>
            <p className="hint">{demo.hint}</p>
          </button>
        ))}
      </div>

      <div className="section-head">
        <h2>Investigation history</h2>
        <p className="meta">
          {recent.length ? `${recent.length} ticket${recent.length === 1 ? "" : "s"}` : "None yet"}
        </p>
      </div>
      {recent.length ? (
        <div className="recent">
          {recent.map((incident) => (
            <a
              key={incident.id}
              className="card recent-card"
              href={`/incidents/${incident.id}`}
            >
              <div className="row">
                <strong>
                  {incident.id}
                  {incident.demo_key ? ` · ${incident.demo_key}` : ""}
                </strong>
                <span className={statusClass(incident.status)}>{incident.status}</span>
              </div>
              <p>{incident.title}</p>
              <p className="hint">{when(incident.created_at)}</p>
            </a>
          ))}
        </div>
      ) : (
        <p className="meta">No tickets yet. Create one or pick a demo above.</p>
      )}
    </>
  );
}
