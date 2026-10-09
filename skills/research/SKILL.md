---
name: research
description: Turn a brief, spec, or prompt into a formatted One Pager, PRD, or Design Document, published as a shareable artifact by default
disable-model-invocation: true
argument-hint: "[brief path | spec path | prompt] [--one-pager | --prd | --design]"
model: opus
effort: high
---
Input: $ARGUMENTS

If the argument is a path, read it; it is the brief or spec. Otherwise it is the prompt. Choose the format: `--one-pager`, `--prd` or `--design` if given, else One Pager when the input asks for a short pitch or summary to align on before deeper work, PRD when the input is about users, outcomes, or scope, and Design Document when it is about how to build something already decided.

Research before writing. Read the parts of this codebase the input touches. For anything external, fetch current documentation rather than relying on memory, and cite it. Every claim that could be false carries its evidence: a file path, a command and its output, or a URL. Anything you could not verify goes in the open questions, never stated as fact.

## One Pager sections

Context and the problem in one paragraph, the proposed solution in 1-2 paragraphs and 2 diagrams at most if needed, the current state of the system, the outline of the changes needed. Should never be more than two pages of text.

## PRD sections

Problem, who has it, and the evidence. Goals and non-goals. Users and the jobs they are doing. Requirements as numbered, falsifiable statements, each marked must or should. Success metrics with how each is measured. Scope boundaries and what is explicitly deferred. Risks and open questions. Rollout.

## Design Document sections

Context and the problem in one paragraph. Goals and non-goals. Current state, from the code, with paths. Options considered, at least two, each with tradeoffs. The decision and why. The design: components, interfaces, data, and the sequence of changes, with real file paths. Testing and verification: the commands that will prove it. Risks and mitigations. Open questions. Alternatives rejected, in one line each.

## Length

Match the input. A two-sentence brief produces a page; a whole spec produces whatever the spec needs. No section that has nothing in it, no restated summary, no filler.

## Output

Publish the document as an artifact by default: load the `artifact-design` skill first, write the HTML, then publish with the Artifact tool, icon `document`, title the document's name.

Print the artifact URL and the file path. Nothing else.
