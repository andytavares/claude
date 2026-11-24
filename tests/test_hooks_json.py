import json
import os
import subprocess
from pathlib import Path

PLUGIN = Path(__file__).parent.parent / "at"
CALL = {
    "hook_event_name": "PreToolUse",
    "tool_name": "Write",
    "tool_input": {"command": "ls", "file_path": "README.md", "content": "# repo\n"},
    "stop_hook_active": False,
}
WORDY = (
    "In order to comprehensively address the underlying architectural considerations "
    "that you raised, it is worth noting that the implementation leverages a robust, "
    "holistic abstraction layer which seamlessly encapsulates the persistence semantics."
)
# One runtime folder for the whole run, so uv, Python and Node download once.
SHARED_RUNTIME = Path(
    os.environ.get("AT_TEST_PLUGIN_DATA", Path.home() / ".cache/at-test-plugin-data")
)


def python_hook_commands():
    hooks = json.loads((PLUGIN / "hooks/hooks.json").read_text())["hooks"]
    return [
        hook["command"].replace("${CLAUDE_PLUGIN_ROOT}", str(PLUGIN))
        for groups in hooks.values()
        for group in groups
        for hook in group["hooks"]
        if hook["type"] == "command" and ".py" in hook["command"]
    ]


def hostile_repo(tmp_path):
    """A repo whose every setting asks uv for Python 3.10 or the system Python."""
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    (repo / "README.md").write_text("# repo\n")
    (repo / ".python-version").write_text("3.10\n")
    (repo / "uv.toml").write_text('python-preference = "only-system"\n')
    (repo / "pyproject.toml").write_text(
        '[project]\nname = "hostile"\nversion = "0"\nrequires-python = "==3.10.*"\n'
    )
    return repo


def hostile_env(tmp_path):
    """A shell whose uv, Python and Node on PATH are broken, and whose settings ask for 3.10."""
    bin_dir = tmp_path / "fake-bin"
    bin_dir.mkdir(parents=True)
    for tool in ("uv", "uvx", "python3", "python", "node", "npx"):
        (bin_dir / tool).write_text("#!/bin/sh\necho broken >&2\nexit 1\n")
        (bin_dir / tool).chmod(0o755)
    return {
        **os.environ,
        "HOME": str(tmp_path),
        "PATH": f"{bin_dir}{os.pathsep}/usr/bin{os.pathsep}/bin",
        "UV_PYTHON": "3.10",
        "UV_PYTHON_PREFERENCE": "only-system",
        "VIRTUAL_ENV": str(tmp_path / "no-venv"),
        "PYTHONPATH": str(tmp_path / "no-path"),
        "AT_RUNTIME_DIR": str(SHARED_RUNTIME),
    }


def run_hook(command, tmp_path, call):
    return subprocess.run(
        ["bash", "-c", command],
        cwd=hostile_repo(tmp_path),
        input=json.dumps(call),
        capture_output=True,
        text=True,
        env=hostile_env(tmp_path),
        check=False,
        timeout=600,
    )


def test_no_hook_runs_uv_from_path():
    for command in python_hook_commands():
        assert command.startswith("bash "), command
        assert "/scripts/run.sh" in command, command


def test_python_hooks_ignore_every_repo_and_shell_setting(tmp_path):
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text("")
    call = {**CALL, "transcript_path": str(transcript)}
    for index, command in enumerate(python_hook_commands()):
        done = run_hook(command, tmp_path / str(index), call)
        output = done.stdout + done.stderr
        assert "incompatible" not in output, f"{command}\n{output}"
        assert "Traceback" not in output, f"{command}\n{output}"
        assert "broken" not in output, f"{command}\n{output}"
        assert done.returncode in (0, 2), f"{command}\n{output}"


def test_prose_hook_runs_vale_on_the_plugin_tools_in_a_hostile_repo(tmp_path):
    prose = next(
        command for command in python_hook_commands() if command.endswith(" prose")
    )
    call = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": f"git commit -m {json.dumps(WORDY)}"},
    }
    done = run_hook(prose, tmp_path, call)
    assert done.returncode == 2, done.stdout + done.stderr
    assert "plain-prose check" in done.stderr
