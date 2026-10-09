---
name: survey
description: Before writing code that adds a function or touches more than one file, map the flow it sits in, the existing code it can reuse, and the nearest example to copy. Produces a short reuse map for the plan and the PR.
argument-hint: "[what is about to be built]"
---
Change: $ARGUMENTS

Find what already exists before anything is written. Use the repo's code-intelligence tools in this order: `codegraph explore` when `.codegraph/` exists, the LSP (workspace symbols, find references), then `git grep -n -w`. Search by likely names and by key literals, since an existing helper may have a different name.

Report exactly three parts, each line with `path:line`:

```
Flow:   the entry point and call chain this change sits in
Reuse:  existing symbols that already do part of the job, and what each does
Shape:  the nearest existing sibling to copy (e.g. "new IPC handler → follow src/ipc/run-channels.ts")
```

Write "none found" for an empty part, with the searches you ran. Keep the map under 20 lines. Use it while writing, and paste it into the plan and the PR body.
