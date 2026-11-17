"""Line numbers a unified diff adds. Shared by the clean-code gate and the harness."""

import re

HUNK = re.compile(r"^@@ -\S+ \+(\d+)(?:,(\d+))? @@", re.MULTILINE)


def changed_lines(diff_text):
    lines = set()
    for start, count in HUNK.findall(diff_text or ""):
        lines.update(range(int(start), int(start) + int(count or 1)))
    return lines
