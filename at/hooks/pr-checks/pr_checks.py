#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Stop hook: do not end a turn while a PR opened in this session has checks running or red."""

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

PR_URL = re.compile(r"https://([\w.-]+(?::\d+)?)/([\w.-]+/[\w.-]+)/pull/\d+")
ASK_EVERY_SECONDS = 24 * 3600
GITHUB_APPS = {"github-actions", "github-advanced-security"}
NOT_GREEN = {"pending": "running", "fail": "failed", "cancel": "failed"}


def text_of(content):
    if isinstance(content, str):
        return content
    return " ".join(part.get("text", "") for part in content if isinstance(part, dict))


def blocks_of(path):
    with open(path, encoding="utf-8") as transcript:
        for line in transcript:
            content = (json.loads(line).get("message") or {}).get("content")
            if isinstance(content, list):
                yield from (block for block in content if isinstance(block, dict))


def opened_prs(path):
    """The PR links that a `gh pr create` printed in this session, in order."""
    creates, prs = set(), []
    for block in blocks_of(path):
        if block.get("type") == "tool_use" and "gh pr create" in json.dumps(
            block.get("input")
        ):
            creates.add(block.get("id"))
        elif block.get("type") == "tool_result" and block.get("tool_use_id") in creates:
            prs += [
                match.group(0)
                for match in PR_URL.finditer(text_of(block.get("content")))
                if match.group(0) not in prs
            ]
    return prs


def gh_json(*args):
    done = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)
    try:
        return done, json.loads(done.stdout)
    except json.JSONDecodeError:
        return done, None


def is_codeql(check):
    return "CodeQL" in (check["name"], check.get("workflow"))


def api_field(host, path, field):
    """The field of a `gh api` answer, or None when gh cannot read it."""
    answer = gh_json("api", "--hostname", host, path)[1]
    return answer.get(field) if isinstance(answer, dict) else None


def has_ci(host, repo):
    """True when the repo has CI other than CodeQL and other GitHub-managed workflows."""
    branch = api_field(host, f"repos/{repo}", "default_branch")
    workflows = api_field(host, f"repos/{repo}/actions/workflows", "workflows")
    runs = api_field(host, f"repos/{repo}/commits/{branch}/check-runs", "check_runs")
    statuses = api_field(host, f"repos/{repo}/commits/{branch}/status", "total_count")
    # An answer gh cannot read counts as CI, so the hook keeps waiting on the PR.
    if None in (workflows, runs, statuses):
        return True
    # GitHub-managed workflows, such as CodeQL default setup, have a path under dynamic/.
    own = [w for w in workflows if not w["path"].startswith("dynamic/")]
    # Runs from these apps belong to Actions workflows or CodeQL, counted above.
    external = [r for r in runs if r["app"]["slug"] not in GITHUB_APPS]
    return bool(own or external or statuses)


def problems(pr):
    """One line per check that is not green, or why the checks could not be read; None without CI."""
    done, checks = gh_json("pr", "checks", pr, "--json", "name,bucket,workflow")
    if done.returncode != 0 and not checks:
        if not has_ci(*PR_URL.match(pr).groups()):
            return None
        return [
            f"{pr}: gh could not read its checks ({done.stderr.strip() or 'none reported yet'})"
        ]
    return [
        f"{pr}: {c['name']} {NOT_GREEN[c['bucket']]}"
        for c in checks
        if c["bucket"] in NOT_GREEN and not is_codeql(c)
    ]


def ask_about_ci(repos):
    """The repos not asked about in the last day, recorded as asked now."""
    data = os.environ.get("CLAUDE_PLUGIN_DATA")
    # Without a data folder the hook cannot remember an ask, so it never asks.
    if not data:
        return []
    record = Path(data) / "no-ci-asked.json"
    asked = json.loads(record.read_text()) if record.exists() else {}
    due = [
        repo for repo in repos if time.time() - asked.get(repo, 0) > ASK_EVERY_SECONDS
    ]
    if due:
        record.parent.mkdir(parents=True, exist_ok=True)
        record.write_text(json.dumps({**asked, **dict.fromkeys(due, time.time())}))
    return due


def no_ci_reason(repos):
    return (
        "These repos have no CI, so their PRs have no checks: " + ", ".join(repos) + "."
        "\nThe project's local check is the done check. Ask the user once whether to add CI "
        "that runs it, in its own PR. Do not mention missing CI again."
    )


def main():
    hook = json.load(sys.stdin)
    # The second stop in a row goes through: Claude has been told, and a block cannot loop.
    if hook.get("stop_hook_active"):
        return
    # Without gh the checks cannot be read, so the hook has nothing to enforce.
    if shutil.which("gh") is None:
        return
    found, no_ci = [], []
    for pr in opened_prs(hook["transcript_path"]):
        lines = problems(pr)
        if lines is None:
            no_ci.append("/".join(PR_URL.match(pr).groups()))
        else:
            found += lines
    if found:
        reason = (
            "A PR you opened is not green, so the task is not done:\n"
            + "\n".join(found)
            + "\nWait for only these checks with `gh run watch <run-id>`, never with "
            "`gh pr checks --watch`, which also waits for CodeQL. Then find and fix the cause "
            "of each failure. Report done only when every check passes."
        )
        print(json.dumps({"decision": "block", "reason": reason}))
    elif due := ask_about_ci(dict.fromkeys(no_ci)):
        print(json.dumps({"decision": "block", "reason": no_ci_reason(due)}))


if __name__ == "__main__":
    main()
