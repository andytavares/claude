---
name: brief
description: Turn a Linear ticket key or a quick prompt into a brief sized to the work, from two sentences to a full design document, for the other skills to work from
disable-model-invocation: true
argument-hint: "[LIN-123 | quick prompt]"
model: opus
effort: medium
---
Brief this: $ARGUMENTS

If it looks like a Linear key, read the ticket with the Linear tools, including comments and linked issues. Otherwise the argument is the ask.

Read enough of the codebase to know which files are involved and whether the approach is obvious. Then size it, and write `briefs/<id>.md` at that size and no larger. `<id>` is the ticket key or a short kebab-case slug.

| Size | When | The brief is |
|---|---|---|
| **S** | One place to change, approach obvious, a reviewer would nod at one sentence | One or two sentences: what changes, where, and the command that proves it. |
| **M** | Several files, approach clear once the code is read, no design choice | A paragraph of intent, the files by real path, what is out of scope, acceptance criteria as statements that can be false, the proof command. |
| **L** | A design choice, more than one reasonable approach, cross-cutting, or unclear boundaries | Run `/research` on the ask with `--design` (or `--prd` if it is product-shaped) and make its output the brief. Note at the top which decisions are still open. |

Every size ends with one line, `size: S | M | L`, and for S and M a `model:` and `effort:` line: `sonnet`/`medium` for S, `sonnet`/`high` for M. L is handed to `/implement`, which plans on its own.

If the ask is L and the design choice cannot be made without the asker, do not guess: write the brief up to the open decision and say `needs /interview` on the last line.

Print the path and the size. Nothing else.
