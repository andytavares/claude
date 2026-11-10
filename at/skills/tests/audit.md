# Audit mode

Apply the rule list in `${CLAUDE_SKILL_DIR}/SKILL.md` to an existing suite. Scope: the path after `audit`, or the whole repo. The audit proposes; the user picks; `/at:implement` changes the code in a PR. Do not change test or production code here.

## Safety

- Run in a worktree, never in the user's checkout.
- Read the runner config before the first run. Block the network first where the runner allows it (`references/frameworks.md`).
- Stop and ask the user before a run that needs credentials, a shared service or a shared DB.

## Steps

1. **Inventory.** Find each runner and its config, and the test commands in the README, the build files and the CI files. Read the project's test rules (CLAUDE.md, CONTRIBUTING, ADRs). Count tests per tier, and record the command that counts them.
2. **Baseline.** Run the whole suite once. Record the exit code, the time and the failures. A red baseline is a finding; continue the audit.
3. **Config check.** Find: retries in any config or CI step (T-NO-RETRY); shuffle off (T-ALONE); mock, env or global restore off (T-CLEAN-SLATE); network open in any tier (T-BOUNDARY); timezone, locale or runtime version not pinned, or CI runs a different command than local (T-SAME-ENV); per-test timeouts (T-CONTROL-TIME); skipped tests with no issue.
4. **Dynamic checks.** Use the commands in `references/frameworks.md`.
   - Run each spec that fails in the baseline alone. A spec that passes alone and fails in the suite is order-dependent (T-ALONE).
   - Run the unit tier with all sockets blocked. Run integration and E2E with only localhost allowed (T-BOUNDARY).
   - Read CI history through the CI capability in `rules/environment.md`. A commit with both a passed and a failed run of one test is a flaky test. `references/frameworks.md` ("CI history") has the GitHub Actions command. With no CI provider, write "not measured" and the reason.
     Each hit is a lead. Confirm in the job logs that the same test passed and failed.
5. **Pattern scan.** Run the commands in "Pattern list" below. Keep the hit list per file.
6. **Read.** Read every test file, not only the hits. Read each test with the production code it calls and that code's callers. Give each test one action from "Actions", with the rule ID. For more than about 40 test files, start one subagent per top-level test directory, at most 8. Give each subagent the rule list, its hit list and the finding format.
7. **Unreachable code.** For each branch that no caller or boundary can reach (T-REACHABLE), ask the user through the questions capability in `rules/environment.md`: "delete branch and test", "delete test only" or "keep". Deleting production code is destructive, so never decide alone.
8. **Mutation guard.** Where Stryker or mutmut runs on the project, run it on the modules whose tests the findings delete or merge. Record the killed-mutant count before the change. If it cannot run, write "not measured" and the reason.
9. **Guards.** For each rule a program can check that the project does not enforce, propose a guard in the project: retries off, shuffle on, mock and env restore on, a network block per tier, pinned timezone and locale, and the lint rules for the project's runners in `references/frameworks.md`. Each guard is a finding with the action "add guard".
10. **Pick and brief.** Show the count per action. Ask the user which actions to apply through the questions capability in `rules/environment.md`, up to 4 options per question. Write the brief (format below).

## Pattern list

Use the pattern list for the project's runners in `references/frameworks.md` ("Pattern lists"). For a runner it does not list, write the same list first: one `git grep` per rule a pattern can find, with the runner's own names. Each hit is a lead to read, not a finding.

## Finding format

One line per finding:

`path:line test name — rule ID — action — evidence`

Always name the test, so a reader can find it without opening the file. A project-level finding names the config file instead.

Example: `tests/test_cart.py:42 test_total_returns_price — T-CAN-FAIL — delete — asserts only the value mock_price.return_value was told to return`

## Actions

`keep`, `delete`, `rewrite`, `move down`, `merge`, `fix flake`, `add guard`. A flaky test gets `fix flake` (at its cause) or `move down`. Never retry or skip it.

## Brief

Find the glossary directory: run `bash "${CLAUDE_SKILL_DIR}/../glossary/path.sh"`. Write the brief to `<that directory>/test-audit/<YYYY-MM-DD>-<slug>.md`. Commit it with the git rules in the `glossary` skill.

The brief has:
- The findings, in the finding format, grouped by action.
- The actions the user picked, and the unreachable-code answers from step 7.
- The conflicts with project rules.
- Acceptance criteria, each with the command that checks it:
  - The suite is green: `<test command>` exits 0.
  - The network-blocked runs per tier are green: `<block command>`.
  - The killed-mutant count is not lower than `<count before>`: `<mutation command>`. Or "not measured" and the reason.

Print the brief path and this command, with the real repo path:

`cd <repo> && /at:implement <brief path>`

You cannot run `/at:implement` yourself: it starts only when the user types it.
