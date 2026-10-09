---
name: intake
description: Size, brief, and dispatch a whole batch of asks at once. The entry point for "here are ten things, go".
disable-model-invocation: true
argument-hint: "[LIN-1 LIN-2 'free text ask' ... | --file asks.md]"
allowed-tools: Bash(claude *) Bash(cat *) Bash(mkdir *) Read Write
effort: medium
---
Asks: $ARGUMENTS

If `--file` is given, each non-empty line of that file is one ask. Otherwise each argument is one ask: a Linear key is read from Linear, anything else is taken as written.

For every ask, size it and route it. Do all of them before dispatching any, so the batch launches together.

## Sizing ladder

| Size | Signal | Route | Model / effort |
|---|---|---|---|
| **trivial** | One file, one obvious edit, describable as a one-line diff | Do it here, now, in this session, then commit and open a PR | this session as-is |
| **small** | Files you can name, approach obvious, under an hour | `claude --bg` | `sonnet` / `medium` |
| **medium** | Several files or modules, approach clear once the code is read | `claude --bg` | `sonnet` / `high` |
| **large** | Approach not obvious, root-cause work, cross-cutting | `claude --bg` | `opus` / `high` |
| **spec-first** | Cannot write a proof command without deciding the design | Write `briefs/<id>.md` with a note that it needs `/at:interview` first. Do not dispatch. | none |
| **mechanical fan-out** | The same change across many files | Print an `ultracode` prompt for it instead of dispatching | none |

Effort is a property of the ask, not the batch. Two asks in the same batch can land on different rungs.

## For each dispatched ask

1. Write `briefs/<id>.md` in the `/at:brief` format: change, files, out of scope, proof command, dispatch line.
2. Launch it:

```bash
claude --bg --name "<id>" --model <model> --effort <effort> --permission-mode auto "$(cat briefs/<id>.md)"
```

## Finish

Print one table: id, size, model/effort, route, session name or "done here" or "needs /at:interview". Then run `/at:fleet --watch` so this session is woken when any of them finishes. Nothing else.
