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


def python_hook_commands():
    hooks = json.loads((PLUGIN / "hooks/hooks.json").read_text())["hooks"]
    return [
        hook["command"].replace("${CLAUDE_PLUGIN_ROOT}", str(PLUGIN))
        for groups in hooks.values()
        for group in groups
        for hook in group["hooks"]
        if hook["type"] == "command" and ".py" in hook["command"]
    ]


def path_with_old_python3(tmp_path):
    found = subprocess.run(
        ["uv", "run", "--no-project", "--python", "3.10", "python", "-c",
         "import sys; print(sys.executable)"],
        capture_output=True, text=True, check=True,
    )
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "python3").symlink_to(found.stdout.strip())
    return f"{bin_dir}{os.pathsep}{os.environ['PATH']}"


def test_python_hooks_run_when_the_repo_python3_is_3_10(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    (repo / "README.md").write_text("# repo\n")
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text("")
    call = {**CALL, "transcript_path": str(transcript)}
    env = {**os.environ, "HOME": str(tmp_path), "PATH": path_with_old_python3(tmp_path)}
    assert subprocess.run(
        ["python3", "--version"], capture_output=True, text=True, env=env, check=True
    ).stdout.startswith("Python 3.10")
    for command in python_hook_commands():
        done = subprocess.run(
            ["bash", "-c", command], cwd=repo, input=json.dumps(call),
            capture_output=True, text=True, env=env, check=False, timeout=300,
        )
        assert "Traceback" not in done.stderr, f"{command}\n{done.stderr}"
        assert done.returncode in (0, 2), f"{command}\n{done.stderr}"
