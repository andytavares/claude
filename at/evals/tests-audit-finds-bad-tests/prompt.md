---
name: tests-audit-finds-bad-tests
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

/at:tests audit tests

The suite has 4 tests in tests/test_price.py. There is no network. If pytest is not installed, record that and continue by reading the code.
No one can answer questions in this session: do not ask with AskUserQuestion. List the findings and stop before you ask which actions to apply.
In your final reply, print one line per test in the audit's finding format, including the test name. Tests you keep get the action keep.
