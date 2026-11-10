---
name: research
description: Turn a brief, spec, or prompt into a formatted One Pager, PRD, or Design Document, published as a shareable artifact by default
argument-hint: "[brief path | spec path | prompt] [--one-pager | --prd | --design]"
model: inherit
---
Input: $ARGUMENTS

If the argument is a path, read it; it is the brief or spec. Otherwise it is the prompt. Choose the format: `--one-pager`, `--prd` or `--design` if given, else One Pager when the input asks for a short pitch or summary to align on before deeper work, PRD when the input is about users, outcomes, or scope, and Design Document when it is about how to build something already decided.

Run the `glossary` skill first and use its terms.

For a Design Document, or any input that asks for a full audit or inventory, start one subagent right after the glossary step. Its brief is the input, word for word, and one instruction: list every place in the codebase the input covers, one line each, as `path:line — what is there`. Merge its list into the draft when it reports. While it runs, read and draft. Never end a message only to wait for a subagent: draft every section that does not depend on its result.

Research before writing. Read the parts of this codebase the input touches. For anything external, fetch current documentation rather than relying on memory, and cite it. Every claim that could be false carries its evidence: a file path, a command and its output, or a URL. Anything you could not verify goes in the open questions, never stated as fact.

## One Pager sections

Executive Summary: why this is needed, from a leadership perspective. Context and the problem, in one paragraph. The proposed solution, in one or two paragraphs, with at most two diagrams. The current state of the system. The outline of the changes. Maximum two pages of text.

## PRD sections

Executive Summary explaining from a leadership perspective why this is needed, Problem, who has it, and the evidence. Goals and non-goals. Users and the jobs they are doing. Requirements as numbered, falsifiable statements, each marked must or should. Success metrics with how each is measured. Scope boundaries and what is explicitly deferred. Risks and open questions. Rollout.

## Design Document sections

Executive Summary explaining from a leadership perspective why this is needed, Context and the problem in one paragraph. Goals and non-goals. Current state, from the code, with paths. Options considered, at least two, each with tradeoffs. The decision and why. The design: components, interfaces, data, and the sequence of changes, with real file paths. Testing and verification: the commands that will prove it. Risks and mitigations. Open questions. Alternatives rejected, in one line each. When the draft is complete, have one fresh subagent read only the input and the document once, and report claims the codebase contradicts: a wrong path, a wrong quote, or behavior described wrongly. The sweep at the start already covered missing items, so this check does not search for them. Fix each claim; ignore style findings.

## Renderings

If the document proposes a change the user sees (a web or app UI, a TUI, CLI output), it includes renderings, as `rules/writing.md` "UI and UX changes" describes. Put them in the section that describes the change.
- A changed screen or state: a before and an after rendering, then the list of changes.
- A new screen or state: write "New screen" and show only the after rendering.
- Before: run the current code and capture it. Start and capture the app through the run-and-capture capability in `rules/environment.md`. For a TUI or CLI, run the command and put its exact output in a `<pre>` block. If you cannot run the current code, say so in the open questions. Do not draw a before from memory.
- After: build the mockup in the artifact's HTML and CSS, at the same size as the before.

## Length

Match the input. A two-sentence brief produces a page; a whole spec produces whatever the spec needs. No section that has nothing in it, no restated summary, no filler.

## Output

Before you publish, run `uv run --script "${CLAUDE_SKILL_DIR}/check_refs.py" <document>` from the repo root. It exits 1 and lists each `path:line` that does not exist, and each quote right after a reference that is not on the cited line. Fix each one, then run it again until it exits 0.

Publish through the publish capability in `rules/environment.md`. For an HTML page, copy `${CLAUDE_SKILL_DIR}/template.html` and fill in its `<title>` and `<main>`. It already holds the theme, layout and components. Write new CSS only for a component the template does not have. Publish with icon `document`, and title it with the document's name.

Print the artifact URL and the file path. Then, unless another skill invoked this one, the short report CLAUDE.md asks for: what was done, what was skipped, what differs from the plan.

All output must follow the writing guidelines in `rules/writing.md`.