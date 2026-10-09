---
name: tool-eval
description: Evaluate a tool or library against fixed criteria in a scratch project and write a verdict
disable-model-invocation: true
argument-hint: "[tool name] [what we would use it for]"
effort: high
---
Evaluate: $ARGUMENTS

Set the criteria before installing anything. Default set, replace any that do not apply: install and first-run time, fit for the stated use, documentation quality (fetch current docs, do not rely on memory), maintenance signal (last release, open issues, maintainers), licence, and one thing it does badly.

Work in a scratch directory under `evals/<tool>/`. Build the smallest thing that exercises the stated use. Record every command you ran.

Write `evals/<tool>/EVAL.md`: verdict in one line (adopt, trial, avoid), then one row per criterion with the evidence, then the commands. Print the path.
