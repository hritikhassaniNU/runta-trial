export type InvestigationEvent = {
  incident_id: string;
  seq: number;
  label: string;
  state: string;
  detail?: string | null;
  created_at: string;
};

export type Evidence = {
  kind: string;
  path: string;
  excerpt: string;
};

export type Diagnosis = {
  incident_id: string;
  root_cause: string;
  confidence: string;
  evidence: Evidence[];
  affected_services: string[];
  affected_files: string[];
  proposed_fix: { summary: string; files: string[] };
  test_result?: string | null;
  git_diff?: string | null;
};

export type DemoFixture = {
  key: string;
  title: string;
  description: string;
  expected_signal: string;
  apply_command: string;
  reset_command: string;
  needs_restart: boolean;
};

export type DemoCatalog = {
  demos: DemoFixture[];
  active?: string | null;
};

export type Artifact = {
  incident_id: string;
  kind: "change_brief" | "runbook" | "postmortem" | "decision_brief";
  body: Record<string, unknown>;
  created_at: string;
};

export type IncidentDetail = {
  id: string;
  title: string;
  description: string;
  source: string;
  demo_key?: string | null;
  status: string;
  created_at: string;
  events: InvestigationEvent[];
  diagnosis?: Diagnosis | null;
  artifacts?: Artifact[];
};

export type IncidentSummary = {
  id: string;
  title: string;
  status: string;
  demo_key?: string | null;
  created_at: string;
};
