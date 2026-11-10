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
import sys
from pathlib import Path

REFERENCE = re.compile(r"([\w./-]+\.[\w]+|[\w./-]*/[\w.-]+):(\d+(?:[-,]\d+)*)")
QUOTE = re.compile(
    r"<code>(?P<path>[\w./-]+):(?P<spec>\d+(?:[-,]\d+)*)</code>\s*(?:→|->|says|:)?\s*"
    r"[\"“]?<code>(?P<quote>[^<]+)</code>"
)


def cited_lines(spec):
    lines = []
    for part in spec.split(","):
        start, _, end = part.partition("-")
        lines += range(int(start), int(end or start) + 1)
    return lines


def reference_problem(path, spec):
    file = Path(path)
    if not file.is_file():
        return f"{path}:{spec}  file not found"
    count = len(file.read_text(errors="replace").splitlines())
    past = [n for n in cited_lines(spec) if n > count]
    return (
        f"{path}:{spec}  line {past[0]} is past the end ({count} lines)"
        if past
        else None
    )


def quote_problem(path, spec, quote):
    """A code span right after a reference quotes the cited line, so it must be on it."""
    file = Path(path)
    if not file.is_file():
        return None
    text = file.read_text(errors="replace").splitlines()
    lines = [text[n - 1] for n in cited_lines(spec) if n <= len(text)]
    if any(quote in line for line in lines):
        return None
    return f"{path}:{spec}  `{quote}` is not on the cited lines"


def broken_references(document):
    found = [
        reference_problem(path, spec) for path, spec in REFERENCE.findall(document)
    ]
    quotes = (m.groupdict() for m in QUOTE.finditer(document))
    found += [
        quote_problem(q["path"], q["spec"], html.unescape(q["quote"])) for q in quotes
    ]
    return sorted({p for p in found if p})


def main():
    found = broken_references(Path(sys.argv[1]).read_text())
    for line in found:
        print(line)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
