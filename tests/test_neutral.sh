#!/usr/bin/env bash
# Fails when harness text names a tool, a repo or a host outside rules/environment.md.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

NAMES='Linear|Context7|codegraph|`bk`|PagerDuty|incident\.io|gh pr|with `gh`|origin/HEAD|AskUserQuestion|Artifact tool|claude artifact|artifact-design|LSP|(^|[^-])(~|\$HOME)/\.claude|model: opus|src/ipc|relativeTime'
PLACES=(global rules at/skills at/agents README.md)
ALLOWED=(':!rules/environment.md')
RUNNER_NAMES='Playwright|Testing Library|typescript-eslint|toBeDefined|page\.clock|fireEvent|user-event'

hits="$(git grep -n -E "$NAMES" -- "${PLACES[@]}" "${ALLOWED[@]}" || true)"
hits+=$'\n'"$(git grep -n -E "$RUNNER_NAMES" -- "${PLACES[@]}" "${ALLOWED[@]}" ':!at/skills/tests/references' || true)"

hits="$(grep . <<< "$hits" || true)"
if [ -n "$hits" ]; then
  echo "$hits"
  echo "FAIL: name a capability from rules/environment.md instead of a tool, repo or host."
  exit 1
fi
echo "All neutrality checks passed."
