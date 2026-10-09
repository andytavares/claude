from datetime import date

import pytest
import trends
import vault

TODAY = date(2026, 10, 9)


@pytest.fixture
def settings(tmp_path):
    folder = tmp_path / "Radar"
    return vault.Settings(
        tmp_path, folder, {"windows": {"attention_days": 30, "signal_days": 90}}
    )


def entity(settings, name, kind, body=""):
    path = settings.folder / "Entities" / f"{name}.md"
    vault.write_note(path, {"type": "entity", "kind": kind}, body)
    return path


def signal(settings, name, about, observed, **props):
    base = {
        "type": "signal",
        "kind": "incident",
        "about": [vault.link(a) for a in about],
        "theme": None,
        "observed": observed,
        "status": "resolved",
    }
    vault.write_note(settings.folder / "Signals" / f"{name}.md", {**base, **props})


def session(settings, name, repo, body="", **props):
    base = {"type": "session", "repo": vault.link(repo), "radar_only": False}
    vault.write_note(
        settings.folder / "Sessions" / f"{name}.md", {**base, **props}, body
    )


def result_for(settings, name):
    rows = trends.trends(settings, TODAY)
    return next(row for row in rows if row["name"] == name)


def test_weeks_are_zero_filled_across_the_whole_window(settings):
    entity(settings, "Tool - GitHub", "tool")
    signal(settings, "a", ["Tool - GitHub"], "2026-10-08")
    weekly = result_for(settings, "Tool - GitHub")["weekly"]
    assert weekly["2026-W41"] == 1
    assert weekly["2026-W30"] == 0
    assert len(weekly) in (13, 14)


def test_slope_is_positive_when_recent_weeks_are_busier(settings):
    entity(settings, "Tool - GitHub", "tool")
    for i, day in enumerate(["2026-10-07", "2026-10-06", "2026-10-01", "2026-09-10"]):
        signal(settings, f"s{i}", ["Tool - GitHub"], day)
    assert result_for(settings, "Tool - GitHub")["slope"] > 0


def test_slope_is_negative_when_recent_weeks_are_quieter(settings):
    entity(settings, "Tool - GitHub", "tool")
    for i, day in enumerate(["2026-09-02", "2026-09-03", "2026-09-04", "2026-09-05"]):
        signal(settings, f"s{i}", ["Tool - GitHub"], day)
    assert result_for(settings, "Tool - GitHub")["slope"] == -1.0


def test_slope_is_exact_on_a_hand_built_series(settings):
    entity(settings, "Tool - GitHub", "tool")
    signal(settings, "recent", ["Tool - GitHub"], "2026-10-07")
    signal(settings, "older", ["Tool - GitHub"], "2026-08-10")
    # last 4 weeks: 1 in 4 -> 0.25; the 4 before: 0 -> 0.0
    assert result_for(settings, "Tool - GitHub")["slope"] == 0.25


def test_counts_open_signals_and_impacts(settings):
    entity(settings, "Tool - GitHub", "tool")
    signal(settings, "a", ["Tool - GitHub"], "2026-10-08", impact="major")
    signal(settings, "b", ["Tool - GitHub"], "2026-10-07", impact="major")
    signal(
        settings, "c", ["Tool - GitHub"], "2026-10-06", impact="minor", status="open"
    )
    row = result_for(settings, "Tool - GitHub")
    assert row["signal_total"] == 3
    assert row["signals_open"] == 1
    assert row["by_impact"] == {"major": 2, "minor": 1}


def test_breadth_counts_components_and_repos(settings):
    entity(settings, "Tool - GitHub", "tool")
    session(settings, "2026-10-01 claude abc12345", "Repo - claude")
    session(settings, "2026-10-02 other def67890", "Repo - other")
    signal(
        settings, "a", ["Tool - GitHub"], "2026-10-08", components=["Actions", "API"]
    )
    signal(settings, "b", ["Tool - GitHub"], "2026-10-07", components=["Actions"])
    signal(
        settings,
        "c",
        ["Tool - GitHub"],
        "2026-10-06",
        kind="friction",
        session=vault.link("2026-10-01 claude abc12345"),
    )
    signal(
        settings,
        "d",
        ["Tool - GitHub"],
        "2026-10-05",
        kind="friction",
        session=vault.link("2026-10-02 other def67890"),
    )
    signal(
        settings,
        "e",
        ["Tool - GitHub"],
        "2026-10-04",
        kind="friction",
        session=vault.link("2026-10-01 claude abc12345"),
    )
    assert result_for(settings, "Tool - GitHub")["breadth"] == 4


def test_sessions_count_by_repo_link_and_by_mention(settings):
    entity(settings, "Repo - claude", "repo")
    entity(settings, "Tool - GitHub", "tool")
    signal(settings, "a", ["Repo - claude", "Tool - GitHub"], "2026-10-08")
    session(settings, "2026-10-01 claude 11111111", "Repo - claude", "fixing ci")
    session(settings, "2026-10-02 other 22222222", "Repo - other", "github was down")
    session(settings, "2026-10-03 other 33333333", "Repo - other", "unrelated")
    assert result_for(settings, "Repo - claude")["sessions"] == 1
    assert result_for(settings, "Tool - GitHub")["sessions"] == 1


def test_radar_only_and_old_sessions_are_not_attention(settings):
    entity(settings, "Repo - claude", "repo")
    signal(settings, "a", ["Repo - claude"], "2026-10-08")
    session(settings, "2026-10-01 claude 11111111", "Repo - claude", radar_only=True)
    session(settings, "2026-07-01 claude 22222222", "Repo - claude")
    assert result_for(settings, "Repo - claude")["sessions"] == 0


def test_signals_outside_the_window_are_ignored(settings):
    entity(settings, "Tool - GitHub", "tool")
    entity(settings, "Tool - Old", "tool")
    signal(settings, "a", ["Tool - GitHub"], "2026-10-08")
    signal(settings, "b", ["Tool - GitHub"], "2026-01-01")
    signal(settings, "c", ["Tool - Old"], "2026-01-01")
    rows = trends.trends(settings, TODAY)
    assert [r["name"] for r in rows] == ["Tool - GitHub"]
    assert rows[0]["signal_total"] == 1


def test_theme_signals_are_linked_via_theme_and_rows_sort_by_total(settings):
    entity(settings, "Tool - GitHub", "tool")
    vault.write_note(settings.folder / "Themes" / "Slow CI.md", {"type": "theme"})
    signal(settings, "a", ["Tool - GitHub"], "2026-10-08", theme="[[Slow CI]]")
    signal(settings, "b", [], "2026-10-07", theme="[[Slow CI]]")
    rows = trends.trends(settings, TODAY)
    assert [(r["name"], r["signal_total"]) for r in rows] == [
        ("Slow CI", 2),
        ("Tool - GitHub", 1),
    ]
    assert rows[0]["kind"] == "theme"


def test_trend_properties_land_on_the_note_and_the_body_is_untouched(settings):
    path = entity(settings, "Tool - GitHub", "tool", "my own words")
    signal(settings, "a", ["Tool - GitHub"], "2026-10-08")
    trends.trends(settings, TODAY)
    props, body = vault.read_note(path)
    assert body.strip() == "my own words"
    assert props["kind"] == "tool"
    assert props["signal_total"] == 1
    assert str(props["first_signal"]) == "2026-10-08"
    assert str(props["trend_updated"]) == "2026-10-09"
