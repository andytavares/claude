#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Quality gates for Claude Code hooks. Knows no language, tool or layout.

Everything repo-specific comes from harness.toml in the repo's data directory
(at/skills/glossary/path.sh). A check without the settings it needs reports
"not measured" to the user and never guesses.
"""

import difflib
import fnmatch
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))
import tomllib
from hunks import changed_lines

PLUGIN = Path(__file__).resolve().parents[2]
STYLE = Path(__file__).with_name("vale.ini")
JSCPD = "jscpd@5.4.3"
MUTATOR = "universalmutator==1.14.1"
VALE = "vale==3.27.0.0"
SHOWN = 5


def sh(command, **options):
    try:
        return subprocess.run(
            command, capture_output=True, text=True, check=False, **options
        )
    except FileNotFoundError as missing:
        return subprocess.CompletedProcess(
            command, 127, "", f"not found: {missing.filename}"
        )


WARNINGS = []


def warn(message):
    WARNINGS.append(f"harness: {message}")


def block(message):
    print(message, file=sys.stderr)
    sys.exit(2)


def config():
    found = sh(["bash", str(PLUGIN / "skills/glossary/path.sh")])
    path = Path(found.stdout.strip()) / "harness.toml"
    return (tomllib.loads(path.read_text()) if path.is_file() else {}), path


def base_ref(settings):
    if settings.get("base"):
        return settings["base"]
    found = sh(["bash", str(PLUGIN / "scripts/default-branch.sh")])
    return found.stdout.split()[1] if found.returncode == 0 else None


def is_text(path):
    with open(path, "rb") as handle:
        return b"\0" not in handle.read(8192)


def changed_files(base):
    tracked = sh(["git", "diff", "--name-only", "--diff-filter=AM", base]).stdout.split(
        "\n"
    )
    untracked = sh(["git", "ls-files", "--others", "--exclude-standard"]).stdout.split(
        "\n"
    )
    return [
        path
        for path in tracked + untracked
        if path and Path(path).is_file() and is_text(path)
    ]


def matches(path, globs):
    return any(fnmatch.fnmatch(path, glob) for glob in globs)


# rules: PreToolUse. A rule is a regex on text a tool is about to write.
def rules(call, settings, _path):
    args = call.get("tool_input", {})
    target = args.get("file_path") or args.get("notebook_path") or ""
    text = args.get("new_string") or args.get("content") or args.get("new_source") or ""
    for rule in settings.get("rule", []):
        if matches(target, rule.get("globs", ["*"])) and re.search(
            rule["pattern"], text, re.MULTILINE
        ):
            block(f"[{rule['name']}] {rule['message']}")


# copies: Stop. jscpd reports clones the branch adds, in any format it reads.
def copies(call, settings, path):
    base = base_ref(settings)
    if not base:
        return warn(f"copies not measured: no base branch. Set base in {path}")
    found = sh(
        [
            "npx",
            "-y",
            JSCPD,
            ".",
            "--baseline-from-ref",
            base,
            "--fail-on-new-clones",
            "-r",
            "ai",
            "--no-tips",
            "--min-tokens",
            str(settings.get("min_tokens", 30)),
            "--min-lines",
            str(settings.get("min_lines", 4)),
        ]
    )
    if found.returncode == 0:
        return None
    if "new clones" not in found.stdout + found.stderr:
        return warn(f"copies not measured: jscpd failed: {found.stderr.strip()[:200]}")
    block(
        "This branch adds copied code. Reuse or extract one version:\n"
        + re.sub(r"\x1b\[[0-9;]*m", "", found.stdout)
    )


def added_line_numbers(base, path):
    if sh(["git", "ls-files", "--error-unmatch", path]).returncode != 0:
        return list(
            range(1, len(Path(path).read_text(errors="replace").splitlines()) + 1)
        )
    return sorted(changed_lines(sh(["git", "diff", "-U0", base, "--", path]).stdout))


def ignored_files(patterns):
    """Ignored files that match `copy_ignored` patterns (gitignore syntax), such as a local env file."""
    if not patterns:
        return []
    excludes = [f"--exclude={pattern}" for pattern in patterns]
    found = sh(["git", "ls-files", "--others", "--ignored", *excludes])
    return [path for path in found.stdout.split("\n") if path and Path(path).is_file()]


def snapshot(base, settings):
    """A private worktree of the current tree, so mutants never touch files other hooks read."""
    copy = Path(tempfile.mkdtemp(prefix="harness-tree-")) / "tree"
    sh(["git", "worktree", "add", "--detach", "--quiet", str(copy), "HEAD"])
    for path in changed_files(base) + ignored_files(settings.get("copy_ignored", [])):
        (copy / path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, copy / path)
    return copy


def drop(copy):
    sh(["git", "worktree", "remove", "--force", str(copy)])
    shutil.rmtree(copy.parent, ignore_errors=True)


def uvx(package, *args, **options):
    return sh(["uvx", "--from", package, *map(str, args)], **options)


def mutate(path, work):
    flags = [
        "--noCheck",
        "--lines",
        work / "lines.txt",
        "--ignore",
        work / "ignore.txt",
    ]
    made = uvx(MUTATOR, "mutate", path, *flags, "--mutantDir", work)
    return made.returncode == 0 and len(list(work.glob("*mutant*"))) > 0


def passing(path, test, work):
    uvx(
        MUTATOR,
        "analyze_mutants",
        path,
        test,
        "--mutantDir",
        work,
        "--prefix",
        work / "run",
    )
    survived = work / "run.notkilled.txt"
    if not survived.is_file():
        return None
    names = survived.read_text().split()
    return [(work / name).read_text(errors="replace") for name in names]


def survivors(path, lines, settings):
    """Mutants of `path` that pass the test command, or None when none could be made or run."""
    work = Path(tempfile.mkdtemp(prefix="harness-"))
    (work / "lines.txt").write_text("\n".join(map(str, lines)))
    (work / "ignore.txt").write_text("\n".join(settings.get("mutation_ignore", [])))
    original = Path(path).read_bytes()
    try:
        return passing(path, settings["test"], work) if mutate(path, work) else None
    finally:
        Path(path).write_bytes(original)
        shutil.rmtree(work, ignore_errors=True)


def mutation_targets(base, settings):
    for source in changed_files(base):
        if not matches(source, settings["tests"] + settings.get("skip", [])):
            lines = added_line_numbers(base, source)
            if lines:
                yield source, lines


def survivor_report(found, test):
    report = [
        f"{len(found)} planted bugs passed `{test}`. Add a test that fails for each, or say why the mutant is equivalent:"
    ]
    for source, mutant in found[:SHOWN]:
        original = Path(source).read_text(errors="replace").splitlines()
        report += difflib.unified_diff(
            original, mutant.splitlines(), source, "mutant", n=0, lineterm=""
        )
    return "\n".join(report)


# can-fail: Stop. Plant bugs on the lines the branch added and run the repo's own test command.
def unready(settings, path):
    if not (settings.get("test") and settings.get("tests")):
        return f"can-fail not measured: set test and tests in {path}"
    if sh(settings["test"], shell=True).returncode != 0:
        return f"can-fail not measured: `{settings['test']}` fails in a fresh worktree. Add the ignored files it needs to copy_ignored in {path}"
    return None


def can_fail(call, settings, path):
    base = base_ref(settings)
    if not base:
        return warn(f"can-fail not measured: no base branch. Set base in {path}")
    copy = snapshot(base, settings)
    home = os.getcwd()
    try:
        os.chdir(copy)
        mutate_and_report(base, settings, path)
    finally:
        os.chdir(home)
        drop(copy)


def mutate_and_report(base, settings, path):
    problem = unready(settings, path)
    if problem:
        return warn(problem)
    found, unmeasured = [], []
    for source, lines in mutation_targets(base, settings):
        mutants = survivors(source, lines, settings)
        unmeasured += [source] if mutants is None else []
        found += [(source, mutant) for mutant in mutants or []]
    if unmeasured:
        warn("can-fail not measured for: " + ", ".join(unmeasured))
    if found:
        block(survivor_report(found, settings["test"]))


# prose: text a person will read. Long strings in any tool's input, and the final reply.
def strings_in(value):
    if isinstance(value, dict):
        return [text for item in value.values() for text in strings_in(item)]
    if isinstance(value, list):
        return [text for item in value for text in strings_in(item)]
    return [value] if isinstance(value, str) else []


def pieces_of(text):
    """A string, plus its heredoc bodies or shell words, so prose inside a command is found."""
    heredocs = [
        body
        for _, body in re.findall(
            r"<<-?\s*['\"]?(\w+)['\"]?\n(.*?)\n\1", text, re.DOTALL
        )
    ]
    if heredocs:
        return heredocs
    try:
        return [text, *shlex.split(text)]
    except ValueError:
        return [text]


def prose_in(value, minimum):
    pieces = [piece for text in strings_in(value) for piece in pieces_of(text)]
    return [
        piece for piece in pieces if len(re.findall(r"[^\W\d_]{2,}", piece)) >= minimum
    ]


EDIT_TOOLS = ["Write", "Edit", "MultiEdit", "NotebookEdit"]


def texts_to_check(call, settings):
    if call.get("hook_event_name") == "Stop":
        wanted = settings.get("check_replies")
        return [call.get("last_assistant_message", "")] if wanted else []
    if call.get("tool_name") in settings.get("prose_skip_tools", EDIT_TOOLS):
        return []
    return prose_in(call.get("tool_input", {}), settings.get("prose_min_words", 25))


def prose(call, settings, path):
    style = Path(settings.get("vale_config", STYLE)).expanduser()
    for text in texts_to_check(call, settings):
        found = uvx(
            VALE, "vale", "--config", style, "--ext=.md", "--output=line", input=text
        )
        if found.returncode not in (0, 1):
            return warn(
                f"prose not measured: vale failed: {found.stderr.strip()[:200]}"
            )
        if found.stdout.strip():
            lines = found.stdout.replace("stdin.md:", "line ")
            block("Rewrite this text. It fails the plain-prose check:\n" + lines)


CHECKS = {"rules": rules, "copies": copies, "can-fail": can_fail, "prose": prose}


def main():
    call = json.load(sys.stdin)
    if call.get("stop_hook_active"):
        return
    if sh(["git", "rev-parse", "--is-inside-work-tree"]).returncode != 0:
        return print(
            json.dumps(
                {
                    "systemMessage": f"harness: {sys.argv[1]} not measured: not a git repo"
                }
            )
        )
    settings, path = config()
    try:
        CHECKS[sys.argv[1]](call, settings, path)
    finally:
        if WARNINGS:
            print(json.dumps({"systemMessage": "\n".join(WARNINGS)}))


if __name__ == "__main__":
    main()
