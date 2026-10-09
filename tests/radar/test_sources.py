import json
import urllib.error
from pathlib import Path

import pytest
import sources
import vault

FIXTURE = Path(__file__).parent / "fixtures" / "status" / "github.json"
GITHUB = {"name": "GitHub", "url": "https://www.githubstatus.com"}
SLACK = {"name": "Slack", "url": "https://status.slack.example"}


@pytest.fixture
def settings(tmp_path):
    settings = vault.init_vault(tmp_path, tmp_path / "Notes")
    off = {"status_pages": False, "session_friction": False, "linear": False}
    return settings._replace(config={**settings.config, "sources": off})


def enable(settings, pages=(GITHUB,), **flags):
    on = {**settings.config["sources"], "status_pages": True, **flags}
    config = {**settings.config, "sources": on, "status_pages": list(pages)}
    return settings._replace(config=config)


def serve(monkeypatch, pages):
    def fetch(url):
        page = pages[url.removesuffix("/api/v2/incidents.json")]
        if isinstance(page, Exception):
            raise page
        return page

    monkeypatch.setattr(sources, "fetch_json", fetch)


def github_payload():
    return json.loads(FIXTURE.read_text())


def signal(settings, name):
    return vault.read_note(settings.folder / "Signals" / name)


def test_writes_one_note_per_incident_with_exact_props(settings, tmp_path, monkeypatch):
    serve(monkeypatch, {GITHUB["url"]: github_payload()})
    sources.pull(enable(settings), tmp_path)
    props, body = signal(settings, "Status GitHub ccc333.md")
    assert props == {
        "type": "signal",
        "source": "status",
        "kind": "incident",
        "about": ["[[Tool - GitHub]]"],
        "theme": None,
        "observed": "2026-10-08",
        "status": "open",
        "severity": 3,
        "impact": "critical",
        "components": ["Pull Requests"],
        "url": "https://stspg.io/ccc333",
        "resolved_at": None,
    }
    assert "Pull requests unavailable" in body


def test_status_severity_and_resolution_follow_impact_and_state(
    settings, tmp_path, monkeypatch
):
    serve(monkeypatch, {GITHUB["url"]: github_payload()})
    sources.pull(enable(settings), tmp_path)
    major, _ = signal(settings, "Status GitHub bbb222.md")
    assert (major["status"], major["severity"]) == ("resolved", 2)
    assert major["components"] == ["Git Operations", "API Requests"]
    assert major["resolved_at"] == "2026-10-05T16:30:00.000Z"
    minor, _ = signal(settings, "Status GitHub aaa111.md")
    assert (minor["status"], minor["severity"]) == ("resolved", 1)
    none, _ = signal(settings, "Status GitHub ddd444.md")
    assert (none["impact"], none["severity"], none["components"]) == ("none", 1, [])


def test_second_pull_updates_changed_incident_and_adds_new_without_duplicates(
    settings, tmp_path, monkeypatch
):
    config = enable(settings)
    serve(monkeypatch, {GITHUB["url"]: github_payload()})
    sources.pull(config, tmp_path)
    payload = github_payload()
    payload["incidents"][2]["status"] = "resolved"
    payload["incidents"][2]["resolved_at"] = "2026-10-09T01:00:00.000Z"
    payload["incidents"].insert(0, {**payload["incidents"][0], "id": "eee555"})
    serve(monkeypatch, {GITHUB["url"]: payload})
    sources.pull(config, tmp_path)
    names = sorted(p.name for p, _ in vault.notes(config, "Signals"))
    assert len(names) == 5
    assert "Status GitHub eee555.md" in names
    props, _ = signal(config, "Status GitHub ccc333.md")
    assert props["status"] == "resolved"
    assert props["resolved_at"] == "2026-10-09T01:00:00.000Z"


def test_incident_outside_the_window_stays_on_disk(settings, tmp_path, monkeypatch):
    config = enable(settings)
    serve(monkeypatch, {GITHUB["url"]: github_payload()})
    sources.pull(config, tmp_path)
    payload = github_payload()
    payload["incidents"] = payload["incidents"][:1]
    serve(monkeypatch, {GITHUB["url"]: payload})
    health = sources.pull(config, tmp_path)
    assert health["status:GitHub"]["count"] == 1
    assert len(list(vault.notes(config, "Signals"))) == 4


def test_failing_page_is_reported_and_the_other_still_runs(
    settings, tmp_path, monkeypatch
):
    pages = {
        GITHUB["url"]: urllib.error.URLError("no route"),
        SLACK["url"]: {"incidents": []},
    }
    serve(monkeypatch, pages)
    health = sources.pull(enable(settings, pages=(GITHUB, SLACK)), tmp_path)
    assert health["status:GitHub"]["ok"] is False
    assert "no route" in health["status:GitHub"]["error"]
    assert health["status:Slack"]["ok"] is True
    assert health["status:Slack"]["count"] == 0


def test_disabled_sources_are_not_run(settings, tmp_path, monkeypatch):
    def boom(url):
        raise AssertionError("fetched")

    monkeypatch.setattr(sources, "fetch_json", boom)
    assert sources.pull(settings, tmp_path) == {}


def test_tool_entity_is_created_once_and_never_overwritten(
    settings, tmp_path, monkeypatch
):
    config = enable(settings)
    serve(monkeypatch, {GITHUB["url"]: github_payload()})
    sources.pull(config, tmp_path)
    path = config.folder / "Entities" / "Tool - GitHub.md"
    assert vault.read_note(path)[0] == {"type": "entity", "kind": "tool"}
    vault.write_note(path, {"owner": "platform"})
    sources.pull(config, tmp_path)
    assert vault.read_note(path)[0]["owner"] == "platform"


def test_health_is_saved_and_friction_and_linear_report(
    settings, tmp_path, monkeypatch
):
    serve(monkeypatch, {GITHUB["url"]: github_payload()})
    config = enable(settings, session_friction=True, linear=True)
    health = sources.pull(config, tmp_path)
    assert health["status:GitHub"]["count"] == 4
    assert health["status:GitHub"]["error"] is None
    assert health["session_friction"]["ok"] is True
    assert health["session_friction"]["count"] == 0
    assert "digest" in health["session_friction"]["error"]
    assert health["linear"] == {
        "ok": True,
        "count": 0,
        "error": sources.LINEAR_NOTE,
        "ran_at": health["linear"]["ran_at"],
    }
    assert vault.load_state(config)["sources"] == health
