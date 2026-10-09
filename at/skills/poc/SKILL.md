---
name: poc
description: Build a proof of concept with a runnable demonstration as its gate and a README of what was learned
disable-model-invocation: true
argument-hint: "[what to prove] [--dir path]"
effort: high
---
Prove: $ARGUMENTS

A proof of concept is done when it demonstrates the thing, not when it is polished. Before writing code, state in one line what command will demonstrate it and what output means yes.

Work in a fresh directory under `poc/` (or `--dir` if given), with the minimum dependencies. No tests unless the thing being proved is testability.

Done when:

- The demonstration command runs and produces the yes output. Put the command and output in the README.
- `README.md` in that directory says how to run it, what was proved, what was not, and what it would take to make it real.

Commit on a branch and open a draft PR so the result is visible.
