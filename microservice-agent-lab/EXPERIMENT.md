# Microservice Agent Experiment

## Aim

How does one repo-wide coding agent compare with two service-scoped agents when a producer API contract changes?

The goal was not simply to see whether an agent could rename a field. I wanted to compare coordination, blast radius, final diff, and captured tool/model traffic from the same starting state.

## Baseline

The repository contains:

- Inventory service on 8001
- Orders service on 8002
- a published inventory response contract
- 8 unit/contract tests
- 4 end-to-end integration tests

Before running the experiment I manually introduced the breaking rename. The harness caught it at the service, contract, and integration layers, so a passing result could not be explained by a weak test setup.

## Runta setup

I prepared one baseline runtime and checkpointed it as `microservices-pre-agent`. Every comparison run came from that point.

The final X-Ray comparison used the explicit API-key provider path so captured calls were meaningful. Both completed runtimes were kept paused for later inspection.

## Run A: repo-wide agent

The agent could see both services, the shared contract, and integration tests.

Task: rename `available` to `available_quantity`, keep the complete system working, update affected code/tests/contracts, and avoid unnecessary changes.

## Run B: service-scoped agents

The Inventory agent could work on the producer and shared contract but was told not to modify Orders. After that change, the system was intentionally in a broken midpoint. The Orders agent then read the published contract and migrated the consumer.

## Understanding 

The repo-wide agent was more token-efficient because it explored the system once and completed the migration in a single pass.

The scoped approach gave a clearer service boundary and a useful intermediate state: after Inventory changed, the consumer was visibly broken until Orders was migrated. That makes the coordination point explicit and may be preferable when service ownership matters more than duplicated exploration.

I would not choose the scoped design to save tokens. I would choose it when I want the contract to be the handoff point and I care about limiting which service an agent can modify.

## Runta's role

The important platform feature here was the checkpoint. Without an identical starting state, the comparison would be much less convincing. Secrets, egress, Token X-Ray, pause/resume, and independent `runta exec` validation completed the experiment around that checkpoint.
