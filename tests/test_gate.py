import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

GATE = Path(__file__).parent.parent / "hooks/clean-gate/gate.py"

LANGS = {
    "ts": ("ts", "function {name}(a) {{\n{body}  return a;\n}}\n", "  a += 1;\n"),
    "py": ("py", "def {name}(a):\n{body}    return a\n", "    a += 1\n"),
    "go": ("go", "func {name}(a int) int {{\n{body}  return a\n}}\n", "  a += 1\n"),
}
COMMENT = {"ts": "// note", "py": "# note", "go": "// note"}


def func(lang, name, lines):
    _, template, line = LANGS[lang]
    return template.format(name=name, body=line * lines)


def git(repo, *args):
    done = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    )
    return done.stdout


def make_repo(tmp_path, files):
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.name", "t")
    git(tmp_path, "config", "user.email", "t@t")
    write(tmp_path, files)
    commit(tmp_path)
    return tmp_path


def write(repo, files):
    for name, text in files.items():
        (repo / name).write_text(text)


def commit(repo):
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "c")


def run_gate(cwd, stdin, *args):
    return subprocess.run(
        [sys.executable, str(GATE), *args],
        cwd=cwd,
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    )


def check_file(repo, name):
    hook = json.dumps({"tool_input": {"file_path": str(repo / name)}})
    done = run_gate(repo, hook, "check", "--hook", "post-tool-use")
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)["reason"] if done.stdout else ""


@pytest.mark.parametrize("lang", LANGS)
def test_new_function_over_limit_is_flagged(tmp_path, lang):
    ext = LANGS[lang][0]
    repo = make_repo(tmp_path, {f"base.{ext}": func(lang, "base", 2)})
    write(repo, {f"a.{ext}": func(lang, "relativeTime", 40)})
    assert "relativeTime has" in check_file(repo, f"a.{ext}")
    assert "(limit 30)" in check_file(repo, f"a.{ext}")


@pytest.mark.parametrize("lang", LANGS)
def test_new_function_under_limit_is_clean(tmp_path, lang):
    ext = LANGS[lang][0]
    repo = make_repo(tmp_path, {f"base.{ext}": func(lang, "base", 2)})
    write(repo, {f"a.{ext}": func(lang, "relativeTime", 10)})
    assert check_file(repo, f"a.{ext}") == ""


@pytest.mark.parametrize("lang", LANGS)
def test_untouched_legacy_function_is_not_flagged(tmp_path, lang):
    ext = LANGS[lang][0]
    legacy = func(lang, "legacyBig", 50) + "\n" + func(lang, "small", 2)
    repo = make_repo(tmp_path, {f"a.{ext}": legacy})
    write(repo, {f"a.{ext}": legacy.replace("small", "smaller")})
    assert check_file(repo, f"a.{ext}") == ""


@pytest.mark.parametrize("lang", LANGS)
def test_legacy_function_that_grows_is_flagged(tmp_path, lang):
    ext = LANGS[lang][0]
    repo = make_repo(tmp_path, {f"a.{ext}": func(lang, "legacyBig", 50)})
    write(repo, {f"a.{ext}": func(lang, "legacyBig", 58)})
    reason = check_file(repo, f"a.{ext}")
    old, new = re.search(r"legacyBig grew from (\d+) to (\d+) lines", reason).groups()
    assert int(new) - int(old) == 8
    assert "already over the limit (30)" in reason


@pytest.mark.parametrize("lang", LANGS)
def test_legacy_function_edited_without_growing_is_clean(tmp_path, lang):
    ext = LANGS[lang][0]
    repo = make_repo(tmp_path, {f"a.{ext}": func(lang, "legacyBig", 50)})
    edited = func(lang, "legacyBig", 50).replace("a += 1", "a += 2", 1)
    write(repo, {f"a.{ext}": edited})
    assert check_file(repo, f"a.{ext}") == ""


@pytest.mark.parametrize("lang", LANGS)
def test_repeated_name_points_at_the_other_file(tmp_path, lang):
    ext = LANGS[lang][0]
    repo = make_repo(tmp_path, {f"one.{ext}": func(lang, "formatTotal", 3)})
    write(repo, {f"two.{ext}": func(lang, "formatTotal", 3)})
    reason = check_file(repo, f"two.{ext}")
    assert f"formatTotal is already defined at one.{ext}:1" in reason
    assert "Reuse it" in reason


def test_ignored_name_is_not_a_repeat(tmp_path):
    repo = make_repo(tmp_path, {"one.ts": func("ts", "formatTotal", 3)})
    config = {"ignoreNames": ["formatTotal"]}
    write(repo, {"two.ts": func("ts", "formatTotal", 3)})
    write(repo, {".clean-gate.json": json.dumps(config)})
    assert check_file(repo, "two.ts") == ""


def test_ignored_path_is_skipped(tmp_path):
    repo = make_repo(tmp_path, {"base.ts": func("ts", "base", 2)})
    write(repo, {".clean-gate.json": json.dumps({"ignorePaths": ["gen/*"]})})
    (repo / "gen").mkdir()
    write(repo, {"gen/big.ts": func("ts", "huge", 50)})
    assert check_file(repo, "gen/big.ts") == ""


def comments(lang, count):
    return "".join(f"{COMMENT[lang]} line {i}\n" for i in range(count))


@pytest.mark.parametrize("lang", LANGS)
def test_five_line_comment_run_is_flagged(tmp_path, lang):
    ext = LANGS[lang][0]
    base = func(lang, "base", 2)
    repo = make_repo(tmp_path, {f"a.{ext}": base})
    write(repo, {f"a.{ext}": base + comments(lang, 5)})
    assert "5-line comment" in check_file(repo, f"a.{ext}")


@pytest.mark.parametrize("lang", LANGS)
def test_two_line_comment_run_is_clean(tmp_path, lang):
    ext = LANGS[lang][0]
    base = func(lang, "base", 2)
    repo = make_repo(tmp_path, {f"a.{ext}": base})
    write(repo, {f"a.{ext}": base + comments(lang, 2)})
    assert check_file(repo, f"a.{ext}") == ""


@pytest.mark.parametrize("lang", LANGS)
def test_comment_run_at_line_one_is_a_header(tmp_path, lang):
    ext = LANGS[lang][0]
    base = func(lang, "base", 2)
    repo = make_repo(tmp_path, {f"a.{ext}": base})
    write(repo, {f"a.{ext}": comments(lang, 5) + base})
    assert check_file(repo, f"a.{ext}") == ""


def test_python_docstring_run_is_flagged(tmp_path):
    base = func("py", "base", 2)
    repo = make_repo(tmp_path, {"a.py": base})
    doc = '"""\none\ntwo\nthree\n"""\n'
    write(repo, {"a.py": base + doc})
    assert "5-line comment" in check_file(repo, "a.py")


def test_post_tool_use_block_names_the_path(tmp_path):
    repo = make_repo(tmp_path, {"base.ts": func("ts", "base", 2)})
    write(repo, {"a.ts": func("ts", "relativeTime", 40)})
    hook = json.dumps({"tool_input": {"file_path": str(repo / "a.ts")}})
    done = run_gate(repo, hook, "check", "--hook", "post-tool-use")
    out = json.loads(done.stdout)
    assert done.returncode == 0
    assert out["decision"] == "block"
    assert "a.ts:1  relativeTime has" in out["reason"]
    assert out["reason"].endswith(
        "Fix these before moving on, or say why one is intended."
    )


def test_stop_hook_is_silent_when_already_active(tmp_path):
    repo = make_repo(tmp_path, {"base.ts": func("ts", "base", 2)})
    write(repo, {"a.ts": func("ts", "relativeTime", 40)})
    hook = json.dumps({"stop_hook_active": True})
    done = run_gate(repo, hook, "check", "--hook", "stop")
    assert (done.returncode, done.stdout) == (0, "")


def test_stop_hook_finds_untracked_file(tmp_path):
    repo = make_repo(tmp_path, {"base.ts": func("ts", "base", 2)})
    write(repo, {"a.ts": func("ts", "relativeTime", 40)})
    done = run_gate(repo, json.dumps({}), "check", "--hook", "stop")
    assert done.returncode == 0
    assert "a.ts:1  relativeTime has" in json.loads(done.stdout)["reason"]


def test_report_counts_a_two_commit_range(tmp_path):
    repo = make_repo(tmp_path, {"a.ts": func("ts", "legacyBig", 50)})
    write(repo, {"a.ts": func("ts", "legacyBig", 58) + func("ts", "fresh", 40)})
    write(repo, {"b.ts": comments("ts", 5) + func("ts", "bee", 2)})
    commit(repo)
    done = run_gate(repo, "", "report", "HEAD~1..HEAD")
    assert done.returncode == 0
    assert "functions over a limit: 1" in done.stdout
    assert "ratchet breaches: 1" in done.stdout
    assert "added lines:" in done.stdout


def test_file_outside_a_git_repo_is_ignored(tmp_path):
    (tmp_path / "a.ts").write_text(func("ts", "relativeTime", 40))
    hook = json.dumps({"tool_input": {"file_path": str(tmp_path / "a.ts")}})
    done = run_gate(tmp_path, hook, "check", "--hook", "post-tool-use")
    assert (done.returncode, done.stdout) == (0, "")
