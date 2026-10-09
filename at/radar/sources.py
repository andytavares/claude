import json
import urllib.request
from datetime import datetime

import vault

LINEAR_NOTE = "pulled by /at:radar when the Linear connector is available"
FRICTION_NOTE = "not run here; /at:radar digest writes friction"
TIMEOUT_SECONDS = 20
SEVERITY = {"critical": 3, "major": 2, "minor": 1, "none": 1}
RESOLVED = {"resolved", "postmortem"}


def fetch_json(url):
    with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as response:
        return json.load(response)


def now():
    return datetime.now().astimezone().isoformat()


def pull(settings, home):
    enabled = {name for name, on in settings.config["sources"].items() if on}
    health = {}
    if "status_pages" in enabled:
        for page in settings.config["status_pages"]:
            health[f"status:{page['name']}"] = run_page(settings, page)
    if "session_friction" in enabled:
        health["session_friction"] = report(error=FRICTION_NOTE)
    if "linear" in enabled:
        health["linear"] = report(error=LINEAR_NOTE)
    vault.save_state(settings, {**vault.load_state(settings), "sources": health})
    return health


def report(ok=True, count=0, error=None):
    return {"ok": ok, "count": count, "error": error, "ran_at": now()}


def run_page(settings, page):
    try:
        count = pull_status_page(settings, page)
    except (OSError, ValueError) as error:
        return report(ok=False, error=str(error))
    return report(count=count)


def pull_status_page(settings, page):
    incidents = fetch_json(f"{page['url']}/api/v2/incidents.json")["incidents"]
    tool = f"Tool - {page['name']}"
    entity = settings.folder / "Entities" / f"{tool}.md"
    if not entity.exists():
        vault.write_note(entity, {"type": "entity", "kind": "tool"})
    for incident in incidents:
        path = (
            settings.folder / "Signals" / f"Status {page['name']} {incident['id']}.md"
        )
        vault.write_note(path, incident_props(incident, tool), incident["name"])
    return len(incidents)


def incident_props(incident, tool):
    return {
        "type": "signal",
        "source": "status",
        "kind": "incident",
        "about": [vault.link(tool)],
        "theme": None,
        "observed": incident["created_at"][:10],
        "status": "resolved" if incident["status"] in RESOLVED else "open",
        "severity": SEVERITY[incident["impact"]],
        "impact": incident["impact"],
        "components": [part["name"] for part in incident["components"]],
        "url": incident["shortlink"],
        "resolved_at": incident["resolved_at"],
    }
