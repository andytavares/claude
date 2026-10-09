---
name: fleet
description: Triage every background session, merge green PRs, re-dispatch failures, and subscribe to be woken when any session finishes
disable-model-invocation: true
argument-hint: "[--watch] [--no-merge]"
allowed-tools: Bash(claude agents *) Bash(until *) Bash(claude logs *) Bash(claude --bg *) Bash(gh pr *) Bash(git *) Read Write
effort: medium
---
Sessions right now:

```!
claude agents --json || true
```

Arguments: $ARGUMENTS

Produce one table, one row per session: name, state, PR number if any, check status from `gh pr checks`, next action. Then act on every row without asking:

- **Completed, PR green.** Merge it with `gh pr merge --squash --delete-branch` unless `--no-merge` was passed. Then `claude rm <id>`.
- **Completed, PR red or no PR.** Read `claude logs <id>` for the last failure. Rewrite `briefs/<id>.md` with what was missing, bump effort one rung if the failure was a skipped step or an unrun check, and relaunch it with the same `claude --bg` command `/at:dispatch` uses. Once. A brief that fails twice is listed as needing you, with the failure verbatim.
- **Needs input.** Print the blocking question verbatim. If the brief already answers it, add the answer to the brief in plain words and relaunch. Otherwise list it for you.
- **Working.** Leave it alone.

With `--watch`: for every session still Working, start this with Bash `run_in_background`, filling in its `id` and current `state`:

```bash
until [ "$(claude agents --json --all | jq -r '.[] | select(.id=="<id>") | .state')" != "<state>" ]; do sleep 30; done
```

It exits when that session changes state or disappears, and you are re-invoked then. Run this skill again with the same arguments. That is the loop: it wakes on a session's state change, not on a fixed schedule.

Output is the table, then one line per action taken, then the list of things only you can answer. No commentary.
