# Environment

Use what the user's environment has. Never assume that a tool, plugin, skill or MCP server is installed or connected. Skills and rules name a capability from this table, never a tool. When a step needs a capability, use the first provider that is present. When none is present, use the fallback and say so in one line.

| Capability | Providers, in order | Fallback |
| --- | --- | --- |
| Questions | The `AskUserQuestion` tool | Write each question in the reply, with the recommended answer first. Stop and wait. |
| Tracker | A connected issue-tracker tool (MCP), such as Linear or Jira | Ask the user to paste the ticket. |
| Code host | The host's CLI on PATH: `gh` (GitHub), `glab` (GitLab), or another | Push the branch. Print the URL that `git push` returns, and ask the user to open the PR. |
| CI | The CI's CLI on PATH (such as `bk`), or the code host CLI (`gh pr checks`, `gh run view --log-failed`) | Ask the user for the log of the first failing job. |
| Docs source | A connected documentation tool (MCP), such as Context7 | WebFetch or WebSearch of the official docs. |
| Publish | The `Artifact` tool. Load the artifact design skill first when the skill list has one. | Write a Markdown file to the glossary directory (the `glossary` skill). Print its path. |
| Read a published spec | The `Artifact` tool, `read` action | Ask the user to paste the spec or give a file path. |
| Code search | The `LSP` tool when it is active, then an index the repo has (such as `.codegraph/` with `codegraph explore`) | `git grep -n -w` on the name and on a key literal. |
| Run and capture the app | The `run` skill and a connected browser tool (such as Playwright) | Start it as the repo's docs say. If you cannot capture it, write "not captured" and why. |

## Terms

- **PR**: a pull request or merge request on the code host.
- **Ticket**: an item in the user's tracker. Never write a tracker's product name in a PR or commit unless the user does.
- **Config directory**: `$CLAUDE_CONFIG_DIR`, default `~/.claude`. The user's `CLAUDE.md` and `rules/` are there.
- **Default branch**: run `bash "${CLAUDE_PLUGIN_ROOT}/scripts/default-branch.sh"`. It prints `<remote> <remote>/<branch>`, for example `origin origin/main`. It picks `origin`, then the branch's upstream remote, then the only remote. With `--remote` it prints only the remote. Never assume a remote named `origin` or a branch named `main`.
- **Worktree**: create it in `.claude/worktrees/<name>` at the repo root. First add `.claude/worktrees/` to `.git/info/exclude` if it is not there, so the worktree never shows as untracked.
