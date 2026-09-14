# Runta Product Trial

This workspace contains the three projects I used to evaluate Runta from a developer's point of view. I started with a small controlled coding task, moved to a multi-service comparison, and finished with a deployed AI incident-investigation application.

The goal was not to touch every feature once. I wanted to see whether Runta could support repeatable agent work: prepare an environment, branch it from a checkpoint, run code safely, observe model/tool traffic, expose a service, and recover the same state later.

## Projects

### 1. Repo Doctor

A deliberately small Python repository with one known bug. I used it to establish a repeatable baseline and compare agent runs from the same prepared environment.

Runta features exercised: runtime creation, checkpoint/restore, pause/resume, SSH, SDK/CLI interoperability, egress controls, Token X-Ray/WatchFox, and early custom-image testing.

See `repo-doctor/ARCHITECTURE.md`.

### 2. Microservice Agent Lab

Two FastAPI services (`inventory` and `orders`) connected through a published response contract. I used one checkpoint as the starting point for a repo-wide agent and a pair of service-scoped agents, then validated both with the same independent tests.

Runta features exercised: checkpoints for A/B reproducibility, secrets, egress, Token X-Ray, service isolation, pause/resume, and runtime-to-runtime comparison.

See `microservice-agent-lab/ARCHITECTURE.md`.

### 3. RootScope

A complete AI incident-investigation application with a Next.js UI, FastAPI backend, tool-using agent, two demo services, reproducible incident scenarios, sandboxed fixes, validation, and operational artifacts.

Runta features exercised: public ingress, internal-only services, secret injection, explicit model/provider configuration, Token X-Ray, token-saving policies, checkpoint/restore, egress, lifecycle behavior, and custom Runtime Image attempts.

See `rootscope/docs/ARCHITECTURE.md` and `rootscope/docs/RUNTA.md`.

## Workspace layout

```text
runta-product-trial/
├── repo-doctor/                  controlled single-repo experiment
├── microservice-agent-lab/       multi-service A/B experiment
├── rootscope/                    final deployed product
├── image-test/                   custom Runtime Image Dockerfile experiments
├── notes/                        chronological observations and experiment notes
├── results/                      raw test, diff, API, and Token X-Ray evidence
└── submission/                   final external-facing trial feedback
```

## Evidence and writing

`notes/trial-log.md` is the chronological working log. It separates observations from hypotheses and does not treat local setup mistakes as Runta product issues.

`results/` contains the raw outputs used to support the conclusions in the final feedback: test results, diffs, Token X-Ray summaries, image-build records, suspend/wake checks, and RootScope runtime records.

`submission/FINAL_FEEDBACK.md` is the concise version intended to send with the project.

## Main takeaways

The strongest parts of Runta in this trial were reproducible runtime state, checkpoint-based branching, secrets, egress controls, SSH/SDK/CLI interoperability, and Token X-Ray once the provider path was configured correctly.

The biggest friction came from hidden state: capture settings after restore, model/provider compatibility, custom image build progress, and suspend/wake behavior were not always obvious from the surface state. Those findings are documented with the exact evidence retained under `results/`.
