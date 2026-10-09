import json
import re
from pathlib import Path

import vault

QUEUE = ".queue.jsonl"
PR_URL = re.compile(r"https://github\.com/[^/\s]+/[^/\s]+/pull/\d+")
SECRETS = re.compile(
    r"ghp_[A-Za-z0-9]{20,}|github_pat_\w{20,}|sk-[A-Za-z0-9-]{20,}|AKIA[0-9A-Z]{16}"
    r"|xox[abpr]-[\w-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r"|(?:password|secret|token)\s*[=:]\s*\S+",
    re.IGNORECASE,
)
WORKTREES = re.compile(r"/\.(?:claude/)?worktrees/.*")
RADAR_COMMAND = "/at:radar"


def digest(settings, home):
    entries = read_queue(settings)
    state = vault.load_state(settings)
    done = state.setdefault("digested", {})
    written = []
    for entry in entries:
        path = Path(entry["transcript_path"])
        if done.get(str(path)) == path.stat().st_size:
            continue
        note = write_session(settings, entry)
        done[str(path)] = path.stat().st_size
        written += [note] if note else []
    vault.save_state(settings, state)
    return written


def read_queue(settings):
    queue = settings.folder / QUEUE
    if not queue.is_file():
        return []
    entries = [json.loads(line) for line in queue.read_text().splitlines() if line]
    alive = [e for e in entries if Path(e["transcript_path"]).is_file()]
    if len(alive) != len(entries):
        text = "".join(json.dumps(e) + "\n" for e in alive)
        vault.atomic_write(queue, text)
    return list({e["transcript_path"]: e for e in alive}.values())


def write_session(settings, entry):
    facts = read_transcript(Path(entry["transcript_path"]))
    if not facts["started"]:
        return None
    repo = repo_name(facts["cwd"] or entry["cwd"])
    session_id = entry["session_id"]
    name = f"{facts['started'][:10]} {repo} {session_id[:8]}.md"
    note = settings.folder / "Sessions" / name
    vault.write_note(note, session_props(facts, repo, session_id))
    note.write_text(replace_body(note, body_lines(facts, settings)))
    ensure_repo_entity(settings, repo)
    return note


def replace_body(note, body):
    front = note.read_text().split("---\n", 2)[1]
    return f"---\n{front}---\n{body}"


def session_props(facts, repo, session_id):
    prompts = facts["prompts"]
    return {
        "type": "session",
        "repo": vault.link(f"Repo - {repo}"),
        "branch": facts["branch"],
        "session_id": session_id,
        "started": facts["started"],
        "ended": facts["ended"],
        "prompts": len(prompts),
        "lines_added": facts["added"],
        "lines_removed": facts["removed"],
        "prs": facts["prs"],
        "not_done": facts["not_done"],
        "radar_only": bool(prompts)
        and all(p.startswith(RADAR_COMMAND) for p in prompts),
    }


def ensure_repo_entity(settings, repo):
    note = settings.folder / "Entities" / f"Repo - {repo}.md"
    if not note.exists():
        vault.write_note(note, {"type": "entity", "kind": "repo"})


def repo_name(cwd):
    return Path(WORKTREES.sub("", cwd)).name


def body_lines(facts, settings):
    mode = settings.config["capture"]["prompt_text"]
    if mode == "none":
        return ""
    lines = [prompt_line(p, mode) for p in facts["prompts"]]
    return "".join(f"- {SECRETS.sub('[redacted]', line)}\n" for line in lines)


def prompt_line(prompt, mode):
    if mode == "first-line":
        return prompt.split("\n")[0][:120]
    return prompt.replace("\n", "\n  ")


def read_transcript(path):
    facts = {"started": None, "ended": None, "cwd": "", "branch": "", "prompts": []}
    facts.update(added=0, removed=0, prs=[], not_done=[])
    last_reply = ""
    for record in parse_lines(path):
        take_scalars(facts, record)
        text = prompt_text(record)
        if text:
            facts["prompts"].append(text)
        replies = assistant_texts(record)
        for url in PR_URL.findall("\n".join(replies)):
            if url not in facts["prs"]:
                facts["prs"].append(url)
        last_reply = replies[-1] if replies else last_reply
    facts["not_done"] = not_done_items(last_reply)
    return facts


def parse_lines(path):
    for line in path.read_text().splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            yield record


def take_scalars(facts, record):
    stamp = record.get("timestamp")
    if stamp:
        facts["started"] = min(facts["started"] or stamp, stamp)
        facts["ended"] = max(facts["ended"] or stamp, stamp)
    for key in ("cwd", "branch"):
        source = "gitBranch" if key == "branch" else key
        facts[key] = facts[key] or record.get(source) or ""
    facts["added"] = record.get("totalLinesAdded", facts["added"])
    facts["removed"] = record.get("totalLinesRemoved", facts["removed"])


def text_blocks(content):
    if isinstance(content, str):
        return [content]
    blocks = content if isinstance(content, list) else []
    return [b["text"] for b in blocks if b.get("type") == "text" and "text" in b]


def prompt_text(record):
    if record.get("type") != "user" or record.get("isMeta"):
        return ""
    texts = text_blocks(record.get("message", {}).get("content"))
    text = "\n".join(texts).strip()
    return "" if text.startswith("<") else text


def assistant_texts(record):
    if record.get("type") != "assistant":
        return []
    return text_blocks(record.get("message", {}).get("content"))


def not_done_items(reply):
    items, collecting = [], False
    for line in reply.splitlines():
        if re.match(r"\s*[-*] ", line) and collecting:
            items.append(line.strip()[2:].replace("**", "").strip())
        elif "not done" in line.lower():
            collecting = True
        elif not line.strip() or line.startswith("#"):
            collecting = False
    return items[:5]
