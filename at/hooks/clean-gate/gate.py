#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["lizard==1.24.1"]
# [tool.uv]
# exclude-newer = "2 weeks"
# ///
import argparse
import fnmatch
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import NamedTuple

import lizard

DEFAULT_CONFIG = {
    "limits": {"nloc": 30, "ccn": 10, "params": 3, "commentRun": 3},
    "ignoreNames": ["main", "__init__", "constructor"],
    "ignorePaths": [],
}
SLASH_EXTENSIONS = [
    *("ts", "tsx", "js", "jsx", "mjs", "cjs", "go", "rs", "java", "kt", "kts"),
    *("swift", "c", "h", "cc", "cpp", "hpp", "cs", "php", "scala", "dart"),
]
HASH_EXTENSIONS = ["py", "rb", "sh", "bash", "pl", "r"]
COMMENT_PREFIXES = {
    **{ext: ("//", "/*", "*", "*/") for ext in SLASH_EXTENSIONS},
    **{ext: ("#",) for ext in HASH_EXTENSIONS},
    **{ext: ("--",) for ext in ["lua", "sql"]},
}
VERDICT = "Fix these before moving on, or say why one is intended."
HUNK = re.compile(r"^@@ -\S+ \+(\d+)(?:,(\d+))? @@", re.MULTILINE)


class Change(NamedTuple):
    path: str
    new: str
    changed: set
    old_functions: list
    new_functions: list


class Finding(NamedTuple):
    path: str
    line: int
    kind: str
    message: str


def git(root, *args):
    done = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=False
    )
    return done.stdout if done.returncode == 0 else None


def repo_root(directory):
    if not Path(directory).is_dir():
        return None
    top = git(directory, "rev-parse", "--show-toplevel")
    return Path(top.strip()).resolve() if top else None


def load_config(root):
    config = json.loads(json.dumps(DEFAULT_CONFIG))
    path = root / ".clean-gate.json"
    if path.exists():
        user = json.loads(path.read_text())
        config["limits"].update(user.get("limits", {}))
        config.update({k: v for k, v in user.items() if k != "limits"})
    return config


def functions_of(path, text):
    return lizard.analyze_file.analyze_source_code(str(path), text).function_list


def changed_lines(diff_text):
    lines = set()
    for start, count in HUNK.findall(diff_text or ""):
        lines.update(range(int(start), int(start) + int(count or 1)))
    return lines


def overlaps(function, changed):
    return any(function.start_line <= n <= function.end_line for n in changed)


def size_findings(function, limits):
    metrics = [
        (function.nloc, limits["nloc"], "lines"),
        (function.cyclomatic_complexity, limits["ccn"], "complexity"),
        (function.parameter_count, limits["params"], "parameters"),
    ]
    return [
        f"{function.name} has {value} {unit} (limit {limit})"
        for value, limit, unit in metrics
        if value > limit
    ]


def ratchet_findings(function, before, limits):
    metrics = [
        (function.nloc, before.nloc, limits["nloc"], "lines"),
        (
            function.cyclomatic_complexity,
            before.cyclomatic_complexity,
            limits["ccn"],
            "complexity",
        ),
    ]
    return [
        f"{function.name} grew from {old} to {new} {unit}; "
        f"it was already over the limit ({limit})"
        for new, old, limit, unit in metrics
        if new > old and new > limit
    ]


def function_findings(change, limits):
    old_by_name = {f.name: f for f in change.old_functions}
    found = []
    for function in change.new_functions:
        before = old_by_name.get(function.name)
        if before is None:
            messages, kind = size_findings(function, limits), "size"
        elif overlaps(function, change.changed):
            messages, kind = ratchet_findings(function, before, limits), "ratchet"
        else:
            continue
        found += [Finding(change.path, function.start_line, kind, m) for m in messages]
    return found


def short_name(name):
    return name.split("::")[-1]


def is_checkable_name(name, config):
    return (
        name not in config["ignoreNames"] and "anonymous" not in name and len(name) >= 3
    )


TEST_DIRECTORIES = {"test", "tests", "__tests__"}
TEST_FILE_PATTERNS = ["*.spec.*", "*.test.*", "test_*.py", "*_test.go"]


def is_test_path(path):
    parts = Path(path).parts
    in_test_directory = any(part in TEST_DIRECTORIES for part in parts[:-1])
    return in_test_directory or any(
        fnmatch.fnmatch(parts[-1], pattern) for pattern in TEST_FILE_PATTERNS
    )


def definitions_elsewhere(root, path, name):
    listing = git(root, "grep", "-l", "-w", name) or ""
    others = [p for p in listing.split("\n") if p and p != path and not is_test_path(p)]
    found = []
    for other in others:
        text = (root / other).read_text(errors="replace")
        found += [
            f"{other}:{f.start_line}"
            for f in functions_of(other, text)
            if short_name(f.name) == name
        ]
    return found


def repeat_finding(root, change, function):
    name = short_name(function.name)
    places = definitions_elsewhere(root, change.path, name)
    if not places:
        return None
    where = " and ".join(places[:2])
    message = (
        f"{name} is already defined at {where}. Reuse it, "
        "or move one shared version to a module both import."
    )
    return Finding(change.path, function.start_line, "repeat", message)


def repeat_findings(root, change, config):
    if is_test_path(change.path):
        return []
    old_names = {f.name for f in change.old_functions}
    new = [f for f in change.new_functions if f.name not in old_names]
    named = [f for f in new if is_checkable_name(short_name(f.name), config)]
    found = [repeat_finding(root, change, f) for f in named]
    return [f for f in found if f]


def comment_flags(path, lines):
    prefixes = COMMENT_PREFIXES.get(Path(path).suffix.lstrip("."), ())
    in_block = False
    flags = []
    for line in lines:
        quotes = line.count('"""') + line.count("'''")
        toggles = Path(path).suffix == ".py" and quotes % 2 == 1
        is_docstring = Path(path).suffix == ".py" and (quotes > 0 or in_block)
        flags.append(is_docstring or line.strip().startswith(prefixes))
        in_block = in_block != toggles
    return flags


def comment_runs(flags, changed):
    runs, current = [], []
    for number, flag in enumerate(flags, start=1):
        if flag and number in changed:
            current.append(number)
        elif current:
            runs.append(current)
            current = []
    return runs + ([current] if current else [])


def comment_finding(path, run):
    message = (
        f"{len(run)}-line comment; keep comments to constraints "
        "the code can't show, 3 lines at most"
    )
    return Finding(path, run[0], "comment", message)


def comment_findings(change, limit):
    flags = comment_flags(change.path, change.new.split("\n"))
    runs = comment_runs(flags, change.changed)
    return [
        comment_finding(change.path, r) for r in runs if len(r) > limit and r[0] != 1
    ]


def find_issues(root, change, config):
    limits = config["limits"]
    return (
        function_findings(change, limits)
        + repeat_findings(root, change, config)
        + comment_findings(change, limits["commentRun"])
    )


def is_ignored(path, config):
    return any(fnmatch.fnmatch(path, pattern) for pattern in config["ignorePaths"])


def load_change(root, path, revisions):
    old = git(root, "show", f"{revisions[0]}:{path}")
    new = content_at(root, path, revisions[1:])
    if new is None:
        return None
    diff = git(root, "diff", "-U0", *revisions, "--", path)
    changed = set(range(1, new.count("\n") + 2)) if old is None else changed_lines(diff)
    old_functions = functions_of(path, old) if old is not None else []
    return Change(path, new, changed, old_functions, functions_of(path, new))


def content_at(root, path, after):
    if after:
        return git(root, "show", f"{after[0]}:{path}")
    file = root / path
    return file.read_text(errors="replace") if file.is_file() else None


def check_file(root, path, config):
    change = None if is_ignored(path, config) else load_change(root, path, ["HEAD"])
    return find_issues(root, change, config) if change else []


def finding_line(finding):
    return f"{finding.path}:{finding.line}  {finding.message}"


def block_message(findings):
    lines = [finding_line(f) for f in findings]
    return json.dumps({"decision": "block", "reason": "\n".join(lines + [VERDICT])})


def emit(findings):
    if findings:
        print(block_message(findings))


def post_tool_use(payload):
    file = Path(payload["tool_input"]["file_path"]).resolve()
    root = repo_root(file.parent)
    if root is None or not file.is_file():
        return []
    return check_file(root, str(file.relative_to(root)), load_config(root))


def run_check():
    payload = json.loads(sys.stdin.read() or "{}")
    emit(post_tool_use(payload))


def added_lines(root, span):
    stat = git(root, "diff", "--numstat", *span.split("..")) or ""
    return sum(
        int(row.split("\t")[0])
        for row in stat.splitlines()
        if row.split("\t")[0].isdigit()
    )


def report_findings(root, span, config):
    before, after = span.split("..")
    names = (git(root, "diff", "--name-only", before, after) or "").split()
    changes = [
        load_change(root, n, [before, after])
        for n in names
        if not is_ignored(n, config)
    ]
    return [f for c in changes if c for f in find_issues(root, c, config)]


def run_report(span):
    root = repo_root(Path.cwd())
    found = report_findings(root, span, load_config(root))
    counts = Counter(f.kind for f in found)
    for f in found:
        print(finding_line(f))
    print(f"functions over a limit: {counts['size']}")
    print(f"ratchet breaches: {counts['ratchet']}")
    print(f"repeated names: {counts['repeat']}")
    print(f"long comment runs: {counts['comment']}")
    print(f"added lines: {added_lines(root, span)}")


def parse_args():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check")
    check.add_argument("--hook", choices=["post-tool-use", "stop"], required=True)
    commands.add_parser("report").add_argument("span")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.command == "check":
        # "stop" is accepted for sessions still running a pre-reinstall Stop hook.
        if args.hook == "post-tool-use":
            run_check()
    else:
        run_report(args.span)


if __name__ == "__main__":
    main()
