import type { DemoCatalog, IncidentDetail } from "../../lib/types";
import { IncidentWorkspace } from "./IncidentWorkspace";

async function loadJson(path: string) {
  const upstream = process.env.API_UPSTREAM || "http://127.0.0.1:8000";
  const response = await fetch(`${upstream}${path}`, { cache: "no-store" });
  if (!response.ok) {
    return null;
  }
  return response.json();
}

export default async function IncidentPage({
  params,
}: {
  params: { id: string };
}) {
  const [incident, catalog] = (await Promise.all([
    loadJson(`/api/incidents/${params.id}`),
    loadJson("/api/demos"),
  ])) as [IncidentDetail | null, DemoCatalog | null];

  if (!incident) {
    return (
      <div className="page-head">
        <h1>Incident not found</h1>
        <p className="crumb">
          <a href="/">← Dashboard</a>
        </p>
      </div>
    );
  }

  return (
    <>
      <p className="crumb">
        <a href="/">Dashboard</a>
        <span> / {incident.id}</span>
      </p>
      <div className="page-head">
        <p className="kicker">
          {incident.source === "demo" ? `Demo · ${incident.demo_key}` : "Freeform ticket"}
        </p>
        <h1>{incident.title}</h1>
        <p className="lede">{incident.description}</p>
      </div>
      <IncidentWorkspace initial={incident} catalog={catalog} />
    </>
  );
}
