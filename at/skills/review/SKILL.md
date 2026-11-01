---
name: review
description: Review every file in a branch's diff for correctness bugs in one pass. Faster than the bundled /code-review, and it never skips a file.
argument-hint: "[base branch]  (default: the remote default branch)"
context: fork
model: opus
effort: medium
---
Base: $ARGUMENTS

1. Find the scope. Run `git fetch -q origin`. If the base above is empty, use `git rev-parse --abbrev-ref origin/HEAD`. Run `BASE=$(git merge-base <base> HEAD)`. The scope is `git diff $BASE`: every commit on the branch plus uncommitted changes. Never review only the latest commit or a range of recent commits.
2. Read the whole diff. Run `git diff --stat $BASE` and keep the file list. Read `git diff $BASE` in full. If it is too long for one read, write it to a file in your scratchpad and read it in parts until you read every line. Do not filter by path, do not pipe through `head`, and do not skip tests, docs, config or scripts. For a lockfile or a generated file, check only that it matches the source change that made it.
3. Find bugs in one pass. For each hunk, ask which input, state or timing makes it wrong: wrong conditions, off-by-one, missing null checks, missing `await`, dropped error handling, removed guards, tests that cannot fail. Find the callers of each changed function with `git grep -n -w` and check that the change does not break them. Read more of a file only when the hunk cannot answer the question. Do not report style, naming or formatting. Do not edit files.
4. Report. The first line is `Reviewed <n> of <n> files in git diff --stat <BASE sha>.` Then one line per finding, most severe first: `path:line — the bug — the input or state that triggers it`. With no findings, write `No findings.`
