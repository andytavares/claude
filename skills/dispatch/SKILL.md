---
name: dispatch
description: Launch one or many briefs as background sessions, each with the model and effort its brief names
disable-model-invocation: true
argument-hint: "[briefs/a.md briefs/b.md ... | briefs/*.md] [--headless]"
allowed-tools: Bash(claude *) Bash(cat *) Read
effort: low
---
Dispatch: $ARGUMENTS

For each brief, read its `model:` and `effort:` lines. The session name is the brief's `<id>`. Launch them all before reporting any.

Default, attachable in `claude agents`, isolated in its own worktree:

```bash
claude --bg --name "<id>" --model <model> --effort <effort> --permission-mode auto "$(cat <brief>)"
```

With `--headless`, a print run with hard rails instead, for scripts and fan-outs:

```bash
claude -p "$(cat <brief>)" --model <model> --effort <effort> --permission-mode auto \
  --max-turns 60 --max-budget-usd 25 --output-format stream-json --verbose
```

Print one line per launch: session name and command. Do not wait, attach, or summarize.
