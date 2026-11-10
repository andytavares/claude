import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

GUARD = Path(__file__).parent.parent / "at/hooks/zsh-guard/guard.py"


def run_guard(command, tool_name="Bash", shell="/bin/zsh", code_shell=None):
    hook = json.dumps({"tool_name": tool_name, "tool_input": {"command": command}})
    return subprocess.run(
        [sys.executable, str(GUARD)],
        input=hook,
        capture_output=True,
        text=True,
        env={
            **{k: v for k, v in os.environ.items() if k != "CLAUDE_CODE_SHELL"},
            "SHELL": shell,
            **({"CLAUDE_CODE_SHELL": code_shell} if code_shell else {}),
        },
        check=False,
    )


@pytest.mark.parametrize(
    "command",
    [
        "grep -rn --include=*.md foo .",
        "grep -rn --exclude=*.lock foo .",
        "cd docs && grep -rln --include=*.py TODO",
    ],
)
def test_unquoted_include_glob_is_blocked(command):
    done = run_guard(command)
    assert done.returncode == 2
    assert "--include='*.md'" in done.stderr


@pytest.mark.parametrize(
    "command",
    [
        "for c in a b; do $c; done",
        "$cmd --help",
        "true && ${runner} tests",
        "ls | $pager",
        "if true; then\n  $c\nfi",
    ],
)
def test_variable_as_command_is_blocked(command):
    done = run_guard(command)
    assert done.returncode == 2
    assert "${=var}" in done.stderr


@pytest.mark.parametrize(
    "command",
    [
        "grep -rn --include='*.md' foo .",
        'grep -rn --include="*.md" foo .',
        "grep -rn --include=\\*.md foo .",
        'echo "$c"',
        "echo '--include=*.md'",
        'echo "for c in a b; do $c; done"',
        "for c in a b; do echo $c; done",
        "${=cmd} --help",
        "cat > notes.md << 'EOF'\n$c\ngrep --include=*.md x\nEOF\nls",
        "cat <<-EOF\n\t$c\n\tEOF",
        "x=$HOME/bin; ls $x",
    ],
)
def test_safe_command_passes(command):
    done = run_guard(command)
    assert done.returncode == 0, done.stderr
    assert done.stderr == ""


def test_code_after_heredoc_is_still_checked():
    done = run_guard("cat << EOF\nhello\nEOF\n$c")
    assert done.returncode == 2


def test_non_bash_input_passes():
    assert run_guard("$c", tool_name="Read").returncode == 0


def test_bash_users_are_not_blocked():
    done = run_guard("$cmd --help", shell="/bin/bash")
    assert done.returncode == 0
    assert done.stderr == ""


def test_claude_code_shell_overrides_shell():
    assert (
        run_guard("$cmd --help", shell="/bin/zsh", code_shell="/bin/bash").returncode
        == 0
    )
    assert (
        run_guard("$cmd --help", shell="/bin/bash", code_shell="/bin/zsh").returncode
        == 2
    )
