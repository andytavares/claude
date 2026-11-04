# Plugin evals

Docs: https://code.claude.com/docs/en/plugin-evals.md

## Graders
- Use a program grader for anything a program can check. Use an `llm` grader only for judgement.
- `type: regex` takes `pattern`, `flags`, `match` and `target`. `match` is `contains` (the default), `not_contains` or `count:N`. `target: last_message` checks the final reply. Put case-insensitivity in `flags: i`; inline `(?i)` does not work.
- `type: tool_used` takes `tool`, `input_match`, `min` and `max`. Set `min: 0` and `max: 0` to assert that Claude never called the tool.

## The sandbox
- Runs never ask for permission (don't-ask mode). A tool that needs a grant you did not give is removed, so Claude cannot call it.
- Bash, Write, Edit, WebFetch and real MCP tools are denied unless the run passes `--allow-tools`. Put the target before `--allow-tools`, because the flag takes a list.
- A grader that needs a real `klaviyocli` or Buildkite call cannot pass in the sandbox.

## Before a fix
1. Test each `regex` grader in `node` on a reply that must pass and a negated reply that must fail. Do this before the first eval run.
2. Prove the case fails against the old code: run it once, with `--runs 3`.
