import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

HOOK = Path(__file__).parent.parent / "at/hooks/pr-checks/pr_checks.py"
PR = "https://github.com/example-org/app/pull/364"


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


def fake_gh(tmp_path, checks, exit_code=0, ci=None):
    """A fake gh: `checks` for `gh pr checks`, and the repo's `ci` for `gh api`."""
    ci = {"workflows": [], "check-runs": [], "status": 0, **(ci or {})}
    repo = "repos/example-org/app"
    routes = {
        "'pr checks'*": checks,
        f"*{repo}/actions/workflows": {
            "workflows": [{"path": p} for p in ci["workflows"]]
        },
        f"*{repo}/commits/main/check-runs": {
            "check_runs": [{"app": {"slug": app}} for app in ci["check-runs"]]
        },
        f"*{repo}/commits/main/status": {"total_count": ci["status"]},
        f"*{repo}": {"default_branch": "main"},
    }
    cases = ""
    for index, (pattern, answer) in enumerate(routes.items()):
        (tmp_path / f"answer-{index}.json").write_text(json.dumps(answer))
        cases += f"  {pattern}) cat '{tmp_path}/answer-{index}.json' ;;\n"
    script = tmp_path / "bin/gh"
    script.parent.mkdir()
    script.write_text(
        f'#!/bin/sh\necho "$@" >> "{tmp_path}/gh-calls"\ncase "$*" in\n{cases}esac\n'
        f'case "$*" in pr*) exit {exit_code} ;; esac\n'
    )
    script.chmod(0o755)
    env = {**os.environ, "PATH": f"{script.parent}:{os.environ['PATH']}"}
    return {**env, "CLAUDE_PLUGIN_DATA": str(tmp_path / "data")}


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


@pytest.mark.parametrize(
    "ci",
    [
        {"workflows": [".github/workflows/ci.yml"]},
        {"check-runs": ["buildkite"]},
        {"status": 1},
    ],
)
def test_blocks_when_gh_reports_no_checks_yet_in_a_repo_with_ci(tmp_path, ci):
    env = fake_gh(tmp_path, [], exit_code=1, ci=ci)
    answer = run_hook(transcript(tmp_path, *CREATED), env)
    assert answer["decision"] == "block"
    assert "could not read" in answer["reason"]


def test_lets_the_stop_through_when_gh_is_not_installed(tmp_path):
    env = {**os.environ, "PATH": str(tmp_path)}
    assert run_hook(transcript(tmp_path, *CREATED), env) is None


def test_checks_a_pr_on_a_github_enterprise_host(tmp_path):
    enterprise = "https://git.example.com/example-org/app/pull/12"
    env = fake_gh(tmp_path, [{"name": "Unit", "bucket": "fail"}])
    path = transcript(tmp_path, "gh pr create --draft", enterprise)
    answer = run_hook(path, env)
    assert enterprise in answer["reason"]


def asked(env, repo, hours_ago):
    """Record that the hook asked about CI for `repo` `hours_ago` hours ago."""
    data = Path(env["CLAUDE_PLUGIN_DATA"])
    data.mkdir(exist_ok=True)
    (data / "no-ci-asked.json").write_text(
        json.dumps({repo: time.time() - hours_ago * 3600})
    )


def test_asks_once_to_add_ci_when_the_repo_has_no_ci(tmp_path):
    env = fake_gh(tmp_path, [], exit_code=1)
    first = run_hook(transcript(tmp_path, *CREATED), env)
    again = run_hook(transcript(tmp_path, *CREATED), env)
    assert first["decision"] == "block"
    assert "no CI" in first["reason"] and "could not read" not in first["reason"]
    assert again is None


def test_stays_silent_when_it_asked_about_this_repo_in_the_last_day(tmp_path):
    env = fake_gh(tmp_path, [], exit_code=1)
    asked(env, "github.com/example-org/app", hours_ago=23)
    assert run_hook(transcript(tmp_path, *CREATED), env) is None


def test_asks_again_when_the_last_ask_was_more_than_a_day_ago(tmp_path):
    env = fake_gh(tmp_path, [], exit_code=1)
    asked(env, "github.com/example-org/app", hours_ago=25)
    assert run_hook(transcript(tmp_path, *CREATED), env)["decision"] == "block"


def test_an_ask_about_another_repo_does_not_silence_this_one(tmp_path):
    env = fake_gh(tmp_path, [], exit_code=1)
    asked(env, "github.com/example-org/other", hours_ago=1)
    assert run_hook(transcript(tmp_path, *CREATED), env)["decision"] == "block"


def test_never_waits_for_codeql(tmp_path):
    env = fake_gh(
        tmp_path,
        [
            {"name": "CodeQL", "bucket": "pending", "workflow": ""},
            {"name": "Analyze (python)", "bucket": "pending", "workflow": "CodeQL"},
            {"name": "Unit", "bucket": "pass", "workflow": "CI"},
        ],
        exit_code=8,
    )
    assert run_hook(transcript(tmp_path, *CREATED), env) is None


def test_a_repo_whose_only_checks_are_codeql_counts_as_having_no_ci(tmp_path):
    codeql_only = {
        "workflows": ["dynamic/github-code-scanning/codeql"],
        "check-runs": ["github-actions", "github-advanced-security"],
    }
    env = fake_gh(tmp_path, [], exit_code=1, ci=codeql_only)
    answer = run_hook(transcript(tmp_path, *CREATED), env)
    assert "no CI" in answer["reason"]


def test_keeps_waiting_when_gh_api_cannot_read_the_repo(tmp_path):
    env = fake_gh(tmp_path, [], exit_code=1)
    (tmp_path / "answer-1.json").write_text('{"message": "Not Found"}')
    answer = run_hook(transcript(tmp_path, *CREATED), env)
    assert "could not read" in answer["reason"]
