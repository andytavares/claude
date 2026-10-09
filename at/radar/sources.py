import json
import subprocess
from datetime import date, datetime

import vault

LINEAR_NOTE = "pulled by /at:radar when the Linear connector is available"
GH_ARGS = [
    "gh", "search", "prs", "--author", "@me", "--state", "open",
    "--json", "url,title,createdAt,repository", "--limit", "100",
]  # fmt: skip


class SourceError(Exception):
    pass


def today():
    return datetime.now().astimezone().date()


def run_command(args):
    return subprocess.run(args, capture_output=True, text=True, check=False)


def pull(settings, home):
    day = today()
    runners = {
        "github": lambda: pull_github(settings, day),
        "memory_corrections": lambda: pull_memory(settings, home, day),
        "linear": lambda: 0,
    }
    health = {}
    for name, enabled in settings.config["sources"].items():
        if enabled and name in runners:
            health[name] = run_source(name, runners[name])
    if health:
        state = vault.load_state(settings)
        vault.save_state(settings, {**state, "sources": health})
    return health


def run_source(name, runner):
    ran_at = datetime.now().astimezone().isoformat()
    if name == "linear":
        return {"ok": True, "count": 0, "error": LINEAR_NOTE, "ran_at": ran_at}
    try:
        return {"ok": True, "count": runner(), "error": None, "ran_at": ran_at}
    except (SourceError, FileNotFoundError, OSError, ValueError) as error:
        return {"ok": False, "count": 0, "error": str(error), "ran_at": ran_at}


def fetch_prs():
    result = run_command(GH_ARGS)
    if result.returncode != 0:
        raise SourceError(result.stderr.strip() or "gh failed")
    return json.loads(result.stdout or "[]")


def pull_github(settings, day):
    found = fetch_prs()
    for pr in found:
        write_pr(settings, pr, day)
    resolve_gone(settings, {pr["url"] for pr in found})
    return len(found)


def write_pr(settings, pr, day):
    owner, repo, _, number = pr["url"].split("/")[3:7]
    entity = f"Repo - {pr['repository']['name']}"
    entity_path = settings.folder / "Entities" / f"{entity}.md"
    if not entity_path.exists():
        vault.write_note(entity_path, {"type": "entity", "kind": "repo"})
    opened = date.fromisoformat(pr["createdAt"][:10])
    props = {
        "type": "signal",
        "source": "github",
        "kind": "aging_pr",
        "about": [vault.link(entity)],
        "theme": None,
        "observed": day.isoformat(),
        "status": "open",
        "severity": 2,
        "url": pr["url"],
        "opened": opened.isoformat(),
        "age_days": (day - opened).days,
    }
    path = settings.folder / "Signals" / f"PR {owner}-{repo}-{number}.md"
    vault.write_note(path, props, pr["title"])


def resolve_gone(settings, urls):
    for path, props in vault.notes(settings, "Signals"):
        if props.get("source") == "github" and props.get("url") not in urls:
            vault.write_note(path, {"status": "resolved"})


def pull_memory(settings, home, day):
    projects = {}
    descriptions = {}
    pattern = ".claude/projects/*/memory/feedback_*.md"
    for path in sorted(home.glob(pattern)):
        props = vault.read_note(path)[0]
        name = props["name"]
        projects.setdefault(name, set()).add(path.parts[-3])
        descriptions[name] = props.get("description", "")
    for name, folders in projects.items():
        write_correction(settings, name, (sorted(folders), descriptions[name], day))
    return len(projects)


def write_correction(settings, name, detail):
    folders, description, day = detail
    props = {
        "type": "signal",
        "source": "memory",
        "kind": "correction",
        "about": [],
        "theme": None,
        "observed": day.isoformat(),
        "status": "open",
        "severity": 2,
        "projects": folders,
        "count": len(folders),
    }
    path = settings.folder / "Signals" / f"Correction {vault.note_name(name)}.md"
    vault.write_note(path, props, description)
