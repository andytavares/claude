---
name: diagnose
description: Use when something is broken, failing, slow or surprising, and for a CI build, a CI failure or a PR URL with "why did this fail" or "debug this". Finds the cause with a loop that can fail, then fixes it.
model: inherit
---
Problem: $ARGUMENTS

Find the cause with evidence, then fix the cause. Phase 1 is a gate: make no fix until a command fails on the bug. Use Phases 2 to 4 as far as the bug needs them.

Read the glossary first: run the `glossary` skill.

## Phase 0: Facts for a CI build or PR

If the input is a CI build URL, a build number or a PR URL, get the facts before you form a hypothesis, through the CI capability in `rules/environment.md`. Look only at jobs that failed or timed out, not soft or allowed failures. Read the log of the first failing job and quote the error and the file, test and line.

For any other problem, go to Phase 1.

## Phase 1: Build a feedback loop

This is the skill. Make one command that:
- fails when the bug is present (it can be red),
- gives the same result on every run,
- finishes fast,
- you can run without help, and
- you have already run.

Pick the cheapest that works: a failing test; a `curl` or CLI call with fixtures; a replay of a saved trace or log; a throwaway script; a fuzz loop; `git bisect run` over a range; a differential run (good against bad); a script that asks the user to do one step and read back the result. For a CI failure, rerun only the failing job's command locally.

Done when the command exists and you ran it and saw it fail. With no such command, do not go on. Tell the user what blocks it.

## Phase 2: Reproduce and cut

Remove one element at a time (a file, a flag, an input) until every element that is left is needed. The smallest repro is the evidence.

## Phase 3: Hypotheses

Write 3 to 5 causes, ranked. Each one says what you would see if it were true and what you would see if it were false. Show them to the user. Test the most likely first.

## Phase 4: Instrument

Prefer a debugger or a targeted assertion. Never log everything and search. Tag each line you add with a prefix such as `[DEBUG-a4f2]` so you can remove them all. Write `<REDACTED>` for secrets, tokens and customer data in anything you print or save.

## Phase 5: Fix the cause

Write the regression test first and see it fail at the right level: the smallest place where the cause shows. If no such place exists, that is the finding; say so. Then make the smallest change that passes it. A workaround is the user's to approve: finish the rest, then offer it as an option with its cons.

## Phase 6: Clean up

Remove every tagged line and throwaway file. Run the project's checks and report their exit codes.

## Report

Lead with the cause in one sentence, then the evidence (`path:line`, the failing job and log line, or the command and its output), the fix, and what you could not determine. If you learned a term of the repo, add it to the glossary. If the cause was a hard-to-reverse decision, offer an ADR.

Adapted from mattpocock/skills (MIT): https://github.com/mattpocock/skills/tree/main/skills/engineering/diagnosing-bugs.
