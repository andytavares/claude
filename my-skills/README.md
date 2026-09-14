# Skill set two

Five skills that cover one task from first prompt to merged PR, each pinned to the model and effort that fits its job. Install with:

```bash
sh ~/claude-throughput-kit/set2/install.sh
```

`/brief`, `/research`, and `/interview` share their names with set one. Whichever installer ran last owns those three names; run `../install.sh` to switch back. `/explain` and `/do-work` are new.

| Skill | Model / effort | Input | Output |
|---|---|---|---|
| `/brief` | Opus / medium | A Linear key or a quick prompt | `briefs/<id>.md`, sized S, M, or L to the work |
| `/research` | Opus / high | A brief, a spec, or a prompt, `--prd` or `--design` | A PRD or Design Document as a shareable artifact, plus `docs/research/<slug>.md` |
| `/explain` | Opus / high | A question about this codebase, optional `as:` format | The answer with file and line evidence, in the format asked for |
| `/interview` | Opus / high | An ask or a brief | `SPEC.md` covering the whole problem, not just the part the ask named |
| `/do-work` | Opus / medium plans, Sonnet / medium builds | A brief, a spec, or a quick ask | A PR, one commit per unit, with the command outputs |

## How they fit together

```
/brief LIN-142          sizes the ask; L briefs are produced by /research
    │
    ├─ S or M ──────────────────────► /do-work briefs/LIN-142.md
    │
    └─ L, or "needs /interview" ──► /interview briefs/LIN-142.md
                                         │  calls /explain to map the code
                                         │  calls /research for the unknowns
                                         ▼
                                     SPEC.md ─────► /do-work SPEC.md
```

`/research` and `/explain` also stand alone: a design document to share, or an answer about how something works.

## Walkthrough

### A ticket

1. `/brief LIN-142`. It reads the ticket and enough code to size it, then writes the brief at that size: two sentences for an S, a page with criteria for an M, a design document via `/research` for an L. It prints the path and the size.
2. For S or M: `/do-work briefs/LIN-142.md`. Opus at medium effort reads the files and their callers, writes a numbered plan of units, and delegates each unit to the `worker` subagent, which is Sonnet at medium effort. Independent units run at the same time. A worker that fails its check is relaunched once with the failure text; a second failure is fixed by the orchestrator itself. Then lint, test, and coverage run to exit 0, one commit per unit, and a PR opens. It prints the PR URL and the outputs.
3. For L: `/interview briefs/LIN-142.md`, then `/do-work SPEC.md`.

### An ask that is only part of the problem

1. `/interview "add rate limiting to the public API"`. Before it asks you anything it runs `/explain` on the area and lists every adjacent concern the ask did not mention: other callers, stored data in the old shape, failure paths, rollback, docs. Each is marked covered, not covered, or unknown. Unknown externals go to `/research`.
2. It interviews you with AskUserQuestion, blind spots first, a recommended answer on every question, until every item is covered or deferred with a reason.
3. It writes `SPEC.md` with the whole problem, non-goals, criteria that can be false, and any decision that survived with your options and its recommendation. It prints the number of blind spots it found.
4. `/do-work SPEC.md`.

### A document to share

1. `/research "move session storage from Redis to Postgres" --design`. It reads the code, fetches current docs for anything external, and writes a Design Document: context, current state with paths, at least two options with tradeoffs, the decision, the design with file paths, verification commands, risks, open questions.
2. It publishes the document as an artifact and prints the URL, and writes the same Markdown under `docs/research/`. Pass `--prd` for the product format, `--file` for Markdown only.

### A question

1. `/explain "what happens between a terminal keystroke and the pty write" as: diagram`. It uses CodeGraph when the repo has it, follows the calls across files, and answers first with a mermaid diagram, then the file and line evidence. Formats: table, list, diagram, prose, or `doc` to write it under `docs/explain/`.
2. To run it on Fable, change `model: opus` to `model: fable` in `skills/explain/SKILL.md`.

## Notes

- Every skill is user-invoked only and ends by printing its output and nothing else.
- `/do-work` will stop and name the decision if a brief says `needs /interview` or a unit cannot be written without a choice the brief does not make. It does not guess.
- The `worker` subagent is installed at `~/.claude/agents/worker.md`. It builds one unit, pastes its command outputs, and never marks its own work complete.
