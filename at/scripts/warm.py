#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Download the plugin's Node through its uv. run.sh has already fetched uv and Python to start this."""

import os
import subprocess
import sys

done = subprocess.run(
    [
        os.environ["AT_UV"],
        "tool",
        "run",
        "--from",
        os.environ["AT_NODE_PACKAGE"],
        "node",
        "--version",
    ],
    capture_output=True,
    text=True,
    check=False,
)
print(
    f"plugin runtime ready: Python {sys.version.split()[0]}, Node {done.stdout.strip()}"
)
sys.exit(done.returncode)
