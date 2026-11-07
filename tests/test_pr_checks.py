import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).parent.parent / "at/hooks/pr-checks/pr_checks.py"
PR = "https://github.com/andytavares/terminator/pull/364"


def transcript(tmp_path, command, output):
    """A session transcript with one Bash call and its result."""
    lines = [
        {
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "t1",
                        "name": "Bash",
                        "input": {"command": command},
                    }
                ]
            }
        },
        {
            "message": {
                "content": [
                    {"type": "tool_result", "tool_use_id": "t1", "content": output}
                ]
            }
        },
    ]
    path = tmp_path / "session.jsonl"
    path.write_text("\n".join(json.dumps(line) for line in lines))
    return path


def fake_gh(tmp_path, checks, exit_code=0):
    """A gh on PATH that prints `checks` for `gh pr checks` and records its arguments."""
    script = tmp_path / "bin/gh"
    script.parent.mkdir()
    script.write_text(
        "#!/bin/sh\n"
        f'echo "$@" >> "{tmp_path}/gh-calls"\n'
        f"printf '%s' '{json.dumps(checks)}'\n"
        f"exit {exit_code}\n"
    )
    script.chmod(0o755)
    return {**os.environ, "PATH": f"{script.parent}:{os.environ['PATH']}"}


def run_hook(path, env, stop_hook_active=False):
    hook = json.dumps(
        {"transcript_path": str(path), "stop_hook_active": stop_hook_active}
    )
    done = subprocess.run(
        [sys.executable, str(HOOK)],
        input=hook,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout) if done.stdout.strip() else None


CREATED = ("gh pr create --draft --title x --body y", f"{PR}\nShell cwd was reset")


@pytest.mark.parametrize(
    "bucket, word", [("pending", "running"), ("fail", "failed"), ("cancel", "failed")]
)
def test_blocks_the_stop_while_a_pr_opened_this_session_is_not_green(
    tmp_path, bucket, word
):
    env = fake_gh(
        tmp_path,
        [{"name": "Unit", "bucket": "pass"}, {"name": "E2E (1/3)", "bucket": bucket}],
    )
    answer = run_hook(transcript(tmp_path, *CREATED), env)
    assert answer["decision"] == "block"
    assert "E2E (1/3)" in answer["reason"] and word in answer["reason"]
    assert "Unit" not in answer["reason"]
    assert f"pr checks {PR}" in (tmp_path / "gh-calls").read_text()


def test_lets_the_stop_through_when_every_check_passed_or_was_skipped(tmp_path):
    env = fake_gh(
        tmp_path,
        [{"name": "Unit", "bucket": "pass"}, {"name": "Release", "bucket": "skipping"}],
    )
    assert run_hook(transcript(tmp_path, *CREATED), env) is None


def test_ignores_pr_links_that_no_gh_pr_create_printed(tmp_path):
    env = fake_gh(tmp_path, [{"name": "Unit", "bucket": "fail"}])
    path = transcript(tmp_path, "gh pr view 364 --json url", PR)
    assert run_hook(path, env) is None
    assert not (tmp_path / "gh-calls").exists()


def test_lets_the_second_stop_through_so_it_cannot_loop(tmp_path):
    env = fake_gh(tmp_path, [{"name": "Unit", "bucket": "fail"}])
    assert run_hook(transcript(tmp_path, *CREATED), env, stop_hook_active=True) is None


def test_blocks_when_gh_reports_no_checks_yet(tmp_path):
    env = fake_gh(tmp_path, [], exit_code=1)
    answer = run_hook(transcript(tmp_path, *CREATED), env)
    assert answer["decision"] == "block"
    assert "could not read" in answer["reason"]
