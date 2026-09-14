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

---

# 1. Repo Doctor

[Project README](repo-doctor/README.md)

Repo Doctor is a deliberately small Python repository with one intentional bug and a pytest suite that makes the failure obvious. I used it to establish the trial methodology before introducing larger systems.

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
- custom Runtime Image behavior
- auto-suspend and wake behavior

The simplicity of this project made it easier to separate application mistakes, agent behavior, and platform behavior.

---

# 2. Microservice Agent Lab

[Project README](microservice-agent-lab/README.md) · [Experiment write-up](microservice-agent-lab/EXPERIMENT.md)

The second project introduces a real dependency boundary between two FastAPI services:

```text
Inventory Service :8001
        │
        │ inventory contract
        ▼
Orders Service :8002
```

The key test was a contract change from `available` to `available_quantity`. I prepared one baseline environment, checkpointed it, and compared a repo-wide agent with two service-scoped agents while keeping the starting state and validation identical.

Both approaches ultimately passed the same independent unit/contract and integration validation. The experiment exposed a real tradeoff: broader context reduced repeated exploration, while service scoping gave a clearer ownership boundary and smaller blast radius.

---

# 3. RootScope

[Project README](rootscope/README.md) · [Architecture and Runta deployment](rootscope/docs/Architecture.md) · [Future scope](rootscope/docs/Future_Scope.md)

**RootScope is an AI incident investigator for software systems.** It is the final and most product-shaped workload in the trial.

A user creates an incident or selects a reproducible demo scenario. RootScope investigates the system using constrained tools, collects evidence, returns a structured diagnosis, proposes a fix, validates that fix in a sandbox, and can generate operational follow-up artifacts.

```text
User browser
    │
    ▼
Runta HTTPS ingress :3000
    │
    ▼
Next.js UI
    │  API + SSE proxy
    ▼
FastAPI backend :8000
    │
    ▼
RootScope agent
    ├── files / repo search
    ├── logs
    ├── service checks
    ├── tests
    └── git diff
    │
    ├── Inventory :8001
    └── Orders :8002

Model traffic → Runta secret + egress policy → OpenAI Responses API
```

Only the Next.js frontend is published. FastAPI, Inventory, and Orders remain internal to the runtime.

RootScope includes three reproducible incidents:

1. **Contract regression** — Inventory returns `available_quantity` while Orders still expects `available`.
2. **Configuration failure** — Orders points to the wrong Inventory endpoint.
3. **Noisy logs** — large repetitive logs hide the useful failure signal.

The final Python suite for the application-level components passed **45 tests** during the trial, and the frontend production build completed successfully after the dependency update.

---

# Where Runta fit

| Layer | Responsibility in this repository |
| --- | --- |
| **Application layer** | Repo Doctor logic, microservices, RootScope UI/API/agent |
| **Runta platform layer** | Runtimes, checkpoints, restore, ingress, secrets, egress, SSH/terminal, Token X-Ray |
| **External systems** | Package registries, browser clients, model provider APIs |
| **Evidence/output layer** | Test results, diffs, token analysis, runtime observations, product feedback |

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
| Python SDK | Runtime lifecycle interoperability tested |
| SSH | Direct and native SSH config tested |
| Secrets | Model API credentials injected without committing secret values |
| Egress | Allowlist and denylist behavior tested |
| Ingress | RootScope frontend published through HTTPS |
| Token X-Ray | Real tool/model traffic inspected |
| WatchFox | Repeated calls and large outputs observed |
| Token-saving policies | Controlled experiments performed |
| Runtime Images | CLI/UI/API build paths tested, including failure behavior |
| Docker in runtime | Nested Docker build and CA-trust behavior tested |

---

# Main findings

The detailed discussion is in the [final feedback PDF](docs/Runta_Product_Trial_Feedback_Hritik_Hassani.pdf).

### What worked well

- checkpointing made controlled A/B experiments straightforward
- runtime filesystem and dependency state persisted reliably in the cases I tested
- pause/resume preserved ongoing work
- egress allowlist/denylist behavior was easy to verify
- CLI, SDK, REST API, and SSH could operate against the same runtime lifecycle
- secret injection kept application credentials out of source control
- Token X-Ray became useful once the model/provider path was explicitly configured
- public ingress was enough to deploy RootScope as a browser-accessible product

### Friction I would investigate first

**Custom Runtime Images.** I saw both staging failures after backend retries and later builds that remained `pending` at `attempt: 0`. Because the same Dockerfile built locally and inside a Runta runtime after handling the child-container CA trust, I would first investigate queueing, worker assignment, and build-context staging rather than assume a hypervisor problem.

**Suspend / wake behavior.** Fresh auto-suspend worked, but the wake activities I tested did not behave as expected. I would first trace wake-event delivery, desired-state reconciliation, and scheduler/runtime-manager transitions before looking lower in the virtualization stack.

**Configuration visibility.** Provider/model compatibility, Token X-Ray policy after restore, image-build state, and CLI/API/docs drift were all easier to diagnose once I inspected effective state directly. Earlier validation and clearer state visibility would improve the developer experience.

---

# Repository structure

```text
runta-trial/
├── README.md
├── ARCHITECTURE_OVERVIEW.md
├── docs/
│   ├── runta-trial-architecture-overview.png
│   └── Runta_Product_Trial_Feedback_Hritik_Hassani.pdf
├── repo-doctor/
├── microservice-agent-lab/
│   └── EXPERIMENT.md
└── rootscope/
    ├── apps/
    ├── agent/
    ├── demo-system/
    ├── deploy/
    ├── scripts/
    └── docs/
        ├── Architecture.md
        └── Future_Scope.md
```

---

# Running the projects

## Repo Doctor

```bash
cd repo-doctor
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -v
```

The baseline intentionally fails three tests because the repository contains the bug used for the experiment.

## Microservice Agent Lab

```bash
cd microservice-agent-lab
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -v
```

For the integration tests, start both services first (or use Docker Compose), then run `integration_tests`.

## RootScope

```bash
cd rootscope
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
# Add OPENAI_API_KEY locally. Do not commit it.
```

The application README and [architecture/deployment notes](rootscope/docs/Architecture.md) describe the runtime topology and Runta deployment configuration.

---

# Evidence and feedback

The public repository keeps the polished conclusions separate from private chronological working notes.

- [`microservice-agent-lab/EXPERIMENT.md`](microservice-agent-lab/EXPERIMENT.md) — controlled repo-wide vs service-scoped agent comparison
- [`docs/Runta_Product_Trial_Feedback_Hritik_Hassani.pdf`](docs/Runta_Product_Trial_Feedback_Hritik_Hassani.pdf) — final candid written product feedback

Additional raw command logs and temporary debugging artifacts were retained privately rather than published with the source repository.

---

# Security and reproducibility

No live API keys, Runta tokens, SSH private keys, or account credentials are intentionally included in this repository. Deployment examples use placeholders such as:

```text
REPLACE_WITH_RUNTA_SECRET_ID
```

The repository documents the workflow without exposing the account-specific secret value.

---

# Final trial feedback

**[Read the final feedback PDF](docs/Runta_Product_Trial_Feedback_Hritik_Hassani.pdf)**

---

## Author

**Hritik Hassani**
