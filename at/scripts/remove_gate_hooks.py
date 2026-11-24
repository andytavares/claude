#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Remove the clean-gate and harness hooks that earlier installs wrote into settings.json."""

import json
import sys

RETIRED = (".claude/hooks/clean-gate/gate.py", ".claude/harness/hooks/")


def is_gate(entry):
    return any(
        retired in hook.get("command", "")
        for hook in entry.get("hooks", [])
        for retired in RETIRED
    )


def main(path):
    with open(path) as handle:
        data = json.load(handle)
    hooks = data.get("hooks", {})
    for event in list(hooks):
        hooks[event] = [entry for entry in hooks[event] if not is_gate(entry)]
        if not hooks[event]:
            del hooks[event]
    with open(path, "w") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")


if __name__ == "__main__":
    main(sys.argv[1])
