---
name: implement
description: Implement a brief or spec. Plans and orchestrates on Opus at medium effort, delegates the building to Opus workers at medium effort, ends in a PR.
disable-model-invocation: true
argument-hint: "[briefs/<id>.md | SPEC.md | quick ask]"
model: opus
effort: medium
---
Work: $ARGUMENTS

If the argument is a path, read it; it is the brief or spec. If it looks like a Linear key, read the ticket with the Linear tools, including comments and linked issues. Otherwise it is the ask, and a size-S brief in your head is enough.

If the brief or spec has open questions (an "Open questions" section, or items marked open, TBD or unresolved), ask the user each one with the AskUserQuestion tool before you start any other step. Ask up to 4 per call, with the recommended answer as the first option, marked "(Recommended)". Treat each answer as part of the spec. Start the plan only when every open question has an answer or the user defers it.

Work in a git worktree. If you are not in one, use the existing worktree for this work, or create one in `.worktrees/` at the repo root. Run `git fetch` first and create a new worktree from the remote default branch (`origin/main`). In an existing worktree, pull its branch, and merge the default branch if it has commits from more than 3 hours ago that the branch lacks. A worktree location in the prompt or in the repo's `CLAUDE.md` replaces this default.

## Plan

If the brief does not say `needs /at:interview` and you can state the diff in one sentence, say the sentence, skip the survey and the workers: write the failing test, make it pass, commit, then go to Prove.

Run the `at:survey` skill on the brief first. Read the files the brief names and their callers. Write the plan as a numbered list of units, each one a change a worker can make in one sitting without seeing the others: the files it touches, the Reuse and Shape lines from the survey it needs, the test it writes first, and the command that proves it. Units that must touch the same files are one unit. Order them by dependency. Keep the list as short as the work allows.

If the brief says `needs /at:interview` or a unit cannot be written without a decision the brief does not make, stop and say which decision. Do not guess it.

## Build

Before launching any worker, do the shared setup once yourself: install, build, anything every unit's checks need. Workers never rebuild or reinstall while another worker's checks are running.

Delegate each unit to the `at:worker` subagent (Opus, medium effort), with the unit's text as its whole brief, the glossary directory path (get it by running the `glossary` skill) when that directory exists, plus the repo's lint and test commands, scoped to what the unit touches. Each brief ends with a time box ("report within 20 minutes with what you have").

Checks in a brief are targeted, never whole-suite:
- the tests for the files the unit touches, run once;
- anything the unit made or changed that must be stable, repeated at most 3 times;
- never a loop that runs every test on its own, and never the full suite repeated. Those belong to Prove, once.

Launch independent units in one message so they run concurrently; launch dependent ones after their dependency reports back. Brief each worker precisely the first time. When a worker reports, take its result; do not redo its work.

A worker that reports a failing check gets one relaunch with the failure text added to its brief. A second failure comes back to you: fix that unit yourself, in this session.

A worker that has not reported by its time box, or says it is waiting on its own background work, gets one message asking for its report now.

When a unit's checks pass, commit it on the feature branch in the repo's convention, one commit per unit, so Prove sees the work in `main...HEAD`.

## Prove

1. For a large or complex change, run the `at:code-review` skill once, as `at:code-review <default branch> <the brief or spec path or URL>` when the work has one, and wait for its report. Fix the `Against the spec` list too. Skip it for trivial work. If its first line counts fewer files than the diff has, review the missing files yourself. Fix each finding in this session; do not relaunch workers for review findings. Commit the fixes. Do not review again after the fixes.
2. Run the stability check from the `at:tests` skill once, for every test spec file added or edited in `main...HEAD`: the spec file alone, then 30 shuffled runs for unit and integration specs, `--repeat-each=5 --retries=0` for E2E specs, with more workers than cores. Fix each failure at its cause; never retry.
3. Run precommit checks once until every exit code 0, or fix until it is. After a fix, rerun only what the fix touches, then the full command once more.
4. Run `uv run --script "${CLAUDE_PLUGIN_ROOT}/hooks/clean-gate/gate.py" report main..HEAD` once and fix what it lists. It also covers files edited through Bash, which the edit hook does not see.

## Ship

Commit anything Prove changed, then open a draft PR with `gh`. The body uses the PR format in `~/.claude/rules/writing.md`.

Finish with the PR URL. Then the short report CLAUDE.md asks for: what was done, what was skipped, what differs from the plan.
