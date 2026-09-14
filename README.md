# Runta Product Trial

This repository contains the work from my Runta product trial. I used three projects of increasing complexity to evaluate Runta as an execution and infrastructure layer for AI-assisted software engineering and agent workflows.

I started with a deliberately small coding task where runtime behavior was easy to isolate, moved to a two-service system where agent changes could affect downstream dependencies, and finished with **RootScope**, a deployed AI incident-investigation application with a real UI, backend, tool-using agent, public ingress, secrets, checkpoints, and Token X-Ray observability.

The goal was not to touch every feature once. I wanted to answer a more practical question:

> **Can Runta provide a repeatable, observable, and controllable environment for real agent-driven engineering work?**

## Architecture overview

![Runta trial architecture overview](docs/runta-trial-architecture-overview.png)

Across all three projects, the application code stayed in the application layer. **Runta surrounded it as the runtime/infrastructure layer**: provisioning environments, checkpointing state, exposing services, injecting secrets, controlling egress, providing terminal/SSH access, and observing model/tool traffic.

For a text version of the architecture, see [ARCHITECTURE_OVERVIEW.md](ARCHITECTURE_OVERVIEW.md).

---

## Projects at a glance

| Project | What I was testing | How Runta was used | Main output |
| --- | --- | --- | --- |
| **Repo Doctor** | Reproducibility of agent runs from an identical starting state | Runtimes, checkpoint/restore, pause/resume, SSH, SDK/CLI/API, egress, Token X-Ray | Controlled A/B agent comparison with independent tests and diffs |
| **Microservice Agent Lab** | Whether agent changes remain safe across service boundaries | Checkpointed A/B environments, secrets, egress, Token X-Ray, lifecycle | Global-agent vs service-scoped-agent comparison across two communicating services |
| **RootScope** | Whether Runta can support a real AI product end to end | Public ingress, internal services, secrets, explicit model/provider config, Token X-Ray, token-saving policies, checkpoints, lifecycle | Deployed AI incident investigator with UI, agent tools, sandboxed fixes, tests, diffs, runbooks, and postmortems |

The projects are intentionally separate. Each one adds a new kind of complexity while keeping the previous experiment understandable.

---

# 1. Repo Doctor

[Project README](repo-doctor/README.md) · [Architecture](repo-doctor/ARCHITECTURE.md)

Repo Doctor is a very small Python repository with one intentional bug and a pytest suite that makes the failure obvious.

I used it to establish the trial methodology before introducing larger systems:

```text
Known failing repository
        ↓
Prepared Runta runtime
        ↓
Checkpoint known-good environment
        ↓
Restore identical runtimes
     ┌───────┴───────┐
     ↓               ↓
 Agent A           Agent B
     ↓               ↓
 pytest + git diff  pytest + git diff
     └───────┬───────┘
             ↓
      Compare behavior
```

### What I tested

- runtime creation and lifecycle
- filesystem and dependency persistence
- checkpoint and restore behavior
- identical A/B starting environments
- coding-agent execution inside the runtime
- independent validation with `pytest` and `git diff`
- SSH access
- Python SDK and CLI interoperability
- REST API usage
- egress allowlist/denylist behavior
- secret injection
- Token X-Ray / WatchFox
- token-saving policies
- early custom Runtime Image behavior
- auto-suspend and wake behavior

### Why this project mattered

The repository is intentionally simple. When there is only one known bug, it is much easier to tell whether a surprising result came from the application, the agent, or the platform.

That made Repo Doctor the foundation for the larger experiments.

---

# 2. Microservice Agent Lab

[Project README](microservice-agent-lab/README.md) · [Architecture](microservice-agent-lab/ARCHITECTURE.md)

The second project introduces a real dependency boundary.

It contains two FastAPI services:

```text
Inventory Service :8001
        │
        │ inventory contract
        ▼
Orders Service :8002
```

`inventory` owns stock availability. `orders` calls `inventory` over HTTP and depends on the published response contract.

The key test was a contract change such as:

```text
available
   ↓
available_quantity
```

A local change to Inventory can therefore break Orders unless the downstream dependency is understood and updated correctly.

### Experiment

I prepared one baseline environment, checkpointed it, and used that checkpoint for two different approaches:

```text
                    Runta checkpoint
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
       Global repo agent      Service-scoped agents
              │              Inventory → Orders
              └───────────┬───────────┘
                          ▼
             Same validation suite
                          │
                          ▼
             Tests + contract + diff
```

The point was not simply to see whether an agent could change code. It was to compare **broad repository context** with **tighter service ownership** while keeping the initial state and validation identical.

### What I tested

- checkpoint-based experiment reproducibility
- cross-service dependency reasoning
- service-scoped vs repo-wide agent behavior
- unit, contract, and integration validation
- diff-based change inspection
- secrets and egress
- Token X-Ray on real agent/tool traffic
- lifecycle and state persistence

This project made the trial closer to how agent-driven changes behave in a real codebase, where one file or service can affect several downstream consumers.

---

# 3. RootScope

[Project README](rootscope/README.md) · [Architecture](rootscope/docs/ARCHITECTURE.md) · [Runta deployment notes](rootscope/docs/RUNTA.md)

**RootScope is an AI incident investigator for software systems.** It is the final and most product-shaped workload in the trial.

A user creates an incident or selects a reproducible demo scenario. RootScope investigates the system using tools, collects evidence, returns a structured diagnosis, proposes a fix, validates that fix in a sandbox, and can generate operational follow-up artifacts.

## Product flow

```text
User reports incident
        ↓
RootScope UI
        ↓
Investigation agent
        ↓
┌──────────────────────────────┐
│ Read/search source files     │
│ Inspect logs                 │
│ Check service health         │
│ Inspect contracts/config     │
│ Run allowlisted commands     │
│ Run tests                    │
│ Inspect git diff             │
└──────────────────────────────┘
        ↓
Diagnosis + evidence
        ↓
Proposed fix
        ↓
Apply in sandbox
        ↓
Tests + git diff
        ↓
Change Brief / Runbook / Postmortem
```

## Runtime architecture

```text
Internet
   │
   ▼
Runta HTTPS ingress
   │  public port 3000
   ▼
Next.js UI :3000
   │
   │ API + SSE proxy
   ▼
FastAPI :8000
   │
   ▼
RootScope agent
   │
   ├────────────► Inventory :8001
   ├────────────► Orders :8002
   │
   └── tools: files, logs, service checks, tests, git

Model traffic
   │
   ▼
Runta secret injection + egress policy
   │
   ▼
OpenAI Responses API

Runta Token X-Ray / WatchFox observes model and tool traffic.
```

Only the Next.js frontend is published. FastAPI, Inventory, and Orders remain internal to the runtime.

## Demo incidents

RootScope includes three reproducible incidents:

1. **Contract regression** — Inventory returns `available_quantity` while Orders still expects `available`.
2. **Configuration failure** — Orders points to the wrong Inventory endpoint.
3. **Noisy logs** — large repetitive logs hide the useful failure signal.

The noisy-log scenario was particularly useful for exercising Token X-Ray and large/repeated tool-output behavior in a realistic workflow.

## What I tested with RootScope

- a long-running application inside a Runta runtime
- public HTTPS ingress
- internal-only backend/service ports
- secret injection for model credentials
- outbound network policy
- explicit model/provider configuration
- Token X-Ray and WatchFox on real agent activity
- token-saving policies
- checkpoint and restore of a working application state
- pause/resume persistence
- runtime terminal access
- custom Runtime Image attempts
- application-level health and integration validation

RootScope was intentionally kept focused. Repository-wide GitHub intelligence, dependency graphs, CI/CD analysis, and change-impact scanning are documented as [future scope](rootscope/docs/FUTURE_SCOPE.md) rather than being added to an already complete v1.

---

# Where Runta fit

The easiest way to describe Runta's role across the trial is by layer:

| Layer | Responsibility in this repository |
| --- | --- |
| **Application layer** | Repo Doctor logic, microservices, RootScope UI/API/agent |
| **Runta platform layer** | Runtimes, checkpoints, restore, ingress, secrets, egress, SSH/terminal, Token X-Ray |
| **External systems** | Git repositories, package registries, browser clients, model provider APIs |
| **Evidence/output layer** | Test results, diffs, token analysis, runtime records, trial feedback |

Runta was not embedded in the application business logic. It provided the **execution and infrastructure boundary around the applications**.

---

# Runta feature coverage

| Area | Trial coverage |
| --- | --- |
| Runtime creation | Tested across multiple workloads |
| Checkpoints | Used for known-good snapshots and A/B experiments |
| Restore | Used to reproduce identical environments and recover application state |
| Pause / resume | Persistence verified across lifecycle transitions |
| Auto-suspend | Suspend behavior and wake paths tested |
| CLI | Used throughout runtime, image, SSH, secret, and lifecycle workflows |
| REST API | Used for explicit runtime/model configuration and deeper inspection |
| Python SDK | Runtime create/list/exec/pause/resume/delete interoperability tested |
| SSH | Direct and native SSH config tested |
| Secrets | Model API credentials injected without committing secret values |
| Egress | Allowlist and denylist behavior tested |
| Ingress | RootScope frontend published through HTTPS |
| Token X-Ray | Real tool/model traffic inspected |
| WatchFox | Repeated calls, repeated paths, and large outputs observed |
| Token-saving policies | Controlled experiments performed |
| Runtime Images | CLI/UI/API build paths tested, including failure behavior |
| Docker in runtime | Nested Docker build and CA-trust behavior tested |

---

# Main findings

The detailed discussion is in the [final feedback PDF](submission/Runta_Product_Trial_Feedback_Hritik_Hassani.pdf). A few themes stood out.

## What worked well

- Checkpointing made controlled A/B experiments straightforward.
- Runtime filesystem and dependency state persisted reliably in the cases I tested.
- Pause/resume worked well for preserving ongoing work.
- Egress allowlist/denylist behavior was easy to verify.
- CLI, SDK, REST API, and SSH could all operate against the same runtime lifecycle.
- Secret injection kept application credentials out of source control.
- Token X-Ray became useful once the model/provider path was explicitly configured.
- Public ingress was enough to deploy RootScope as an actual browser-accessible product.

## Friction I would investigate first

### Custom Runtime Image pipeline

I observed two distinct managed-image behaviors during the trial:

- builds that started and later ended in `cloud_build_staging_failed`
- later builds that stayed `pending` with `attempt: 0` and no attempt history

The same Docker image built successfully as `linux/amd64` locally, and also built successfully with Docker inside a Runta runtime after the child image trusted the Runta egress CA.

From the evidence available externally, I would investigate the managed path in this order:

```text
API request
   → queue
   → worker assignment
   → build-context staging
   → Docker build
   → image publication
```

I would not attribute the issue directly to the hypervisor without internal telemetry.

### Suspend / wake path

Fresh auto-suspend worked, but wake behavior was inconsistent in my observed tests across exec, terminal, and HTTP access.

My first debugging path would be control-plane state rather than immediately assuming a VM/hypervisor problem:

```text
wake event
   → event delivery
   → desired-state reconciliation
   → scheduler/runtime manager
   → VM/runtime wake
```

### Configuration consistency

A few workflows exposed cases where configuration was not obvious from the surface state, especially:

- provider/model compatibility
- Token X-Ray policy after restore
- Runtime Image build phase/progress
- API/CLI documentation drift

These are good candidates for earlier validation and clearer user-facing diagnostics.

---

# Repository structure

```text
runta-product-trial/
├── README.md
├── ARCHITECTURE_OVERVIEW.md
├── docs/
│   └── runta-trial-architecture-overview.png
│
├── repo-doctor/
│   ├── README.md
│   ├── ARCHITECTURE.md
│   └── tests/
│
├── microservice-agent-lab/
│   ├── README.md
│   ├── ARCHITECTURE.md
│   ├── services/
│   ├── contracts/
│   └── integration_tests/
│
├── rootscope/
│   ├── README.md
│   ├── apps/
│   │   ├── web/
│   │   └── api/
│   ├── agent/
│   ├── demo-system/
│   ├── deploy/
│   ├── scripts/
│   └── docs/
│       ├── ARCHITECTURE.md
│       ├── RUNTA.md
│       └── FUTURE_SCOPE.md
│
├── image-test/
├── notes/
├── results/
└── submission/
```

---

# Running the projects

Each project has its own README with setup instructions. The shortest starting points are below.

## Repo Doctor

```bash
cd repo-doctor
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -v
```

The repository intentionally contains a bug, so the baseline is expected to fail before an agent/fix is applied.

## Microservice Agent Lab

```bash
cd microservice-agent-lab
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -v
```

For the integration tests:

```bash
docker compose up -d --build
.venv/bin/python -m pytest integration_tests -v
docker compose down
```

## RootScope

```bash
cd rootscope
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
# Add OPENAI_API_KEY locally. Do not commit it.
.venv/bin/python -m pytest -q
```

Start the Python services:

```bash
./scripts/local-services.sh start
```

Then start the frontend:

```bash
cd apps/web
npm install
npm run dev
```

See [rootscope/docs/RUNTA.md](rootscope/docs/RUNTA.md) for the Runta-specific deployment workflow.

---

# Evidence

The repository keeps raw evidence separate from conclusions.

- [`notes/trial-log.md`](notes/trial-log.md) — chronological observations from the trial
- [`notes/microservice-agent-experiment.md`](notes/microservice-agent-experiment.md) — multi-service experiment notes
- [`notes/rootscope-log.md`](notes/rootscope-log.md) — RootScope-specific trial notes
- [`results/`](results/) — tests, diffs, runtime records, Token X-Ray output, image-build records, and other supporting artifacts
- [`submission/FINAL_FEEDBACK.md`](submission/FINAL_FEEDBACK.md) — concise written feedback
- [`submission/Runta_Product_Trial_Feedback_Hritik_Hassani.pdf`](submission/Runta_Product_Trial_Feedback_Hritik_Hassani.pdf) — formatted final report

I kept observations separate from hypotheses wherever possible. Local setup mistakes are not treated as product defects, and infrastructure-level hypotheses are labeled as such rather than presented as confirmed root causes.

---

# Security and reproducibility notes

No API keys, Runta tokens, SSH private keys, or live account credentials are included in this repository.

Runta deployment examples use placeholders such as:

```text
REPLACE_WITH_RUNTA_SECRET_ID
```

so the repository can document the workflow without exposing account-specific secrets.

---

# Future direction

The most natural extension of RootScope is repository intelligence: accepting a public repository, mapping services and file dependencies, analyzing CI/CD state, and estimating the downstream impact of a proposed change.

I intentionally left that out of v1 so the product remained focused and the Runta evaluation stayed measurable.

See [rootscope/docs/FUTURE_SCOPE.md](rootscope/docs/FUTURE_SCOPE.md).

---

# Final trial feedback

The final report covers both the positive results and the areas where I ran into friction, including the evidence behind each conclusion.

**[Read the final feedback PDF](submission/Runta_Product_Trial_Feedback_Hritik_Hassani.pdf)**

---

## Author

**Hritik Hassani**

This repository was created as part of a hands-on evaluation of Runta's developer experience and runtime infrastructure.
