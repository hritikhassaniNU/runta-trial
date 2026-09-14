# Future Scope

RootScope v1 stops at incident investigation, sandboxed remediation, and operational artifacts. The next direction I would explore is repository intelligence: understanding a codebase before an incident happens and connecting changes to likely downstream impact.

## Repository intake

A future version could accept a public GitHub repository URL and create a read-only analysis workspace. It would identify languages, packages, services, API contracts, Docker/Compose topology, tests, environment configuration, and CI workflows.

The default scan should avoid executing repository code. A separate Deep Scan could install dependencies and run tests inside a disposable Runta runtime.

## Dependency graph

RootScope could build both service-level and file/module-level dependency graphs. That would support questions such as:

- Which services depend on Inventory?
- What consumes this response schema?
- If a field changes, which files and tests are at risk?
- Which CI workflows exercise the affected path?

## Change-impact analysis

Given a file, diff, or commit, RootScope could estimate:

- directly affected files
- downstream modules and services
- API or contract compatibility risks
- tests likely to require updates
- CI workflows likely to be affected
- probable production impact

The product should distinguish deterministic evidence from model inference rather than presenting every conclusion with the same confidence.

## Repository health

A useful scan would combine several methods:

- syntax/compiler checks
- linters and type checking
- unit and integration tests
- dependency and manifest inspection
- static/security rules
- model-assisted cross-file and cross-service reasoning

Each finding should include evidence, severity, confidence, affected components, and a proposed next step.

## CI/CD intelligence

For supported public repositories, RootScope could read recent workflow/check status and connect failed jobs to relevant source changes, tests, and dependency paths. A failed integration test could then become a RootScope incident with the commit and failing check already attached.

This keeps untrusted execution away from the main RootScope application runtime while still giving the agent a realistic environment for deeper verification.
