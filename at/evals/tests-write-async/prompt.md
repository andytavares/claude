---
name: tests-write-async
max_turns: 30
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

/at:tests write a unit test for src/debounce.ts in src/debounce.test.ts
