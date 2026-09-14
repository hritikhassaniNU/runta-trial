# Architecture Overview

The trial progressed through three increasingly realistic workloads. Each project reused the same basic pattern: prepare a known state, run an agent inside an isolated runtime, validate the result independently, and record what Runta made easy or difficult.

## Repo Doctor

```text
Local buggy repo
      │
      ▼
Prepared Runta runtime
  Python + pytest + agent auth
      │
      ▼
Checkpoint: pre-fix state
      │
   ┌──┴──┐
   ▼     ▼
Run A   Run B
   │     │
   └──┬──┘
      ▼
Independent pytest + git diff
      │
      ▼
Token X-Ray / WatchFox comparison
```

Purpose: prove that two runs really start from the same environment and establish the independent-validation method used later.

## Microservice Agent Lab

```text
                 checkpoint: microservices-pre-agent
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
             repo-wide agent      service-scoped agents
                    │             inventory → orders
                    │                   │
                    └─────────┬─────────┘
                              ▼
               same tests / same contract
                              │
                              ▼
                   diff + token comparison

inventory :8001  ───────────────►  orders :8002
        publishes contract            consumes contract
```

Purpose: compare broad repository context with tighter service ownership while keeping the starting state and validation identical.

## RootScope

```text
Internet
   │
   ▼
Runta HTTPS ingress
   │  port 3000 only
   ▼
Next.js UI :3000
   │
   │ server-side API/SSE proxy
   ▼
FastAPI :8000
   │
   ▼
RootScope investigation agent
   │
   ├── read/search files
   ├── read logs
   ├── check service health
   ├── run allowlisted commands/tests
   └── inspect git diff
   │
   ├────────► inventory :8001
   └────────► orders :8002

Agent model traffic
   │
   ▼
Runta secret injection + egress policy
   │
   ▼
OpenAI Responses API

Runta observes tool/model traffic with Token X-Ray / WatchFox.
```

Purpose: test Runta as the execution and observability layer behind a real AI application rather than only as a shell environment.

## Why the projects are separate

Repo Doctor is intentionally tiny so runtime behavior is easy to isolate. The microservice lab adds service boundaries and a shared contract. RootScope adds a real UI, model traffic, tool execution, public ingress, state, and a user-facing workflow. Keeping the projects separate made it easier to tell whether a result came from the application or from the platform.
