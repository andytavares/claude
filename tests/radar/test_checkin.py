from datetime import date

import checkin
import pytest
import vault

TODAY = date(2026, 10, 9)


@pytest.fixture
def settings(tmp_path, monkeypatch):
    monkeypatch.setattr(checkin, "run_digest", lambda settings, home: None)
    monkeypatch.setattr(checkin, "run_pull", lambda settings, home: None)
    monkeypatch.setattr(checkin, "run_trends", lambda settings, today: [])
    return vault.init_vault(tmp_path, tmp_path / "Notes")


def add_opportunity(settings, name, **props):
    base = {"type": "opportunity", "status": "candidate", "score": 3.0}
    vault.write_note(
        settings.folder / "Opportunities" / f"{name}.md", {**base, **props}
    )


def add_feedback(settings, number, **props):
    base = {"type": "feedback", "date": "2026-10-08", "text": None, "target": None}
    vault.write_note(
        settings.folder / "Feedback" / f"fb-{number:04d}.md", {**base, **props}
    )


def trend(name, **props):
    base = {
        "name": name,
        "kind": "tool",
        "slope": 0,
        "signals_open": 0,
        "sessions": 5,
        "weekly": {},
    }
    return {**base, **props}


def brief(settings, trends=None, monkeypatch=None):
    if trends is not None:
        monkeypatch.setattr(checkin, "run_trends", lambda settings, today: trends)
    result = checkin.checkin(settings, None, TODAY)
    return result, (settings.folder / "Briefs" / "2026-W41.md").read_text()


def section(text, heading):
    return text.split(f"## {heading}")[1].split("\n## ")[0]


def test_brief_has_sections_in_order(settings):
    _, text = brief(settings)
    headings = [line for line in text.splitlines() if line.startswith("## ")]
    assert headings == [
        "## What changed because of your feedback",
        "## Opportunities",
        "## Rising",
        "## Blind spots",
        "## Held back",
        "## Sources",
    ]
    assert vault.read_note(settings.folder / "Briefs" / "2026-W41.md")[0] == {
        "type": "brief",
        "date": "2026-10-09",
    }


def test_checkin_runs_digest_pull_and_trends(settings, monkeypatch):
    calls = []
    monkeypatch.setattr(checkin, "run_digest", lambda s, h: calls.append("digest"))
    monkeypatch.setattr(checkin, "run_pull", lambda s, h: calls.append("pull"))
    monkeypatch.setattr(
        checkin, "run_trends", lambda s, t: calls.append(("trends", t)) or []
    )
    checkin.checkin(settings, None, TODAY)
    assert calls == ["digest", "pull", ("trends", TODAY)]


def test_no_opportunities_says_how_to_find_some(settings):
    result, text = brief(settings)
    assert "None yet. Run /at:radar-scan to find some from the evidence below." in text
    assert result["opportunities"] == []
    assert vault.load_state(settings)["last_checkin"] == []


def test_opportunities_ranked_numbered_and_limited(settings):
    add_opportunity(settings, "Low", score=2.0)
    add_opportunity(
        settings,
        "Replace GitHub",
        score=4.1,
        confidence=0.6,
        previous_score=3.5,
        weeks_estimate=12,
        ladder_criteria=["org-wide scope", "cross-team"],
        provisional=True,
        status="pursuing",
    )
    add_opportunity(settings, "Middle", score=3.0)
    add_opportunity(settings, "Done one", score=5.0, status="done")
    add_opportunity(settings, "Parked one", score=5.0, status="parked")
    settings.config["check_in"]["max_opportunities"] = 2
    result, text = brief(settings)
    body = section(text, "Opportunities")
    assert "1. Replace GitHub" in body
    assert "4.1, confidence 0.6" in body
    assert "(was 3.5)" in body
    assert "pursuing" in body
    assert "12 weeks" in body
    assert "org-wide scope" in body
    assert "cross-team" in body
    assert "(provisional)" in body
    assert "2. Middle" in body
    assert "Low" not in body
    assert "Done one" not in body
    assert [o["name"] for o in result["opportunities"]] == ["Replace GitHub", "Middle"]
    assert vault.load_state(settings)["last_checkin"] == ["Replace GitHub", "Middle"]


def test_unchanged_score_shows_no_change_and_not_provisional(settings):
    add_opportunity(settings, "Same", score=3.0, previous_score=3.0, provisional=False)
    _, text = brief(settings)
    body = section(text, "Opportunities")
    assert "was" not in body
    assert "provisional" not in body


def test_feedback_applied_lists_last_week_only(settings):
    add_feedback(settings, 1, kind="pursue", target="[[Replace GitHub]]")
    add_feedback(settings, 2, kind="park", target="[[Old]]", date="2026-09-20")
    result, text = brief(settings)
    body = section(text, "What changed because of your feedback")
    assert "Replace GitHub" in body
    assert "pursue" in body
    assert "Old" not in body
    assert result["feedback_applied"] == ["fb-0001"]


def test_rising_top_three_by_slope_with_last_four_weeks(settings, monkeypatch):
    weekly = {"2026-W36": 9, "2026-W37": 1, "2026-W38": 2, "2026-W39": 3, "2026-W40": 4}
    trends = [
        trend("Flat", slope=0),
        trend("A", slope=1.0),
        trend("B", slope=4.0, weekly=weekly, signals_open=7),
        trend("C", slope=2.0),
        trend("D", slope=3.0),
    ]
    result, text = brief(settings, trends=trends, monkeypatch=monkeypatch)
    body = section(text, "Rising")
    assert body.index("B") < body.index("D") < body.index("C")
    assert "A:" not in body
    assert "Flat" not in body
    assert "1, 2, 3, 4" in body
    assert "9," not in body
    assert "7 open" in body
    assert [t["name"] for t in result["rising"]] == ["B", "D", "C"]


def test_blind_spots_need_open_signals_and_few_sessions(settings, monkeypatch):
    trends = [
        trend("GitHub", signals_open=6, sessions=1),
        trend("Busy", signals_open=9, sessions=4),
        trend("Quiet", signals_open=2, sessions=0),
        trend("Jenkins", signals_open=4, sessions=0),
    ]
    settings.config["check_in"]["max_blind_spots"] = 2
    result, text = brief(settings, trends=trends, monkeypatch=monkeypatch)
    body = section(text, "Blind spots")
    assert "GitHub: 6 open signals, 1 sessions in 30 days" in body
    assert "Jenkins: 4 open signals, 0 sessions in 30 days" in body
    assert "Busy" not in body
    assert "Quiet" not in body
    assert [t["name"] for t in result["blind_spots"]] == ["GitHub", "Jenkins"]


def test_held_back_uses_latest_feedback_text_and_config(settings):
    add_opportunity(settings, "Parked one", status="parked")
    add_opportunity(settings, "Rejected one", status="rejected")
    add_opportunity(settings, "Silent", status="rejected")
    add_feedback(settings, 1, kind="park", target="[[Parked one]]", text="old reason")
    add_feedback(settings, 2, kind="park", target="[[Parked one]]", text="after Q4")
    add_feedback(settings, 3, kind="reject", target="[[Rejected one]]", text="no")
    add_feedback(settings, 4, kind="reject", target="[[Silent]]")
    settings.config["out_of_scope"] = [{"area": "Payroll", "reason": "HR owns it"}]
    result, text = brief(settings)
    body = section(text, "Held back")
    assert "Parked one" in body
    assert "after Q4" in body
    assert "old reason" not in body
    assert "Rejected one" in body
    assert "Silent" not in body
    assert "Payroll" in body
    assert "HR owns it" in body
    assert len(result["held_back"]) == 3


def test_sources_show_health(settings):
    health = {
        "linear": {"ok": True, "count": 12},
        "status": {"ok": False, "error": "timeout"},
    }
    vault.save_state(settings, {"sources": health})
    result, text = brief(settings)
    body = section(text, "Sources")
    assert "- linear: ok, 12 items" in body
    assert "- status: failed: timeout" in body
    assert result["sources"] == health


def test_rewriting_the_same_week_replaces_the_brief(settings):
    brief(settings)
    add_opportunity(settings, "Late arrival")
    _, text = brief(settings)
    assert text.count("# Radar check-in") == 1
    assert "Late arrival" in text


def candidate(settings, name, first_seen):
    add_opportunity(settings, name, first_seen=first_seen)


def test_nudge_counts_candidates_seen_since_last_nudge(settings):
    candidate(settings, "Old", "2026-10-01")
    candidate(settings, "New", "2026-10-08")
    add_opportunity(settings, "Pursued", status="pursuing", first_seen="2026-10-08")
    vault.save_state(settings, {"nudged_on": "2026-10-05"})
    line = checkin.nudge(settings, TODAY)
    assert line == "Radar: 1 new opportunity. Run /at:radar to see it."
    assert vault.load_state(settings)["nudged_on"] == "2026-10-09"


def test_nudge_with_no_history_counts_all_and_pluralises(settings):
    candidate(settings, "One", "2026-09-01")
    candidate(settings, "Two", "2026-10-01")
    assert checkin.nudge(settings, TODAY) == (
        "Radar: 2 new opportunities. Run /at:radar to see them."
    )


def test_nudge_daily_fires_once_per_day(settings):
    candidate(settings, "One", "2026-10-09")
    assert checkin.nudge(settings, TODAY)
    candidate(settings, "Two", "2026-10-10")
    assert checkin.nudge(settings, TODAY) is None


def test_nudge_every_fires_each_time(settings):
    settings.config["check_in"]["nudge_at_session_start"] = "every"
    candidate(settings, "One", "2026-10-09")
    vault.save_state(settings, {"nudged_on": "2026-10-08"})
    assert checkin.nudge(settings, TODAY)
    candidate(settings, "Two", "2026-10-10")
    assert checkin.nudge(settings, TODAY) == (
        "Radar: 1 new opportunity. Run /at:radar to see it."
    )


def test_nudge_off_is_silent(settings):
    settings.config["check_in"]["nudge_at_session_start"] = "off"
    candidate(settings, "One", "2026-10-09")
    assert checkin.nudge(settings, TODAY) is None


def test_nudge_with_nothing_new_leaves_state_alone(settings):
    candidate(settings, "Old", "2026-10-01")
    vault.save_state(settings, {"nudged_on": "2026-10-05"})
    assert checkin.nudge(settings, TODAY) is None
    assert vault.load_state(settings)["nudged_on"] == "2026-10-05"
