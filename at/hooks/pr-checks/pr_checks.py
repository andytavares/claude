"""Stop hook: do not end a turn while a PR opened in this session has checks running or red."""

import json
import re
import subprocess
import sys

PR_URL = re.compile(r"https://github\.com/[\w.-]+/[\w.-]+/pull/\d+")
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
                url
                for url in PR_URL.findall(text_of(block.get("content")))
                if url not in prs
            ]
    return prs


def problems(pr):
    """One line per check that is not green, or why the checks could not be read."""
    done = subprocess.run(
        ["gh", "pr", "checks", pr, "--json", "name,bucket"],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        checks = json.loads(done.stdout)
    except json.JSONDecodeError:
        checks = None
    if done.returncode != 0 and not checks:
        return [
            f"{pr}: gh could not read its checks ({done.stderr.strip() or 'none reported yet'})"
        ]
    return [
        f"{pr}: {c['name']} {NOT_GREEN[c['bucket']]}"
        for c in checks
        if c["bucket"] in NOT_GREEN
    ]


def main():
    hook = json.load(sys.stdin)
    # The second stop in a row goes through: Claude has been told, and a block cannot loop.
    if hook.get("stop_hook_active"):
        return
    found = [
        line for pr in opened_prs(hook["transcript_path"]) for line in problems(pr)
    ]
    if found:
        reason = (
            "A PR you opened is not green, so the task is not done:\n"
            + "\n".join(found)
            + "\nWait with `gh pr checks <url> --watch`, then find and fix the cause of each "
            "failure. Report done only when every check passes."
        )
        print(json.dumps({"decision": "block", "reason": reason}))


if __name__ == "__main__":
    main()
