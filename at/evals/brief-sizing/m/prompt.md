---
max_turns: 30
timeout_seconds: 400
runs: 1
allowed_tools: [Read, Glob, Grep, Skill, Agent, Write]
---
/at:brief Add a CSV export of orders: a new GET /orders.csv route in src/routes/orders.ts that uses a new src/export/csv.ts helper, with tests in test/csv.test.ts. Follow the existing JSON route in the same file; the approach is obvious. Use the id csv-export for the brief file.
