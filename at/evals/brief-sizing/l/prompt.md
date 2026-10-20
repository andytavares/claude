---
max_turns: 30
timeout_seconds: 400
runs: 1
allowed_tools: [Read, Glob, Grep, Skill, Agent, Write]
---
/at:brief Pick a caching strategy for the orders, catalog and pricing services: they share a database and each has different staleness tolerance. Options include per-service in-memory, shared Redis, or HTTP caching at the gateway; decide which. Use the id caching for the brief file.
