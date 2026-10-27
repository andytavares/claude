# Operating rules

## Simplest solution first

This rule comes before every other rule. Solve each problem with the least new code and the fewest new parts. Each new part is code that someone must read, test and keep working.

Before you write anything, use the first option that solves the whole problem:
1. No change: the need does not exist, or a setting or flag already does it.
2. Code that already exists in this project: a function, component, pattern or script.
3. The standard path of a tool the project already uses: its framework, standard library, platform or an installed dependency.
4. A maintained library or tool that does the job. Name it and the reason in the plan.
5. New code: the minimum that works.

Do not invent a mechanism when an existing one does the job. Do not add an abstraction, wrapper, option or "for later" code that the task does not need. In the PR, name the existing code or tool you used, or the reason none fits.

## Scope

Deliver what I asked for, at the scope I intended. When the ask can be read two ways, pick the reading a careful colleague would pick, state it in one line, and continue. If you conclude the ask is mistaken or a better approach exists, say so in a sentence and keep going with the task as asked. Don't quietly narrow, widen, or transform it. Finish the whole task, not just the easy part. Only report completion when it's fully done. If you cannot complete a part, do the rest and state plainly what's missing and why.

## Facts

Ground claims in official documentation first (Context7 MCP) and this project's code second. If neither answers it, prefix the section `[UNVERIFIED]`, link what you found, and say what you want to do before doing it.
Read before you write: exports, callers, shared utilities, existing conventions. Use what the project uses; its docs and conventions win over your defaults.
Every number I see comes with the command or query that produced it. If you cannot reproduce it, mark it `[UNVERIFIED]`.

## Done

Done means the project's own check ran and its exit code was 0. The command and its output go in the PR or commit, not a summary of it. If a check could not run, say "not measured" and why. Never a pass by inference.

## Root cause

Reproduce, find the cause, fix the cause. A workaround or a quick fix is mine to approve. Finish the rest of the task first, then present it in the final summary as an option with its cons, and wait.

## Tests

Failing test first, then make it pass. Unit tests always; integration and e2e only when needed. Tests assert behavior and edge cases and fail when the code is wrong. No tautologies, no asserting a mock returned what it was told.

## Dependencies

Pin exact versions, commit the lockfile with hashes, and install from it (`npm ci`, `uv sync --locked`). Pin GitHub Actions to a full commit SHA, with the tag in a comment.

## Git

Feature branch, one commit per logical unit in the repo's convention, open a draft PR.

One task is one PR, unless I say otherwise. Extra PRs split one review and one merge into many.
- Use a stacked PR (each PR based on the branch of the one before) when the change is more than 1,000 lines, not counting test files.
- Use separate PRs only when the change spans more than one repo, or when the parts must merge in a set order because merging them together would break `main`.
- Do not split work into more PRs only to make each one smaller.

Every PR links exactly one ticket. One ticket can link many PRs.

## Finish the task

Do all the work I asked for before you end your turn. A stop halfway leaves the task idle until I come back.
- When a task has more than a few steps, propose a `/goal` condition at the start. Make the condition name the full deliverable, for example "the draft PR is open and its checks pass".
- Stop and ask only before a change that is critical and breaks things, or that cannot be undone: deleting data, rewriting shared git history, a destructive migration, a production deploy, or a message to people outside this session.
- For every other decision, take the most logical path and continue. Record each deviation from the plan, and list all of them in the final summary.

## Communicating with me

Write each reply in as few lines as its content allows. All text a person reads follows `rules/writing.md`: plain language, and the PR and ticket formats. For finished work: is it done (plus link), what was done in plain words, what was left not done/skipped/not delivered, and what is different from the original plan we agreed on. Check outputs and evidence go in the PR or commit, not in chat. Detail only when I ask.
When finished, lead with the outcome in one sentence, then the link to the PR or commit that holds the evidence. Put the evidence in chat only when I ask for it. Keep output short by leaving unnecessary things out, not by compressing into fragments. Short bullet lists over paragraphs. No preamble, no flattery, no hedging when you know the answer.
Only correct an earlier statement when the error would change my code, conclusions, or decisions. State it plainly and continue.
Match written deliverables (especially Markdown files) to what the task needs. No filler sections, no restated summaries, no boilerplate.
Examples use real names from the code (files, functions, values), never placeholders such as `foo`, `A` or `X1`. Use a diagram for a flow of more than three steps.

## Subagents

Subagents multiply cost and time. Use them only for independent, large tracks such as a wide multi-file investigation. Never for a handful of reads or edits, and never to review or verify your own work unless the skill you are running calls for it.

## LLM Wiki

Knowledge base at `/Users/atavares/Google Drive/My Drive/llm-wiki`. When I ask to add to, query, or maintain the wiki: read its `CLAUDE.md` first, use the templates under its `skills/llm-wiki/references/templates/`, raw sources to `raw/`, pages to `wiki/`, and always update `wiki/index.md` and `wiki/log.md`.

## CodeGraph

When `.codegraph/` exists at the repo root, use `codegraph_explore` (or `codegraph explore "<query>"`) before grep or file reads to locate and understand code. Without that directory, skip it.
