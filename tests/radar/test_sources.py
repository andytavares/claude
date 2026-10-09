import json

import pytest
import sources
import vault

TODAY = sources.date(2026, 10, 9)


@pytest.fixture
def settings(tmp_path, monkeypatch):
    monkeypatch.setattr(sources, "today", lambda: TODAY)
    settings = vault.init_vault(tmp_path, tmp_path / "Notes")
    off = {"github": False, "linear": False, "memory_corrections": False}
    config = {**settings.config, "sources": off}
    return settings._replace(config=config)


def enable(settings, **flags):
    sources_config = {**settings.config["sources"], **flags}
    return settings._replace(config={**settings.config, "sources": sources_config})


def prs(*numbers):
    return json.dumps(
        [
            {
                "url": f"https://github.com/acme/widgets/pull/{n}",
                "title": f"PR {n}",
                "createdAt": "2026-10-01T12:00:00Z",
                "repository": {"name": "widgets", "nameWithOwner": "acme/widgets"},
            }
            for n in numbers
        ]
    )


def fake_gh(monkeypatch, output="", code=0, error=""):
    result = sources.subprocess.CompletedProcess([], code, output, error)
    monkeypatch.setattr(sources, "run_command", lambda args: result)


def signal_notes(settings):
    return {p.name: vault.read_note(p) for p, _ in vault.notes(settings, "Signals")}


def test_github_writes_one_signal_per_pr_with_age(settings, tmp_path, monkeypatch):
    settings = enable(settings, github=True)
    fake_gh(monkeypatch, prs(1, 2))
    health = sources.pull(settings, tmp_path)
    assert health["github"]["ok"] is True
    assert health["github"]["count"] == 2
    props, _ = signal_notes(settings)["PR acme-widgets-1.md"]
    assert props["kind"] == "aging_pr"
    assert props["source"] == "github"
    assert props["about"] == ["[[Repo - widgets]]"]
    assert props["url"] == "https://github.com/acme/widgets/pull/1"
    assert props["opened"] == "2026-10-01"
    assert props["age_days"] == 8
    assert props["status"] == "open"
    assert (settings.folder / "Entities" / "Repo - widgets.md").is_file()


def test_github_resolves_a_pr_that_is_gone(settings, tmp_path, monkeypatch):
    settings = enable(settings, github=True)
    fake_gh(monkeypatch, prs(1, 2))
    sources.pull(settings, tmp_path)
    fake_gh(monkeypatch, prs(2))
    sources.pull(settings, tmp_path)
    notes = signal_notes(settings)
    assert notes["PR acme-widgets-1.md"][0]["status"] == "resolved"
    assert notes["PR acme-widgets-2.md"][0]["status"] == "open"


def test_github_failure_is_reported_and_others_still_run(
    settings, tmp_path, monkeypatch
):
    memory = tmp_path / ".claude" / "projects" / "p1" / "memory"
    memory.mkdir(parents=True)
    (memory / "feedback_a.md").write_text(
        "---\nname: Be brief\ndescription: Short.\n---\n"
    )
    settings = enable(settings, github=True, memory_corrections=True)
    fake_gh(monkeypatch, code=1, error="not logged in")
    health = sources.pull(settings, tmp_path)
    assert health["github"]["ok"] is False
    assert "not logged in" in health["github"]["error"]
    assert health["memory_corrections"]["ok"] is True


def test_missing_gh_is_a_failure_not_a_crash(settings, tmp_path, monkeypatch):
    def missing(args):
        raise FileNotFoundError("gh")

    monkeypatch.setattr(sources, "run_command", missing)
    health = sources.pull(enable(settings, github=True), tmp_path)
    assert health["github"]["ok"] is False


def test_memory_groups_corrections_by_name_across_projects(settings, tmp_path):
    for project, name in [("p1", "Be brief"), ("p2", "Be brief"), ("p2", "Use rg")]:
        folder = tmp_path / ".claude" / "projects" / project / "memory"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"feedback_{note_slug(name)}.md").write_text(
            f"---\nname: {name}\ndescription: About {name}.\n---\nbody\n"
        )
    health = sources.pull(enable(settings, memory_corrections=True), tmp_path)
    assert health["memory_corrections"]["count"] == 2
    notes = signal_notes(settings)
    brief, body = notes["Correction Be brief.md"]
    assert brief["count"] == 2
    assert brief["projects"] == ["p1", "p2"]
    assert brief["kind"] == "correction"
    assert brief["source"] == "memory"
    assert body.strip() == "About Be brief."
    assert notes["Correction Use rg.md"][0]["count"] == 1


def note_slug(name):
    return name.lower().replace(" ", "_")


def test_disabled_sources_do_not_run(settings, tmp_path, monkeypatch):
    def boom(args):
        raise AssertionError("gh must not run")

    monkeypatch.setattr(sources, "run_command", boom)
    assert sources.pull(settings, tmp_path) == {}


def test_linear_is_left_to_the_skill(settings, tmp_path):
    health = sources.pull(enable(settings, linear=True), tmp_path)
    assert health["linear"]["ok"] is True
    assert health["linear"]["count"] == 0
    assert "Linear connector" in health["linear"]["error"]


def test_health_is_saved_in_state(settings, tmp_path, monkeypatch):
    fake_gh(monkeypatch, prs(1))
    health = sources.pull(enable(settings, github=True), tmp_path)
    saved = vault.load_state(settings)
    assert saved["sources"] == health
    assert set(health["github"]) == {"ok", "count", "error", "ran_at"}
