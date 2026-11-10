---
name: tests
description: Use before you write, change or review a test, and when asked to audit tests. Holds one rule list for tests. Write mode applies it to the test you write; audit mode applies it to an existing suite and writes a brief for /at:implement.
argument-hint: "[what you test] | audit [path]"
---
Input: $ARGUMENTS

If the first word of the input is `audit`, read and follow `${CLAUDE_SKILL_DIR}/audit.md`. The rest of the input is the path to audit. Otherwise use write mode below.

Read the glossary first: run the `glossary` skill. Then read the project's own test rules: `CLAUDE.md`, `CONTRIBUTING`, ADRs. A project rule wins over a rule here. Report each conflict with its rule ID.

## The rule list

Cite the rule ID when you make a choice in a PR, and on every audit finding.

- **T-TIER**: Put each check in the lowest tier that can prove it. Unit: one behavior, one process, no I/O. Integration: one boundary the code owns, through a private instance. E2E: one user journey per test, a step per behavior.
- **T-BEHAVIOR**: Test one behavior per test, through the public interface. No private methods, no internal call order.
- **T-CAN-FAIL**: A test fails when the behavior is wrong. Delete tests with no assertion, mock-echo tests, and tests that assert a constant, that a function exists, or only `toBeDefined()`.
- **T-STATE**: Assert output or state, not calls. Assert a call only when the call is the behavior, such as a request to a third party.
- **T-NO-SNAPSHOT-ONLY**: A large snapshot is never the only assertion.
- **T-REACHABLE**: Each case is an input that a caller or a boundary can send. Check types, boundary validation and callers (`git grep -n -w`). Do not test an unreachable branch.
- **T-NO-DUPLICATE**: Two tests that fail for the same defect become one test or one parametrized test.
- **T-ALONE**: Each test passes alone and in any order. Every run shuffles and prints the seed.
- **T-CLEAN-SLATE**: Each test makes its own data, temp dir, DB and mock state. Restore mocks, timers, env and globals after each test. No mutable module-level state.
- **T-BOUNDARY**: Fake every boundary. No real host in any tier: unit runs block all sockets; integration and E2E runs allow only localhost. Use real code for everything inside the process. Unit tests never touch a DB; integration tests use a private DB that each test creates and drops.
- **T-SAME-ENV**: Tests run in one sealed environment, the same on a laptop and in CI: pinned timezone, locale and runtime version, a scrubbed env and HOME, one test command for both.
- **T-NO-RETRY**: No retries in any runner, config or CI step. The first run is the result. Fix a flaky test at its cause, or move its check down a tier, in the same PR. Never skip it.
- **T-WAIT-CONDITION**: Wait on the condition you assert, never on a fixed delay. No `sleep`, `waitForTimeout` or `setTimeout` in tests. Use retrying assertions: Playwright `expect(locator)`, Testing Library `findBy*`, `expect.poll`.
- **T-READY-TARGET**: Act only on a target that is ready. Wait for the element you act on. Before keyboard input, assert focus with `toBeFocused()`.
- **T-AWAIT-ALL**: Await every promise a test starts. Lint tests with `@typescript-eslint/no-floating-promises`.
- **T-CONTROL-TIME**: Fake timers in unit tests, `page.clock` in E2E. One generous hang bound per runner; no per-test tuned timeouts.
- **T-APP-SIGNAL**: If the app gives no signal that it is ready, add one to the app: a role, a state attribute, an event. A test never guesses.
- **T-TEARDOWN**: Cleanup never decides a result. Per-test cleanup does not throw. Bulk cleanup runs in a global teardown.
- **T-READABLE**: The name says the behavior and the expected result. Arrange, act, assert. No `if` or loops in a test. DAMP over DRY. Testing Library query order: role, label, text, test id last. Use `user-event`, not `fireEvent`.

## Write mode

Do these steps before you write or change a test. `${CLAUDE_SKILL_DIR}/references/frameworks.md` has the runner commands and config for each step.

1. Pick the tier with T-TIER.
2. Write the test. Run it against the current code. Show that it fails on its assertion, not on an error.
3. Check the test against every rule in the list.
4. Make it pass.

Sources: Software Engineering at Google ch. 11-14, The Practical Test Pyramid, xUnit Patterns (Erratic Test), testsmells.org, Testing Library docs, Playwright best practices.
