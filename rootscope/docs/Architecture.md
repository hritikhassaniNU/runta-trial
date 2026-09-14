# RootScope Architecture

## Product boundary

RootScope has four runtime processes and one external model endpoint.

```text
                         PUBLIC
                           │
                           ▼
                  Runta HTTPS ingress
                           │
                     port 3000 only
                           │
                           ▼
                 ┌─────────────────┐
                 │ Next.js web app │
                 │      :3000      │
                 └────────┬────────┘
                          │
                server-side API/SSE proxy
                          │
                          ▼
                 ┌─────────────────┐
                 │ FastAPI backend │
                 │      :8000      │
                 └────────┬────────┘
                          │
                    RootScope agent
                          │
          ┌───────────────┼────────────────┐
          ▼               ▼                ▼
      workspace          logs          service checks
   files / search     test output       HTTP health
          │               │                │
          └───────────────┼────────────────┘
                          │
                 sandboxed remediation
                          │
                tests + scoped git diff

          Inventory :8001 ─────► Orders :8002
                 internal demo services
```

The backend stores incidents, events, diagnoses, and generated artifacts in SQLite. Investigation and modification are separate actions: the first pass gathers evidence and produces a diagnosis; Apply Fix works on a temporary copy of the demo system rather than the live workspace.

## Agent execution

The investigation agent uses the OpenAI Responses API with a small set of constrained tools:

- `read_file` — workspace-only file reads
- `search_repo` — capped repository search
- `read_logs` — bounded service-log reads/searches
- `run_command` — allowlisted diagnostic commands
- `check_service` — service health/URL checks
- `run_tests` — named pytest targets
- `git_diff` — workspace diff inspection

Tool results are returned to the model, which makes the workload suitable for Token X-Ray and WatchFox. The noisy-log scenario intentionally contains repeated data, but the agent is expected to search for the useful line rather than dump the whole file.

## Runta integration

```text
RootScope runtime
   │
   ├── secret configuration
   │      └── OPENAI_API_KEY
   │
   ├── egress policy
   │      └── api.openai.com/v1/*
   │
   ├── Token X-Ray
   │      ├── tool I/O capture
   │      ├── JSON-array optimization
   │      ├── log optimization
   │      ├── search-result optimization
   │      └── git-diff optimization
   │
   ├── ingress
   │      └── :3000 / HTTPS
   │
   └── checkpoint / restore
          └── reproducible application state
```

Only the frontend is exposed through Runta ingress. Requests from the browser reach FastAPI through the Next.js proxy; Inventory and Orders are never independently published.

The final deployment used explicit provider/model configuration because the trial showed that relying on the default provider/model path could produce an incompatible combination. The REST create payload was used when model selection and Token X-Ray policy needed to be explicit.

## Demo-system architecture

```text
POST /orders
    │
    ▼
Orders :8002
    │ GET /inventory/{sku}
    ▼
Inventory :8001
    │
    ▼
contracts/inventory-contract.json
```

This small dependency is enough to produce realistic failure modes:

- a schema change can break a downstream consumer
- a bad service URL can break connectivity while both processes remain healthy
- noisy logs can hide a meaningful error without changing application code

## Checkpoint strategy

A checkpoint is most useful after dependencies and application state are prepared. Restoring that point gives a clean branch for another investigation or fix experiment without rebuilding the environment.

During the trial, I found that runtime policy should be verified after restore rather than assumed. For RootScope, capture, token-saving settings, ingress, and secret configuration were checked explicitly on the restored runtime.

## Custom images

RootScope includes Dockerfiles, but the application does not depend on a successful managed custom image build. Custom Runtime Images were evaluated as a separate Runta feature so that an image-builder failure would not block the product deployment.



# Running RootScope on Runta

RootScope is designed so that the browser-facing application is public while the API and demo services stay inside one runtime.

## Ports

| Port | Process | Exposure |
| 3000 | Next.js | public HTTPS ingress |
| 8000 | FastAPI | internal |
| 8001 | Inventory | internal |
| 8002 | Orders | internal |

The working public URL format observed during the trial was:

```text
https://3000-<runtime-id>.runta.dev
```

Next.js proxies API and SSE traffic to FastAPI, so the browser never needs direct access to ports 8000, 8001, or 8002.

## Runtime configuration

The example payload in `deploy/create-runtime.json` uses:

- 4 vCPU / 8 GiB memory
- `codex` runtime image
- `openai_responses`
- explicit `gpt-4.1` model selection
- Token X-Ray tool-I/O capture
- all four token-saving policies
- HTTPS ingress on port 3000
- OpenAI credential injection through a Runta secret

