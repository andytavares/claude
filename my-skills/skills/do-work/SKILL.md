---
name: do-work
description: Implement a brief or spec. Plans and orchestrates on Opus at medium effort, delegates the building to Sonnet workers at medium effort, ends in a PR.
disable-model-invocation: true
argument-hint: "[briefs/<id>.md | SPEC.md | quick ask]"
model: opus
effort: medium
---
Work: $ARGUMENTS

If the argument is a path, read it; it is the brief or spec. Otherwise it is the ask, and a size-S brief in your head is enough.

## Plan

Read the files the brief names and their callers. Write the plan as a numbered list of units, each one a change a worker can make in one sitting without seeing the others: the files it touches, the test it writes first, and the command that proves it. Units that must touch the same files are one unit. Order them by dependency. Keep the list as short as the work allows.

If the brief says `needs /interview` or a unit cannot be written without a decision the brief does not make, stop and say which decision. Do not guess it.

## Build

Delegate each unit to the `worker` subagent (Sonnet, medium effort), with the unit's text as its whole brief plus the repo's lint and test commands. Launch independent units in one message so they run concurrently; launch dependent ones after their dependency reports back. Brief each worker precisely the first time. When a worker reports, take its result; do not redo its work.

A worker that reports a failing check gets one relaunch with the failure text added to its brief. A second failure comes back to you: fix that unit yourself, in this session.

## Prove

Run the repo's own lint, test, and coverage commands. Every exit code 0, or fix until it is. Show the outputs.

## Ship

Commit on a feature branch in the repo's convention, one commit per unit, and open a PR with `gh`. The body is the plan, what each unit did, and the command outputs.

Finish with the PR URL and the command outputs. Nothing else.
