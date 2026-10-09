---
name: interview
description: Clarify an ask until no ambiguity is left, hunting the parts of the problem the ask did not mention, then write the spec
disable-model-invocation: true
argument-hint: "[ask | brief path]"
model: opus
effort: high
---
Ask: $ARGUMENTS

If the argument is a path, read it; it is the brief. Otherwise it is the ask.

The ask is usually a view of part of the problem. Your job is the whole of it. Before asking anything, map the problem space yourself:

1. Run `/at:explain` on the area the ask touches: what exists, who calls it, what depends on it, what it depends on.
2. List every adjacent concern the ask did not mention: other callers, other platforms or entry points, data already stored in the old shape, migrations, permissions, failure and retry paths, concurrency, observability, rollback, docs, and the people who will be affected. Mark each one as covered by the ask, not covered, or unknown.
3. If the ask depends on something external you do not know, run `/at:research` on that narrow question first.

Then interview with the AskUserQuestion tool. Only ask what the code and the research could not answer. Prioritise the not-covered and unknown items: those are the blind spots. Give the recommended answer with each question. Keep going until every item on the map is covered or explicitly deferred with a reason. Do not stop early because the original ask looks answered; stop when the problem does.

Write `SPEC.md`:

- The problem in full, including the parts the original ask left out.
- Goals and explicit non-goals, with the deferrals and their reasons.
- The files and interfaces involved, by real path.
- Acceptance criteria as statements that can be false, each with the check that proves it.
- Open decisions, if any survived, each with the options and your recommendation.
- An end-to-end verification step.

Print the path and the number of blind spots found. Nothing else.
