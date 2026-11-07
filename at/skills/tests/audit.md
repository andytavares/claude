# Audit mode

Apply the rule list in `${CLAUDE_SKILL_DIR}/SKILL.md` to an existing suite. Scope: the path after `audit`, or the whole repo. The audit proposes; the user picks; `/at:implement` changes the code in a PR. Do not change test or production code here.

## Safety

- Run in a worktree, never in the user's checkout.
- Read the runner config before the first run. Block the network first where the runner allows it (`references/frameworks.md`).
- Stop and ask the user before a run that needs credentials, a shared service or a shared DB.

## Steps

1. **Inventory.** Find each runner and its config, and the test commands in README, `package.json`, `pyproject.toml` and CI files. Read the project's test rules (CLAUDE.md, CONTRIBUTING, ADRs). Count tests per tier, and record the command that counts them.
2. **Baseline.** Run the whole suite once. Record the exit code, the time and the failures. A red baseline is a finding; continue the audit.
3. **Config check.** Find: retries in any config or CI step (T-NO-RETRY); shuffle off (T-ALONE); mock, env or global restore off (T-CLEAN-SLATE); network open in any tier (T-BOUNDARY); timezone, locale or runtime version not pinned, or CI runs a different command than local (T-SAME-ENV); per-test timeouts (T-CONTROL-TIME); skipped tests with no issue; no repeat run after merge that looks for flakes.
4. **Dynamic checks.** Use the commands in `references/frameworks.md`.
   - Run the suite 3 times, shuffled, each with a new seed. Record each seed.
   - Run each spec that fails when shuffled alone. A spec that passes alone and fails shuffled is order-dependent (T-ALONE).
   - Run the unit tier with all sockets blocked. Run integration and E2E with only localhost allowed (T-BOUNDARY).
   - Run E2E specs with `--repeat-each=5 --retries=0` and more workers than cores. Use the project's own load tool if it has one.
   - Read CI history. A commit with both a passed and a failed run of one test is a flaky test:
     `gh run list --limit 100 --json headSha,workflowName,conclusion --jq 'group_by([.headSha, .workflowName])[] | select((map(.conclusion) | index("success")) and (map(.conclusion) | index("failure"))) | "\(.[0].headSha) \(.[0].workflowName)"'`
     Each hit is a lead. Confirm in the job logs that the same test passed and failed.
5. **Pattern scan.** Run the commands in "Pattern list" below. Keep the hit list per file.
6. **Read.** Read every test file, not only the hits. Read each test with the production code it calls and that code's callers. Give each test one action from "Actions", with the rule ID. For more than about 40 test files, start one subagent per top-level test directory, at most 8. Give each subagent the rule list, its hit list and the finding format.
7. **Unreachable code.** For each branch that no caller or boundary can reach (T-REACHABLE), ask the user with AskUserQuestion: "delete branch and test", "delete test only" or "keep". Deleting production code is destructive, so never decide alone.
8. **Mutation guard.** Where Stryker or mutmut runs on the project, run it on the modules whose tests the findings delete or merge. Record the killed-mutant count before the change. If it cannot run, write "not measured" and the reason.
9. **Guards.** For each rule a program can check that the project does not enforce, propose a guard in the project: `retries: 0`, shuffle on, mock and env restore on, a network block per tier, pinned timezone and locale, an eslint `no-restricted-syntax` rule for `waitForTimeout` and `setTimeout` in tests, `@typescript-eslint/no-floating-promises`, ruff `PT` rules, and a nightly CI job that repeats the suite and reports tests that both pass and fail on one commit. Each guard is a finding with the action "add guard".
10. **Pick and brief.** Show the count per action. Ask the user which actions to apply with AskUserQuestion, up to 4 options per question. Write the brief (format below).

## Pattern list

Set `TESTS` to a shell array of the test pathspecs, then pass it as `"${TESTS[@]}"`. This works in bash and zsh. The patterns use POSIX classes, because `git grep -E` on macOS does not support `\b` or `\s`. Each hit is a lead to read, not a finding.

```sh
TESTS=(tests '*.test.*' '*.spec.*' 'test_*.py')
git grep -L -E '(expect|assert)' -- "${TESTS[@]}"                                       # T-CAN-FAIL: file with no assertion
git grep -n -E 'mockReturnValue|mockResolvedValue|return_value[[:space:]]*=' -- "${TESTS[@]}"   # T-CAN-FAIL: possible mock-echo test
git grep -n -E 'toBeDefined\(\)|toBeTruthy\(\)|is not None$' -- "${TESTS[@]}"            # T-CAN-FAIL: weak assertion
git grep -n -E 'toHaveBeenCalled|assert_called|assert_any_call' -- "${TESTS[@]}"         # T-STATE: call assertion
git grep -n -E 'toMatchSnapshot|toMatchInlineSnapshot|snapshot' -- "${TESTS[@]}"         # T-NO-SNAPSHOT-ONLY
git grep -n -E '(^|[^[:alnum:]_])sleep\(|waitForTimeout|setTimeout\(' -- "${TESTS[@]}"   # T-WAIT-CONDITION
git grep -n -E 'waitFor\(.*getBy' -- "${TESTS[@]}"                                       # T-READY-TARGET: use findBy
git grep -n -E '\.(skip|only|fixme)\(|(^|[^[:alnum:]_])x(it|describe)\(|mark\.(skip|xfail)' -- "${TESTS[@]}"   # skipped or focused tests
git grep -n -E '^[[:space:]]+(if|for|while)[[:space:](]|\.forEach\(' -- "${TESTS[@]}"     # T-READABLE: logic in a test
git grep -n -E 'fireEvent\.|getByTestId' -- "${TESTS[@]}"                                # T-READABLE: query order, user-event
git grep -n -E 'https?://' -- "${TESTS[@]}" | grep -v -E 'localhost|127\.0\.0\.1'        # T-BOUNDARY: real host
git grep -n -E '\.setTimeout\(|timeout:[[:space:]]*[0-9]|mark\.timeout' -- "${TESTS[@]}"  # T-CONTROL-TIME: per-test timeout
git grep -n -i -E 'retries|retry|retryTimes|reruns' -- '*.config.*' pyproject.toml setup.cfg pytest.ini .github .buildkite   # T-NO-RETRY
```

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
  - 3 shuffled runs with new seeds are green: `<shuffle command>`.
  - The network-blocked runs per tier are green: `<block command>`.
  - The killed-mutant count is not lower than `<count before>`: `<mutation command>`. Or "not measured" and the reason.

Print the brief path and this command, with the real repo path:

`cd <repo> && /at:implement <brief path>`

You cannot run `/at:implement` yourself: it starts only when the user types it.
