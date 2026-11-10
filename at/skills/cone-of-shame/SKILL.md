---
name: cone-of-shame
description: Audit your previous response, or the text given, against the rules. Redo the work that broke them, then fix the cause in the Claude config so the same class of mistake cannot repeat.
argument-hint: "[what went wrong | text]  (default: your previous response)"
disable-model-invocation: true
model: inherit
---
Input: $ARGUMENTS

The user says your output was bad. Open the reply with one blunt line that names the failure. No apology, no excuse, no request for permission. Then find the mistakes, redo the work, and remove their cause.

The input is a note on what went wrong, text to audit, or both. If it is empty, audit your previous response and the tool calls that led to it.

## Audit

Read `CLAUDE.md` and each file in `rules/` in the config directory (`rules/environment.md`), and the SKILL.md of each skill that ran in the turn. List each violation, most severe first: what you did, quoted from the response or a tool call, and the rule it broke as `path:line`, or "no rule". The note names at least one violation. Find the others too.

## Redo

Fix the output in this session first. Finish the work you stopped, undo what you did against a rule, and rewrite what you wrote badly. Follow the original task and its skill.

## Root cause

For each violation, name the cause in one line:
- Missing: no rule covers it.
- Unclear: the rule can be read two ways, or another rule contradicts it.
- Ignored: the rule is clear, but nothing makes it hold at the step where it applies.
- Setting: a skill or agent setting caused it, such as `model` or `effort`.

A rule that a program can check becomes a hook, a gate or a test, not prose. A judgement call goes in the skill step where it applies, or in `rules/`. Keep `global/CLAUDE.md` short. Write each fix for the class of mistake, never for this one case. For "Ignored", do not repeat the rule in more words: move it to the step where it applies, or make a program check it.

## Fix

The config is in the repo named in `${CLAUDE_PLUGIN_ROOT}/.source-repo`. If that file does not exist, ask the user for the path of their clone of this harness. If they have none, write the fix as a brief to the glossary directory, print its path, and stop.

Run `git fetch`, then create a worktree from the remote default branch, as `rules/environment.md` says. For a hook, gate or script, write the failing test first. Run the checks listed in the repo's README until each exit code is 0. Commit in the repo's convention, then open a draft PR through the code host (`rules/environment.md`). Use the PR format in `rules/writing.md`. Link the ticket as the operating rules say.

## Report

- One blunt line that names the failure.
- Each violation in one line, with its rule and its cause.
- What you redid.
- The draft PR URL, and this line: run `./install.sh` after the merge.
