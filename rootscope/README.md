# RootScope

RootScope is an AI incident investigator for software systems. It combines a user-facing web application with a tool-using investigation agent that can inspect code, logs, service health, tests, and git state before proposing a diagnosis.

The v1 project was built as the final workload in my Runta product trial. The application is real rather than a static demo: it has two communicating services, three reproducible incident scenarios, streamed investigation activity, sandboxed remediation, test validation, and operational artifacts.

## What it does

A user creates an incident from a description or chooses a demo scenario. RootScope investigates without modifying the working tree, returns a structured diagnosis with evidence, and then allows the user to apply a fix in a temporary sandbox.

The current demo scenarios are:

- contract regression: Inventory returns `available_quantity` while Orders still expects `available`
- configuration failure: Orders points to the wrong Inventory endpoint
- noisy logs: thousands of repetitive log lines hide one useful error

After a diagnosis, RootScope can generate a Change Brief, Runbook, Postmortem, and a Decision Brief when confidence is low.
