---
name: harness-setup
description: Set up the quality gates for the current repo. Finds the test command and the test paths from the repo's own evidence, confirms them with the user, and writes harness.toml. Run it when a harness message says "not measured".
disable-model-invocation: true
---
The gates in `${CLAUDE_PLUGIN_ROOT}/hooks/harness/harness.py` know no language or layout. They read `harness.toml` in the repo's data directory: run `bash "${CLAUDE_PLUGIN_ROOT}/skills/glossary/path.sh"` to find it.

1. Find the evidence, in this order: the CI config, then `CONTRIBUTING`, `README` and `CLAUDE.md`, then the build manifests. Note each fact with `path:line`. Do not use a command or a path that no file in the repo shows.
2. Find `test`: one shell command that runs the tests for the changed code and exits non-zero when a test fails. Run it once. It must exit 0 on the current code.
3. Find `tests`: glob patterns (`fnmatch`, matched on repo-relative paths) for every test file. Find `skip`: globs for changed files that are not code, such as lockfiles and docs.
4. If the repo puts tests inside source files, find the lines that mark test code and add them to `mutation_ignore` as regular expressions.
5. If the base branch cannot be found by `bash "${CLAUDE_PLUGIN_ROOT}/scripts/default-branch.sh"`, ask the user for it and set `base`.
6. Show the user each value with its evidence, through the questions capability in `rules/environment.md`. Write the file only after they confirm.

```toml
base = "upstream/trunk"            # only when default-branch.sh cannot find it
test = "<command from the evidence>"
tests = ["<glob>"]
skip = ["<glob>"]
mutation_ignore = ["<regex>"]      # optional
check_replies = false              # true: also check the final reply with Vale
prose_min_words = 25               # tool text with fewer words is not checked

[[rule]]                           # optional, one per repeated correction
name = "<kebab-case>"
globs = ["<glob>"]
pattern = '<regex on the text an edit adds>'
message = "<what to do instead, one sentence>"
```

If a gate still says "not measured" after the file exists, it names what is missing. Fix that value; never weaken a check to make the message go away.
