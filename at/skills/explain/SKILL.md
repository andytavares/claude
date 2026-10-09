---
name: explain
description: Research this codebase and answer a question about it in the format asked for
disable-model-invocation: true
argument-hint: "[question] [as: table | list | diagram | prose | doc]"
model: opus
effort: high
---
Question: $ARGUMENTS

Answer from the code, not from memory. When `.codegraph/` exists at the repo root, use `codegraph_explore` first to locate symbols and call paths; otherwise search and read. Follow calls across files until the answer is grounded; a claim about behaviour names the file and line it comes from. Use git history when the question is "why".

For a question wide enough that reading would fill this context, use one subagent per independent area, brief each precisely once, and merge what comes back. Do not use subagents for a few file reads.

Format: if the argument names one after `as:`, use it. Otherwise match the question: a "how does X work" gets prose with paths, a "what are all the Y" gets a table, a "what calls Z" gets a list, a "how do these fit together" gets a mermaid diagram, and `doc` writes `docs/explain/<slug>.md`.

Lead with the answer in one or two sentences. Evidence after, as file paths and line numbers. Say plainly what you could not determine and where you stopped. No narration of how you searched.
