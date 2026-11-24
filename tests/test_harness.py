import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

HARNESS = Path(__file__).parent.parent / "at/hooks/harness/harness.py"
spec = importlib.util.spec_from_file_location("harness", HARNESS)
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)

WORDY = (
    "In order to comprehensively address the underlying architectural considerations "
    "that you raised, it is worth noting that the implementation leverages a robust, "
    "holistic abstraction layer which seamlessly encapsulates the persistence semantics."
)
SOURCE = "def total(prices, discount):\n    subtotal = sum(prices)\n    if subtotal > 100:\n        return subtotal - discount\n    return subtotal\n"
WEAK = "from pricing import total\nassert total([10, 20], 5) is not None\n"
STRONG = "from pricing import total\nassert total([60, 40], 5) == 100\nassert total([61, 40], 5) == 96\nassert total([], 5) == 0\n"


def git(repo, *args):
    done = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    )
    return done.stdout


def make_repo(tmp_path):
    remote, repo = tmp_path / "remote.git", tmp_path / "repo"
    git(tmp_path, "init", "-q", "--bare", "-b", "trunk", str(remote))
    repo.mkdir()
    git(repo, "init", "-q", "-b", "trunk")
    git(repo, "remote", "add", "upstream", str(remote))
    (repo / "README.md").write_text("# repo\n")
    git(repo, "add", "-A")
    git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base")
    git(repo, "push", "-q", "upstream", "trunk")
    git(repo, "remote", "set-head", "upstream", "-a")
    git(repo, "checkout", "-q", "-b", "feature")
    return repo


def configure(home, repo, text):
    found = subprocess.run(
        ["bash", str(harness.PLUGIN / "skills/glossary/path.sh")],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "HOME": str(home)},
    )
    directory = Path(found.stdout.strip())
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "harness.toml").write_text(text)


def run(check, repo, call):
    home = repo.parent
    env = {**os.environ, "HOME": str(home)}
    return subprocess.run(
        [sys.executable, str(HARNESS), check],
        cwd=repo,
        input=json.dumps(call),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_prose_in_finds_heredoc_body_and_ignores_short_text():
    command = f"tool create --body \"$(cat <<'EOF'\n{WORDY}\nEOF\n)\""
    assert harness.prose_in({"command": command}, 25) == [WORDY]
    assert harness.prose_in({"title": "Fix cache"}, 25) == []


def test_prose_in_finds_quoted_argument_in_any_command():
    assert WORDY in harness.prose_in(
        {"command": f"git commit -m {json.dumps(WORDY)}"}, 25
    )


def test_prose_in_ignores_a_long_shell_command_with_no_quoted_prose():
    command = (
        "cd /repo && git pull -q; git ls-files | head -100; echo ---; "
        "grep -n 'requires-python' at/hooks/*/*.py at/skills/*/*.py; "
        "uv --version; which -a python3; python3 --version; ls ~/.local/share/uv/python"
    )
    assert harness.prose_in({"command": command}, 25) == []


def test_prose_in_ignores_a_quoted_jq_filter():
    command = (
        'bk api "/builds/$b" | jq -r \'.web_url, (.jobs[] | select(.type=="script" '
        'and .state=="failed" and .soft_failed==false and .retried==false) '
        '| "\\(.step_key) \\(.name) \\(.state) \\(.exit_status) \\(.agent.name) '
        "\\(.started_at) \\(.finished_at) \\(.web_url) \\(.log_url) \\(.id)\")'"
    )
    assert harness.prose_in({"command": command}, 25) == []


def test_prose_in_ignores_a_python_heredoc():
    script = (
        "from pathlib import Path\n"
        'path = Path("tests/test_harness.py")\n'
        "text = path.read_text()\n"
        'anchor = "def test_prose_in_ignores_a_shell_command_it_cannot_parse():"\n'
        "path.write_text(text.replace(anchor, new_tests + anchor))\n"
        "print(len(text), len(new_tests), path.name, anchor.split()[1])\n"
    )
    command = f"python3 - <<'EOF'\n{script}EOF"
    assert harness.prose_in({"command": command}, 25) == []


def test_prose_in_still_checks_prose_with_markdown_links():
    body = f"{WORDY} See [the gate](https://example.com/gate) and [the test](https://example.com/test)."
    assert harness.prose_in(
        {"command": f"gh pr create --body {json.dumps(body)}"}, 25
    ) == [body]


def test_prose_in_ignores_a_shell_command_it_cannot_parse():
    assert harness.prose_in({"command": "echo 'unclosed " + WORDY}, 25) == []


def test_prose_in_checks_the_whole_text_of_a_prompt():
    assert harness.prose_in({"prompt": WORDY}, 25) == [WORDY]


def test_prose_skips_web_fetch_prompts():
    call = {"tool_name": "WebFetch", "tool_input": {"prompt": WORDY}}
    assert harness.texts_to_check(call, {}) == []


def test_rules_block_matching_edit(tmp_path):
    repo = make_repo(tmp_path)
    configure(
        tmp_path,
        repo,
        '[[rule]]\nname = "no-sleep"\nglobs = ["*_spec.*"]\npattern = "sleep"\nmessage = "Wait on a condition."\n',
    )
    call = {
        "tool_name": "Edit",
        "tool_input": {"file_path": str(repo / "a_spec.rb"), "new_string": "sleep 1\n"},
    }
    done = run("rules", repo, call)
    assert (done.returncode, done.stderr.strip()) == (
        2,
        "[no-sleep] Wait on a condition.",
    )


def test_rules_ignore_files_outside_globs(tmp_path):
    repo = make_repo(tmp_path)
    configure(
        tmp_path,
        repo,
        '[[rule]]\nname = "no-sleep"\nglobs = ["*_spec.*"]\npattern = "sleep"\nmessage = "m"\n',
    )
    call = {
        "tool_name": "Edit",
        "tool_input": {"file_path": str(repo / "worker.rb"), "new_string": "sleep 1\n"},
    }
    assert run("rules", repo, call).returncode == 0


def test_can_fail_reports_not_measured_without_settings(tmp_path):
    repo = make_repo(tmp_path)
    done = run("can-fail", repo, {"hook_event_name": "Stop"})
    assert done.returncode == 0
    assert (
        "can-fail not measured: set test and tests"
        in json.loads(done.stdout)["systemMessage"]
    )


def test_can_fail_reports_not_measured_when_tests_fail_on_current_code(tmp_path):
    repo = make_repo(tmp_path)
    configure(tmp_path, repo, 'test = "false"\ntests = ["checks/*"]\n')
    done = run("can-fail", repo, {"hook_event_name": "Stop"})
    assert "fails in a fresh worktree" in json.loads(done.stdout)["systemMessage"]


def test_can_fail_blocks_weak_test_and_leaves_tree_unchanged(tmp_path):
    repo = make_repo(tmp_path)
    configure(
        tmp_path,
        repo,
        'test = "python3 checks/pricing_check.py"\ntests = ["checks/*"]\n',
    )
    (repo / "checks").mkdir()
    (repo / "pricing.py").write_text(SOURCE)
    (repo / "checks/pricing_check.py").write_text(
        "import sys; sys.path.insert(0, '.')\n" + WEAK
    )
    done = run("can-fail", repo, {"hook_event_name": "Stop"})
    assert done.returncode == 2
    assert "planted bugs passed" in done.stderr
    assert (repo / "pricing.py").read_text() == SOURCE
    assert git(repo, "worktree", "list").count("\n") == 1


def test_can_fail_passes_boundary_tests(tmp_path):
    repo = make_repo(tmp_path)
    configure(
        tmp_path,
        repo,
        'test = "python3 checks/pricing_check.py"\ntests = ["checks/*"]\n',
    )
    (repo / "checks").mkdir()
    (repo / "pricing.py").write_text(SOURCE)
    (repo / "checks/pricing_check.py").write_text(
        "import sys; sys.path.insert(0, '.')\n" + STRONG
    )
    assert run("can-fail", repo, {"hook_event_name": "Stop"}).returncode == 0


def test_every_check_skips_a_repeat_stop(tmp_path):
    repo = make_repo(tmp_path)
    for check in ("copies", "can-fail", "prose"):
        assert (
            run(
                check,
                repo,
                {"hook_event_name": "Stop", "stop_hook_active": True},
            ).stdout
            == ""
        )


def test_copies_reports_not_measured_without_npx(tmp_path):
    repo = make_repo(tmp_path)
    env = {"HOME": str(tmp_path), "PATH": "/usr/bin:/bin"}
    call = json.dumps({"hook_event_name": "Stop"})
    done = subprocess.run(
        [sys.executable, str(HARNESS), "copies"],
        cwd=repo,
        input=call,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert done.returncode == 0
    assert (
        "copies not measured: jscpd failed: not found: npx"
        in json.loads(done.stdout)["systemMessage"]
    )


def test_can_fail_copies_ignored_files_the_tests_need(tmp_path):
    repo = make_repo(tmp_path)
    configure(
        tmp_path,
        repo,
        'test = "test -f local.env && python3 checks/pricing_check.py"\n'
        'tests = ["checks/*"]\ncopy_ignored = ["local.env"]\n',
    )
    (repo / ".gitignore").write_text("local.env\n")
    (repo / "local.env").write_text("KEY=1\n")
    (repo / "checks").mkdir()
    (repo / "pricing.py").write_text(SOURCE)
    (repo / "checks/pricing_check.py").write_text(
        "import sys; sys.path.insert(0, '.')\n" + STRONG
    )
    done = run("can-fail", repo, {"hook_event_name": "Stop"})
    assert (done.returncode, done.stdout) == (0, "")


def test_gates_write_no_file_into_the_repo(tmp_path):
    repo = make_repo(tmp_path)
    configure(
        tmp_path,
        repo,
        'test = "python3 checks/pricing_check.py"\ntests = ["checks/*"]\n',
    )
    (repo / "checks").mkdir()
    (repo / "pricing.py").write_text(SOURCE)
    (repo / "checks/pricing_check.py").write_text(
        "import sys; sys.path.insert(0, '.')\n" + WEAK
    )
    before = git(repo, "status", "--short", "--ignored")
    for check in ("copies", "can-fail"):
        run(check, repo, {"hook_event_name": "Stop"})
    assert git(repo, "status", "--short", "--ignored") == before
