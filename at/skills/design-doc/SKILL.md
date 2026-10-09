---
name: design-doc
description: Draft a design or strategy document from a spec, get it gap-reviewed once by a fresh subagent, and fix the gaps
disable-model-invocation: true
argument-hint: "[SPEC.md] [DESIGN.md]"
model: opus
effort: xhigh
---
Spec: $0. Output: $1 (default `DESIGN.md`).

Write the document from the spec and from this codebase. Sections: context and problem, options considered with tradeoffs, the decision and why, the design in enough detail to build from, risks, and what is explicitly not decided. Match the length to what the spec needs. No filler sections, no restated summaries.

When the draft is complete, use one subagent, once, with only the spec and the document, to report gaps: requirements in the spec the document does not address, and claims in the document the codebase contradicts. Fix the gaps it reports that affect correctness or the spec. Ignore style findings.

Finish with the path and the list of gaps that were fixed.
