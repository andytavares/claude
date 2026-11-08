---
name: postmortem
description: Read this session and list changes to the Claude config that stop repeated friction. You pick, then it writes a brief for /at:implement.
disable-model-invocation: true
argument-hint: "[focus]  (default: the whole session)"
model: opus
---
Focus: $ARGUMENTS

Find friction in this session, then propose fixes to the config in the repo named in `~/.claude/skills/at/.source-repo`. If that file does not exist, tell the user to run `./install.sh` and stop.

## Find friction

Read the session from its start. Read the primary sources: the prompts, the tool calls, the errors, the corrections. Look for:
- Navigation: files or commands Claude had to search for more than once.
- Repeated asks: something the user said or approved more than once.
- Missing checks: a mistake a hook, a test or a command would have caught.
- Wrong or stale instructions: a rule in `global/CLAUDE.md`, `rules/` or a skill that was ignored, misread or false.
- Slow steps: tool calls or subagents that did not change the result.
- Permission prompts for safe commands that appeared more than once.

A rule that a program can check becomes a hook or a gate, not prose. Prose goes in `rules/` only for a judgement call. Keep `global/CLAUDE.md` short: pointers and rules that apply to every task.

## Propose

List the fixes, most severe first. Each fix has: the friction (one line, with the prompt or tool call that shows it), the change, and the file in the source repo it changes. No fix without evidence from this session.

Ask the user which fixes to keep, with AskUserQuestion, up to 4 per question.

## Brief

For the fixes the user picked, write one brief to `~/at-skills-data/postmortem/<YYYY-MM-DD>-<slug>.md` and commit it there (see the `glossary` skill for the git rules). The brief has: the problem, the picked fixes with target files, and acceptance criteria that can be false, each with the command that checks it.

Print the path and this command, with the real source repo path:

`cd <source repo> && /at:implement <brief path>`

You cannot run `/at:implement` yourself: it starts only when the user types it.

Adapted from mattpocock/skills (MIT): https://github.com/mattpocock/skills/tree/main/skills/engineering/retro
