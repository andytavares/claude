#!/bin/sh
# Installs skill set two by copying: /brief /research /explain /interview /do-work,
# plus the worker subagent /do-work delegates to. Re-run after editing here.
#
# /brief, /research and /interview share names with set one. Whichever installer
# ran last owns those three; re-run the other to switch back.
set -eu
SET="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$HOME/.claude/skills" "$HOME/.claude/agents"
for skill in "$SET"/skills/*/; do
  name="$(basename "$skill")"
  rm -rf "$HOME/.claude/skills/$name"
  cp -R "$skill" "$HOME/.claude/skills/$name"
done
rm -f "$HOME/.claude/agents/worker.md"
cp "$SET/agents/worker.md" "$HOME/.claude/agents/worker.md"

echo "skills:  $(ls "$HOME/.claude/skills" | tr '\n' ' ')"
echo "agents:  $(ls "$HOME/.claude/agents" | tr '\n' ' ')"
echo "set two owns /brief /research /interview until ../install.sh runs again"