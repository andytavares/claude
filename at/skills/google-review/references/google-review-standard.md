# Google Code Review Standard — Reference

Source: https://google.github.io/eng-practices/review/

## Core Principle

Approve a CL once it **definitively improves overall code health**, even if imperfect. Do not block for polish that could be addressed later.

## The Eight Dimensions

| # | Dimension | What to check |
|---|-----------|---------------|
| 1 | **Design** | Is the overall approach sound? Does this change belong here? Do components interact logically? |
| 2 | **Functionality** | Does it do what the author intends? Edge cases, concurrency, user-facing behavior. |
| 3 | **Complexity** | Is it as simple as it can be? No over-engineering or speculation about future needs. |
| 4 | **Tests** | Appropriate unit/integration/e2e tests. Tests must actually catch regressions. |
| 5 | **Naming** | All identifiers communicate purpose clearly and precisely. |
| 6 | **Comments** | Explain WHY. Don't restate WHAT. No stale comments. |
| 7 | **Style** | Matches established style guides and existing codebase patterns. |
| 8 | **Documentation** | Updated when user-facing behavior, build steps, or APIs change. |

## Severity Tags

- `[MUST]` — Required before approval. Cite `file:line` with a concrete fix.
- `[NIT]` — Optional. Reviewer preference. Never blocks approval.

## Principles

- Technical facts and data override opinions and personal preferences.
- Style disputes defer to the style guide; if no guide, match the existing codebase.
- Avoid perfectionism: "good enough that it improves the system" is the bar, not "perfect."
- Resolve disagreements through documented guidelines, not prolonged debate.

## On Complexity

> "If a reviewer can't understand it in a reasonable amount of time, that's a problem."

Flag:
- Functions doing more than one thing
- Unnecessary generality / future-proofing that isn't needed today
- Logic that would surprise a competent reader

## On Tests

Tests are code too. Require:
- Tests that will actually FAIL when the production code is broken
- No tests so complex they need their own tests
- Coverage of the specific behavior changed, not just coverage for its own sake

## CL Description Quality

A good commit/CL description:
- First line: imperative mood, specific summary ("Delete the FizzBuzz RPC" not "Fix bug")
- Body: explains WHY, not just WHAT
- Links to relevant issues, design docs, benchmarks
- Accurately reflects the final state of the change
