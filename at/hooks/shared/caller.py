"""Run a shell command with the environment the hook was started with, before run.sh cleared it.

Usage: python caller.py <command>
"""

import base64
import os
import sys


def caller_env():
    encoded = os.environ.get("AT_CALLER_ENV")
    if not encoded:
        return dict(os.environ)
    pairs = base64.b64decode(encoded).split(b"\0")
    return dict(
        pair.decode(errors="replace").split("=", 1) for pair in pairs if b"=" in pair
    )


if __name__ == "__main__":
    os.execvpe("sh", ["sh", "-c", sys.argv[1]], caller_env())
