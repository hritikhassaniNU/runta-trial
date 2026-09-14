# Repo Doctor Architecture

## Application

```text
calculator.py
    │
    ▼
pytest suite
    │
    ├── divide positive values
    ├── divide different values
    └── divide by zero
```

The initial implementation intentionally multiplies instead of dividing. The expected baseline is three failing tests.

## Runta workflow

```text
Local repository
      │
      ▼
repo-doctor-base runtime
  Python + pytest + coding agent
      │
      ▼
checkpoint: repo-doctor-pre-fix
      │
   ┌──┴──┐
   ▼     ▼
Agent A Agent B
   │     │
   └──┬──┘
      ▼
Independent validation
  pytest + git diff
```

The checkpoint made the comparison useful: both agents started from the same filesystem, dependencies, repository commit, and prepared environment.

## Runta features exercised

- runtime create / inspect / exec
- checkpoint and restore
- pause / resume persistence
- SSH access and native SSH config
- Python SDK lifecycle operations
- allowlist and denylist egress rules
- secret injection
- Token X-Ray / WatchFox
- custom Runtime Image build attempts

## What this experiment established

Repo Doctor was less about the calculator fix and more about the evaluation method. I learned to treat the agent's own test report as advisory and run validation from outside the agent flow. That same method was used for the microservice and RootScope experiments.
