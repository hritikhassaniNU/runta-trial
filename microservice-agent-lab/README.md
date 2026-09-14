# Microservice Agent Lab Architecture

## System under test

```text
Client / integration test
          │
          ▼
     orders :8002
          │
          │ HTTP
          ▼
   inventory :8001
          │
          ▼
contracts/inventory-contract.json
```

`inventory` owns stock availability. `orders` calls it over HTTP and consumes the published response contract. The coupling is intentional: changing the inventory field from `available` to `available_quantity` breaks the consumer unless the change is coordinated.

The test harness checks the system at three levels:

```text
service unit tests
      +
contract validation
      +
end-to-end order tests
```

## Runta A/B design

```text
Prepared baseline runtime
  repo + dependencies + green tests
              │
              ▼
checkpoint: microservices-pre-agent
              │
       ┌──────┴──────┐
       ▼             ▼
Global agent     Scoped agents
whole repo       inventory first
                 orders second
       │             │
       └──────┬──────┘
              ▼
     independent validation
     8 unit/contract tests
     4 integration tests
     git diff + X-Ray data
```

The global agent could inspect and update both services in one pass. In the scoped run, the inventory agent was told to modify only the producer and shared contract; the orders agent then read that contract and migrated the consumer.

## Why Runta mattered

The experiment depends on the two approaches having the same starting state. Runta's checkpoint was the fork point, so I did not need to rebuild the environment by hand for each run.

Runta also supplied:

- isolated runtimes for each strategy
- secret injection for the model API key
- egress policy around external model traffic
- Token X-Ray / WatchFox for tool-call and token comparison
- pause/resume so completed runs could be retained for inspection

## Result shape

Both approaches passed the same independent validation. The scoped path touched fewer unrelated files but required two agent sessions and more captured tool/model traffic. The global path was more token-efficient in the captured comparison but made a broader diff.

The experiment therefore measured a real tradeoff rather than only whether the rename could be completed.
