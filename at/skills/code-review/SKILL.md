---
name: code-review
description: Review every file in a branch's diff for correctness bugs. Unlike the bundled /code-review, it reads every file in one pass and never skips one.
argument-hint: "[base branch] [spec path or artifact URL]  (default: the remote default branch, no spec)"
context: fork
model: inherit
---
Input: $ARGUMENTS

The first word is the base branch. A second word, if present, is the spec: a file path or a published spec URL (read it as `rules/environment.md` says).

1. Find the scope. Run `bash "${CLAUDE_PLUGIN_ROOT}/scripts/default-branch.sh"`; it prints `<remote> <remote>/<branch>`. Run `git fetch -q <remote>`. If the base is empty, use `<remote>/<branch>`. Run `BASE=$(git merge-base <base> HEAD)`. The scope is `git diff $BASE`: every commit on the branch plus uncommitted changes. Never review only the latest commit or a range of recent commits.
2. Read the whole diff. Run `git diff --stat $BASE` and keep the file list. Read `git diff $BASE` in full. If it is too long for one read, write it to a file in your scratchpad and read it in parts until you read every line. Do not filter by path, do not pipe through `head`, and do not skip tests, docs, config or scripts. For a lockfile or a generated file, check only that it matches the source change that made it.
3. Find bugs in one pass. For each hunk, ask which input, state or timing makes it wrong: wrong conditions, off-by-one, missing null checks, missing `await`, dropped error handling, removed guards, tests that cannot fail. Find the callers of each changed function with `git grep -n -w` and check that the change does not break them. Read more of a file only when the hunk cannot answer the question. Do not report style, naming or formatting. Do not edit files.
4. Report. The first line is `Reviewed <n> of <n> files in git diff --stat <BASE sha>.` Then one line per finding, most severe first: `path:line — the bug — the input or state that triggers it`. With no findings, write `No findings.`
5. With a spec, read it in full, then add a second list under the heading `Against the spec`, kept apart from the bug list. One line each: `requirement or path:line — missing, extra (scope creep) or wrong — what the diff does instead`. Check each acceptance criterion in the spec. With no spec, skip this step.

Adapted from mattpocock/skills (MIT): https://github.com/mattpocock/skills/tree/main/skills/engineering/code-review
