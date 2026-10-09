from datetime import date

import checkin
import pytest
import vault

TODAY = date(2026, 10, 9)


@pytest.fixture
def settings(tmp_path):
    settings = vault.init_vault(tmp_path, tmp_path / "Notes")
    monkey_calls.clear()
    return settings


monkey_calls = []


@pytest.fixture(autouse=True)
def stub_digest_and_pull(monkeypatch):
    monkeypatch.setattr(
        checkin, "run_digest", lambda s, h: monkey_calls.append("digest")
    )
    monkeypatch.setattr(checkin, "run_pull", lambda s, h: monkey_calls.append("pull"))


def add_pr(settings, repo, age):
    vault.write_note(
        settings.folder / "Signals" / f"PR {repo}.md",
        {
            "type": "signal",
            "kind": "aging_pr",
            "about": [f"[[Repo - {repo}]]"],
            "observed": "2026-10-08",
            "status": "open",
            "age_days": age,
        },
    )


def test_checkin_writes_brief_with_sections_in_order(settings, tmp_path):
    add_pr(settings, "claude", 9)
    add_pr(settings, "secret", 20)
    settings.config["out_of_scope"] = ["secret"]
    vault.write_note(
        settings.folder / "Feedback" / "fb-0001.md",
        {
            "type": "feedback",
            "response": "known",
            "evidence_count_at": 1,
            "date": "2026-10-05",
            "responds_to": "[[Old]]",
        },
    )
    vault.save_state(
        settings, {"sources": {"github": {"ok": True, "count": 1, "error": None}}}
    )
    result = checkin.checkin(settings, tmp_path, TODAY)
    text = (settings.folder / "Briefs" / "2026-W41.md").read_text()
    assert result["brief"].endswith("2026-W41.md")
    positions = [
        text.index(f"## {name}")
        for name in [
            "What changed because of your feedback",
            "Commitments",
            "Blind spots",
            "Held back",
            "Sources",
        ]
    ]
    assert positions == sorted(positions)
    assert "1. PR open 9 days: claude" in text
    assert "[[PR claude]]" in text
    assert "secret" in text.split("## Held back")[1]
    assert "fb-0001" in text.split("## Commitments")[0]
    assert "github" in text.split("## Sources")[1]
    assert result["feedback_applied"] == ["fb-0001"]
    assert result["sources"]["github"]["ok"] is True
    assert monkey_calls == ["digest", "pull"]


def test_checkin_saves_last_checkin_in_order(settings, tmp_path):
    add_pr(settings, "small", 7)
    add_pr(settings, "big", 30)
    checkin.checkin(settings, tmp_path, TODAY)
    saved = vault.load_state(settings)["last_checkin"]
    assert saved == ["PR open 30 days big", "PR open 7 days small"]


def test_numbering_runs_through_commitments_then_blind_spots(settings, tmp_path):
    add_pr(settings, "claude", 9)
    for name, count in [("one", 3)]:
        vault.write_note(
            settings.folder / "Signals" / f"Correction {name}.md",
            {
                "type": "signal",
                "kind": "correction",
                "status": "open",
                "count": count,
                "about": [],
                "observed": "2026-10-08",
            },
        )
    checkin.checkin(settings, tmp_path, TODAY)
    text = (settings.folder / "Briefs" / "2026-W41.md").read_text()
    commitments = text.split("## Commitments")[1].split("## Blind spots")[0]
    spots = text.split("## Blind spots")[1].split("## Held back")[0]
    assert "1. PR open 9 days: claude" in commitments
    assert "2. Told Claude 3 times: one" in spots
    assert "PR open" not in spots


def test_long_evidence_is_shortened_and_sources_read_plainly(settings, tmp_path):
    vault.write_note(
        settings.folder / "Entities" / "Repo - busy.md",
        {"type": "entity", "kind": "repo"},
    )
    for number in range(8):
        vault.write_note(
            settings.folder / "Signals" / f"s{number}.md",
            {
                "type": "signal",
                "kind": "note",
                "status": "open",
                "about": ["[[Repo - busy]]"],
                "observed": "2026-10-08",
            },
        )
    vault.save_state(
        settings,
        {
            "sources": {
                "github": {"ok": True, "count": 79, "error": None},
                "linear": {"ok": False, "count": 0, "error": "no connector"},
            }
        },
    )
    checkin.checkin(settings, tmp_path, TODAY)
    text = (settings.folder / "Briefs" / "2026-W41.md").read_text()
    assert "and 3 more" in text
    assert "- github: ok, 79 items" in text
    assert "- linear: failed: no connector" in text


def test_rerunning_the_same_week_rewrites_the_brief(settings, tmp_path):
    add_pr(settings, "claude", 9)
    checkin.checkin(settings, tmp_path, TODAY)
    checkin.checkin(settings, tmp_path, TODAY)
    assert len(list((settings.folder / "Briefs").glob("*.md"))) == 1
    props, _ = vault.read_note(settings.folder / "Briefs" / "2026-W41.md")
    assert props["type"] == "brief"


def open_spot(settings):
    vault.write_note(
        settings.folder / "Blind spots" / "A.md",
        {"type": "blind_spot", "status": "open"},
    )


def test_nudge_daily_fires_once_per_day(settings):
    open_spot(settings)
    line = checkin.nudge(settings, TODAY)
    assert line == "Radar: 1 open blind spot. Run /at:radar to see them."
    assert checkin.nudge(settings, TODAY) is None
    assert checkin.nudge(settings, date(2026, 10, 10)) == line


def test_nudge_every_fires_each_time(settings):
    settings.config["check_in"]["nudge_at_session_start"] = "every"
    open_spot(settings)
    assert checkin.nudge(settings, TODAY)
    assert checkin.nudge(settings, TODAY)


def test_nudge_off_is_silent(settings):
    settings.config["check_in"]["nudge_at_session_start"] = "off"
    open_spot(settings)
    assert checkin.nudge(settings, TODAY) is None


def test_nudge_silent_when_nothing_is_open(settings):
    vault.write_note(
        settings.folder / "Blind spots" / "A.md",
        {"type": "blind_spot", "status": "known"},
    )
    assert checkin.nudge(settings, TODAY) is None
    assert "nudged_on" not in vault.load_state(settings)
