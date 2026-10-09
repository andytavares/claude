# shellcheck shell=bash
# Sourced by install.sh and uninstall.sh.

remove_radar_from_plugin() {
  local plugin="$1"
  rm -rf "$plugin/skills/radar" "$plugin/radar" "$plugin/bin/radar"
  [ -f "$plugin/hooks/hooks.json" ] || return 0
  python3 - "$plugin/hooks/hooks.json" << 'PY'
import json, sys
path = sys.argv[1]
def is_radar(entry):
    return any("bin/radar" in h.get("command", "") for h in entry.get("hooks", []))
data = json.load(open(path))
hooks = data.get("hooks", {})
for event in list(hooks):
    hooks[event] = [e for e in hooks[event] if not is_radar(e)]
    if not hooks[event]:
        del hooks[event]
json.dump(data, open(path, "w"), indent=2)
open(path, "a").write("\n")
PY
}
