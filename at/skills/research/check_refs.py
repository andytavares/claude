#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Check every path:line reference in a document against the repo it was written from.

Run it from the repo root. Exit 1 and print one line per broken reference.
"""

import html
import re
import subprocess
import sys
from pathlib import Path

# A reference is a code span, in HTML or Markdown, that holds only path:lines.
SPAN = r"(?:<code>|`)"
END = r"(?:</code>|`)"
PATH = r"(?P<path>~?[\w.-]*(?:/[\w.-]+)*\.\w+|~?[\w.-]*(?:/[\w.-]+)+)"
LINES = r"(?P<spec>\d+(?:[-,]\d+)*)"
REFERENCE = re.compile(SPAN + PATH + ":" + LINES + END)
QUOTE = re.compile(
    SPAN + PATH + ":" + LINES + END + r"\s*(?:→|->|says|:)?\s*[\"“]?"
    r"(?:<code>|`)(?P<quote>[^<`]+)(?:</code>|`)"
)


def repo_files():
    done = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, check=False
    )
    return done.stdout.split()


def bare_name_problem(path, spec, files):
    """A name with no directory is a reference only when the repo has a file by that name."""
    matches = [f for f in files if Path(f).name == path]
    if not matches or path in files:
        return None
    return f"{path}:{spec}  give the path: {', '.join(matches)}"


def cited_lines(spec):
    lines = []
    for part in spec.split(","):
        start, _, end = part.partition("-")
        lines += range(int(start), int(end or start) + 1)
    return lines


def reference_problem(path, spec, files):
    if "/" not in path:
        found = bare_name_problem(path, spec, files)
        if found or path not in files:
            return found
    file = Path(path).expanduser()
    if not file.is_file():
        return f"{path}:{spec}  file not found"
    count = len(file.read_text(errors="replace").splitlines())
    past = [n for n in cited_lines(spec) if n > count]
    if not past:
        return None
    return f"{path}:{spec}  line {past[0]} is past the end ({count} lines)"


def quote_problem(path, spec, quote):
    """A code span right after a reference quotes the cited line, so it must be on it."""
    file = Path(path).expanduser()
    if not file.is_file():
        return None
    text = file.read_text(errors="replace").splitlines()
    lines = [text[n - 1] for n in cited_lines(spec) if n <= len(text)]
    if any(quote in line for line in lines):
        return None
    return f"{path}:{spec}  `{quote}` is not on the cited lines"


def broken_references(document):
    files = repo_files()
    refs = REFERENCE.finditer(document)
    found = [reference_problem(m["path"], m["spec"], files) for m in refs]
    quotes = QUOTE.finditer(document)
    found += [
        quote_problem(m["path"], m["spec"], html.unescape(m["quote"])) for m in quotes
    ]
    return sorted({p for p in found if p})


def main():
    found = broken_references(Path(sys.argv[1]).read_text())
    for line in found:
        print(line)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
