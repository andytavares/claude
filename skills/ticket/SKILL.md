---
name: ticket
description: Implement one Linear ticket end to end in this session. Failing test first, fix, repo checks green, commit, PR.
disable-model-invocation: true
argument-hint: "[LIN-123]"
effort: high
---
Implement Linear ticket $ARGUMENTS.

1. Read the ticket. If the acceptance criteria are missing or contradictory, write the two or three readings and pick the one a careful colleague would, stating it in one line.
2. Find the files involved by reading the codebase, not by guessing from the title.
3. Write the failing test first, where this repo has tests.
4. Make the smallest change that makes it pass, matching the surrounding code.
5. Run this repo's own lint, test, and coverage commands from its scripts. Fix until every exit code is 0.
6. Commit on a feature branch in this repo's commit convention and open a PR with `gh`. The PR body is: what was asked, what changed, the command outputs.

Finish with the PR URL. Nothing else.
