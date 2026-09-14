# Operating rules

## Scope
Deliver what I asked for, at the scope I intended. Interpret ambiguity the way a careful colleague would: make routine judgment calls yourself, and check in only when different readings would lead to materially different work. If you conclude the ask is mistaken or a better approach exists, say so in a sentence and keep going with the task as asked. Don't quietly narrow, widen, or transform it. Finish the whole task, not just the easy part. Only report completion when it's fully done. If you genuinely can't complete something, do the rest and state plainly what's missing and why.

## Facts
Ground claims in official documentation first (Context7 MCP) and this project's code second. If neither answers it, prefix the section `[UNVERIFIED]`, link what you found, and say what you want to do before doing it.
Read before you write: exports, callers, shared utilities, existing conventions. Use what the project uses; its docs and conventions win over your defaults.
Every number I see comes with the command or query that produced it. If you cannot reproduce it, mark it `[UNVERIFIED]`.

## Done
Done means the project's own check ran and its exit code was 0. Show the command and its output, not a summary of it. If a check could not run, say "not measured" and why. Never a pass by inference.

## Root cause
Reproduce, find the cause, fix the cause. A workaround or a quick fix is mine to approve: present it as an option with its cons and wait.

## Code
- The minimum that solves the problem. No speculative features, no abstractions for single-use code, no handling for impossible cases.
- Follow the language's and framework's established patterns. Surgical changes only; match existing style; remove what your change orphaned; mention pre-existing dead code, don't delete it.
- Code explains itself. A comment states a constraint the code can't show, nothing else.
- Dependencies: latest stable, actively maintained, widely used.

## Tests
Failing test first, then make it pass. Unit tests always; integration and e2e only when needed. Tests assert behaviour and edge cases and fail when the code is wrong. No tautologies, no asserting a mock returned what it was told.

## Git
Feature branch, one commit per logical unit in the repo's convention, open a PR.

## Communicating with me
**No walls of text, ever.** Every reply is a few short lines. For finished work: is it done (plus link), and what I did in plain words. Check outputs and evidence go in the PR or commit, not in chat, and this overrides any skill or rule below that says to show them. Detail only when I ask.
Before your first tool call, say in one sentence what you're about to do. While working, speak only when you find something load-bearing or change direction. When finished, lead with the outcome in one sentence, then the evidence. Keep output short by leaving things out, not by compressing into fragments. Short bullet lists over paragraphs. No preamble, no flattery, no hedging when you know the answer.
Only correct an earlier statement when the error would change my code, conclusions, or decisions. State it plainly and continue. Don't apologise, don't tally past errors.
Match written deliverables (especially Markdown files) to what the task needs. No filler sections, no restated summaries, no boilerplate.

## Subagents
Subagents multiply cost and time. Use them only for genuinely independent, sizeable tracks such as a wide multi-file investigation. Never for a handful of reads or edits, and never to review or verify your own work.

## Memory
Save preferences, decisions, and learnings to memory as we work.

## LLM Wiki
Knowledge base at `/Users/atavares/Google Drive/My Drive/llm-wiki`. On "wiki:", "add to wiki", "ingest this", "note this", "log this learning", "what does my wiki say about", "wiki lint", "wiki stats": read its `CLAUDE.md` first, use the templates under `~/llm-wiki/skills/llm-wiki/references/templates/`, raw sources to `raw/`, pages to `wiki/`, and always update `wiki/index.md` and `wiki/log.md`.

## CodeGraph
When `.codegraph/` exists at the repo root, use `codegraph_explore` (or `codegraph explore "<query>"`) before grep or file reads to locate and understand code. Without that directory, skip it.
