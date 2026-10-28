# claude

My Claude Code setup: global rules, a clean-code standard, and a plugin named `at` that holds the skills, agents and the clean-code gate. Every skill runs as `/at:<skill>`, so none of them collide with other skills.

## Install, update, remove

Requires `uv` and `python3`.

The gate is a uv script. It pins its dependencies exactly and has a lockfile beside it (`gate.py.lock`) with the hash of every package. After changing its dependencies, run `uv lock --script at/hooks/clean-gate/gate.py` and commit the lockfile.

```sh
./install.sh      # installs or updates everything
./uninstall.sh    # removes everything and restores CLAUDE.md from the first backup
```

Install backs up `settings.json` and `CLAUDE.md` once. Run `/reload-plugins` in open Claude Code sessions or start a new one, then run `claude plugin list` and look for `at@skills-dir … loaded`. To change anything, edit it here and run `./install.sh` again. Skills and agents of your own in `~/.claude` are left alone.

If your repos need gitignored files such as `.env` to build, list them in a `.worktreeinclude` file at the repo root (`.gitignore` syntax). Claude Code copies them into every worktree it creates, so worktrees start ready to build.

## How it fits together

| Layer | Installed to | Loaded | What it does |
| --- | --- | --- | --- |
| `global/CLAUDE.md` | `~/.claude/CLAUDE.md` | Every session | How to work and report: scope, evidence, done means checks pass, one PR per task, finish without stopping, short replies |
| `rules/clean-code.md` | `~/.claude/rules/` | Every session | How to write code: reuse first, match the neighbours, small units, plain names, few comments |
| `rules/writing.md` | `~/.claude/rules/` | Every session | How to write text: Simplified Technical English, no extra words, the PR and ticket formats |
| `at/` plugin | `~/.claude/skills/at/` | Skills on demand; hooks always | The skills below, the `at:worker` agent, and the clean-gate hooks that check every edit |

Only `/at:survey` can start on its own when Claude thinks it fits. Every other skill runs only when you type it.

## Pick the skill

```mermaid
flowchart TD
  Q{"What do you have?"}
  Q -->|"a question about the code"| EX["/at:explain"]
  Q -->|"a ticket or an ask"| BR["/at:brief"]
  Q -->|"a document to write"| RS["/at:research"]
  BR -->|"size S or M"| IM["/at:implement"]
  BR -->|"size L, or needs a decision"| IV["/at:interview"] --> SP["SPEC.md"] --> IM
  IM --> PR["draft PR"]
```

## Skills

| Skill | Use it when | Runs on | You get |
| --- | --- | --- | --- |
| `/at:brief` | You have a Linear key or a short ask and want it sized | Opus, medium | `briefs/<id>.md`, sized S, M or L |
| `/at:interview` | The ask is part of a bigger problem, or needs decisions | Opus, high | `SPEC.md` covering what the ask didn't mention |
| `/at:research` | You need a one-pager (`--one-pager`), PRD (`--prd`) or design doc (`--design`) | Opus, high | A shareable artifact |
| `/at:explain` | You want to know how something works, with `as: table \| list \| diagram \| prose \| doc` | Opus, high | An answer with file and line evidence |
| `/at:survey` | Before writing code: what exists, what to reuse, what to copy | Session model | A reuse map of up to 20 lines |
| `/at:implement` | A brief or spec is ready to build | Opus plans, Sonnet workers build | A draft PR |
| `/at:word-salad` | A reply is too dense to read | Opus, medium | The same content in plain, short, ordered prose |

## Getting the best results

- **Start from a file, not a paragraph.** Skills read a brief or spec by path. Anything bigger than a one-line change goes through `/at:brief` first, and the size it picks sets the route: S and M go to `/at:implement`, L goes to `/at:interview` or `/at:research`.
- **Let size set effort, not worry.** Raise effort only after a run fails for lack of it, one level at a time. On the 5.5 models, medium already handles most multi-step coding.
- **Survey before you build.** `/at:implement` does this for you, but for work in your own session, run `/at:survey <what you're adding>` first. On terminator, asking for a "last edited 5m ago" label showed the label already existed (`NoteList.tsx:296`) and that `relativeTime` is copied, with different output, in two other files.
- **Read gate findings like review comments.** Fix each one, or say why it's intended. Tune each repo with a `.clean-gate.json` (below).
- **Judge the PR by its first sections.** Every PR opens with "Current state" and "This PR" in three sentences or fewer each. If you can't follow them, ask for a rewrite before reading the code.
- **Done means the checks ran.** The PR carries each command and its exit code. A summary that says "tests pass" without output isn't done.
- **Too much to read?** Run `/at:word-salad` with no argument to rewrite the last reply, or pass it text or a file path.
- **One ask per session.** Start a new session between unrelated tasks, so old context doesn't steer the new one.

## The clean-code gate

The gate runs after every edit, including in agent sessions Foundry starts, since those write code too. It sends its findings back to Claude, which fixes them before carrying on.

| Check | Rule |
| --- | --- |
| Size | A new function has at most 30 lines, complexity 10 and 3 parameters |
| Ratchet | A changed function that was already over a limit may not grow; untouched code is never reported |
| Repeated name | A new function's name isn't already defined in another tracked file |
| Comment run | No added comment longer than 3 lines, except a header at line 1 |

[lizard](https://github.com/terryyin/lizard) reads functions in 26 languages. In a language lizard can't read, only the comment check runs.

An optional `.clean-gate.json` at a repo root changes the defaults for that repo:

```json
{
  "limits": { "nloc": 30, "ccn": 10, "params": 3, "commentRun": 3 },
  "ignoreNames": ["main", "__init__", "constructor", "App"],
  "ignorePaths": ["**/generated/**"]
}
```

To measure a branch, including files edited through Bash, which the edit hook does not see: `uv run --script ~/.claude/skills/at/hooks/clean-gate/gate.py report main..HEAD`

The design behind all this: https://claude.ai/artifact/17jp31c5gsQX9JQQbvgd4i

## Tests

```sh
uv run --no-project --with pytest==9.1.1 --with lizard==1.24.1 pytest -q tests
bash tests/test_install.sh
uvx ruff@0.16.10 check at tests && uvx ruff@0.16.10 format --check at tests
claude plugin validate at
shellcheck -x install.sh uninstall.sh tests/test_install.sh
```
