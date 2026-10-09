---
name: google-review
description: Run a Google engineering-standard code review on the current diff. Invoked as /at:google-review [base-ref]. Reviews design, functionality, complexity, tests, naming, comments, style, and documentation. Returns a structured verdict with file:line citations. Available globally in all projects.
---

# Google Code Review

Spawns the `at:google-code-reviewer` subagent to review the current change set.

## Usage

```
/at:google-review           # reviews git diff HEAD (all uncommitted changes)
/at:google-review main      # reviews everything on this branch vs main
/at:google-review HEAD~3    # reviews the last 3 commits
```

## What it checks

Based on Google's engineering practices (https://google.github.io/eng-practices/review/):

1. **Design** — overall structure, component interaction, architectural fit
2. **Functionality** — edge cases, concurrency, user-facing correctness
3. **Complexity** — over-engineering, single-responsibility, readability
4. **Tests** — behavioral coverage, regression value, test quality
5. **Naming** — clarity and precision of all identifiers
6. **Comments** — WHY not WHAT; no stale or redundant comments
7. **Style** — consistency with the existing codebase
8. **Documentation** — docs updated when user-facing behavior changes

## Verdict

Each review ends with **Approve** or **Request Changes**. Issues are tagged:
- `[MUST]` — blocks approval, includes `file:line` and a concrete fix
- `[NIT]` — optional polish, not blocking

## How to invoke

When the user runs `/at:google-review` with an optional base ref argument:

1. Pass the base ref (if provided) to the `at:google-code-reviewer` agent prompt.
2. Spawn the `at:google-code-reviewer` agent.
3. Show its output to the user, then ask which lettered fixes to apply (`A B C`, `all`, or `none`). Edit nothing until they answer.

Spawn the agent now using the args provided (if any) as the base ref.
