---
name: implement
description: Implement a brief or spec. Plans and orchestrates on Opus at medium effort, delegates the building to Sonnet workers at medium effort, ends in a PR.
disable-model-invocation: true
argument-hint: "[briefs/<id>.md | SPEC.md | quick ask]"
model: opus
effort: medium
---
Work: $ARGUMENTS

If the argument is a path, read it; it is the brief or spec. Otherwise it is the ask, and a size-S brief in your head is enough.

If you are not in a git worktree switch to the one for this body of work or create a new worktree for this work if one does not exist yet. By default worktrees should exist in the root of the repo you're working in, inside a `.worktrees` folder, allow the user to override this either via prompt or their repo level `CLAUDE.md`.

## Plan

Run the `survey` skill on the brief first. Read the files the brief names and their callers. Write the plan as a numbered list of units, each one a change a worker can make in one sitting without seeing the others: the files it touches, the Reuse and Shape lines from the survey it needs, the test it writes first, and the command that proves it. Units that must touch the same files are one unit. Order them by dependency. Keep the list as short as the work allows.

If the brief says `needs /interview` or a unit cannot be written without a decision the brief does not make, stop and say which decision. Do not guess it.

## Build

Before launching any worker, do the shared setup once yourself: install, build, anything every unit's checks need. Workers never rebuild or reinstall while another worker's checks are running.

Delegate each unit to the `worker` subagent (Sonnet, medium effort), with the unit's text as its whole brief plus the repo's lint and test commands, scoped to what the unit touches. Each brief ends with a time box ("report within 20 minutes with what you have").

Checks in a brief are targeted, never whole-suite:
- the tests for the files the unit touches, run once;
- anything the unit made or changed that must be stable, repeated at most 3 times (`--repeat-each=3`, `vitest --repeat`);
- never a loop that runs every test on its own, and never the full suite repeated. Those belong to Prove, once. Launch independent units in one message so they run concurrently; launch dependent ones after their dependency reports back. Brief each worker precisely the first time. When a worker reports, take its result; do not redo its work.

A worker that reports a failing check gets one relaunch with the failure text added to its brief. A second failure comes back to you: fix that unit yourself, in this session.

A worker that has not reported by its time box, or says it is waiting on its own background work, gets one message asking for its report now.

## Prove

Run the repo's own lint, test, and coverage commands once each, in full. Every exit code 0, or fix until it is. After a fix, rerun only what the fix touches, then the full command once more.

Then run the `google-code-reviewer` agent on the branch with `main` as base, passing the reuse map. Fix every `[MUST]`, then run `uv run --script ~/.claude/hooks/clean-gate/gate.py report main..HEAD`.

## Ship

Commit on a feature branch in the repo's convention, one commit per unit, and open a PR with `gh`. The body starts with "How to read this change": the entry point, then each step in call order as `path:line`, with a mermaid diagram when the change spans more than three files. Then the plan, what each unit did, the command outputs, and the clean-gate report.

Finish with the PR URL. Nothing else.
