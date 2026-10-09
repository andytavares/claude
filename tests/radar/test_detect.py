from datetime import date

import detect
import pytest
import vault

TODAY = date(2026, 10, 9)


@pytest.fixture
def settings(tmp_path):
    return vault.init_vault(tmp_path, tmp_path / "Notes")


def add_repo(settings, repo):
    vault.write_note(
        settings.folder / "Entities" / f"Repo - {repo}.md",
        {"type": "entity", "kind": "repo"},
    )


def add_session(settings, repo, day, body="", **props):
    stem = f"{day} {repo} {len(list((settings.folder / 'Sessions').glob('*.md'))):08d}"
    base = {
        "type": "session",
        "repo": f"[[Repo - {repo}]]",
        "started": f"{day}T10:00:00+00:00",
        "not_done": [],
        "radar_only": False,
    }
    vault.write_note(
        settings.folder / "Sessions" / f"{stem}.md", {**base, **props}, body
    )
    return stem


def add_signal(settings, stem, repo, observed="2026-10-01", **props):
    base = {
        "type": "signal",
        "source": "note",
        "kind": "note",
        "about": [f"[[Repo - {repo}]]"],
        "observed": observed,
        "status": "open",
    }
    vault.write_note(settings.folder / "Signals" / f"{stem}.md", {**base, **props})


def add_pr(settings, repo, age):
    add_signal(
        settings,
        f"PR {repo} {age}",
        repo,
        kind="aging_pr",
        age_days=age,
        source="github",
    )


def titles(result):
    return [spot["title"] for spot in result["blind_spots"]]


def test_aging_pr_fires_at_threshold_and_not_below(settings):
    add_pr(settings, "claude", 7)
    add_pr(settings, "other", 6)
    result = detect.detect(settings, TODAY)
    assert titles(result) == ["PR open 7 days: claude"]
    spot = result["blind_spots"][0]
    assert spot["detector"] == "aging_commitments"
    assert spot["why_missed"] == "No activity since opening"
    assert spot["score"] == 1.0
    assert spot["evidence"] == ["PR claude 7"]


def test_resolved_pr_is_ignored(settings):
    add_signal(
        settings, "PR", "claude", kind="aging_pr", age_days=30, status="resolved"
    )
    assert titles(detect.detect(settings, TODAY)) == []


def test_silence_fires_when_no_session_in_window(settings):
    add_repo(settings, "claude")
    add_signal(settings, "s1", "claude")
    add_session(settings, "claude", "2026-09-24")
    result = detect.detect(settings, TODAY)
    assert titles(result) == ["claude: signals but no sessions in 14 days"]
    assert result["blind_spots"][0]["score"] == 1


def test_silence_quiet_on_the_edge_day(settings):
    add_repo(settings, "claude")
    add_signal(settings, "s1", "claude")
    add_session(settings, "claude", "2026-09-25")
    assert titles(detect.detect(settings, TODAY)) == []


def test_silence_needs_recent_signals(settings):
    add_repo(settings, "claude")
    add_signal(settings, "old", "claude", observed="2026-06-01")
    assert titles(detect.detect(settings, TODAY)) == []


def test_repeated_correction_fires_at_threshold(settings):
    add_signal(settings, "Correction Use uv", "claude", kind="correction", count=3)
    add_signal(settings, "Correction Twice", "claude", kind="correction", count=2)
    result = detect.detect(settings, TODAY)
    assert titles(result) == ["Told Claude 3 times: Use uv"]
    assert result["blind_spots"][0]["why_missed"].startswith("The same correction")
    assert result["blind_spots"][0]["score"] == 3


def test_not_done_fires_for_old_session_item(settings):
    add_session(settings, "claude", "2026-10-06", not_done=["wire the retry handler"])
    result = detect.detect(settings, TODAY)
    assert titles(result) == ["Left not done: wire the retry handler"]
    assert result["blind_spots"][0]["score"] == 1


def test_not_done_quiet_when_session_is_recent(settings):
    add_session(settings, "claude", "2026-10-07", not_done=["wire the retry handler"])
    assert titles(detect.detect(settings, TODAY)) == []


def test_not_done_quiet_when_later_prompt_shares_three_words(settings):
    add_session(settings, "claude", "2026-10-01", not_done=["wire the retry handler"])
    add_session(settings, "claude", "2026-10-02", body="finish retry handler wire up\n")
    assert titles(detect.detect(settings, TODAY)) == []


def test_not_done_fires_when_later_prompt_shares_only_two_words(settings):
    add_session(settings, "claude", "2026-10-01", not_done=["wire the retry handler"])
    add_session(settings, "claude", "2026-10-02", body="retry handler tests\n")
    assert titles(detect.detect(settings, TODAY)) == [
        "Left not done: wire the retry handler"
    ]


def test_not_done_ignores_later_session_in_another_repo(settings):
    add_session(settings, "claude", "2026-10-01", not_done=["wire the retry handler"])
    add_session(settings, "other", "2026-10-02", body="wire retry handler\n")
    assert len(titles(detect.detect(settings, TODAY))) == 1


def test_strong_signal_low_attention_edges(settings):
    add_repo(settings, "claude")
    for number in range(3):
        add_signal(settings, f"s{number}", "claude")
    add_session(settings, "claude", "2026-10-08")
    result = detect.detect(settings, TODAY)
    assert [spot["detector"] for spot in result["blind_spots"]] == [
        "strong_signal_low_attention"
    ]
    assert result["blind_spots"][0]["score"] == 1.5


def test_strong_signal_quiet_with_two_sessions_or_two_signals(settings):
    add_repo(settings, "claude")
    add_repo(settings, "other")
    for number in range(3):
        add_signal(settings, f"s{number}", "claude")
    add_session(settings, "claude", "2026-10-07")
    add_session(settings, "claude", "2026-10-08")
    for number in range(2):
        add_signal(settings, f"o{number}", "other")
    add_session(settings, "other", "2026-10-08")
    assert titles(detect.detect(settings, TODAY)) == []


def test_radar_only_sessions_do_not_count(settings):
    add_repo(settings, "claude")
    add_signal(settings, "s1", "claude")
    add_session(settings, "claude", "2026-10-08", radar_only=True)
    assert len(titles(detect.detect(settings, TODAY))) == 1


def test_out_of_scope_entry_suppresses_and_reports(settings):
    settings.config["out_of_scope"] = ["CLAUDE"]
    add_pr(settings, "claude", 9)
    result = detect.detect(settings, TODAY)
    assert result["blind_spots"] == []
    assert result["suppressed"][0]["title"] == "PR open 9 days: claude"
    assert result["suppressed"][0]["matched"] == "CLAUDE"


def test_commitments_are_not_capped_and_come_first_by_score(settings):
    settings.config["check_in"]["max_blind_spots"] = 2
    for repo, age in [("a", 7), ("b", 21), ("c", 14)]:
        add_pr(settings, repo, age)
    assert titles(detect.detect(settings, TODAY)) == [
        "PR open 21 days: b",
        "PR open 14 days: c",
        "PR open 7 days: a",
    ]


def test_cap_keeps_highest_scoring_blind_spots_after_commitments(settings):
    settings.config["check_in"]["max_blind_spots"] = 1
    add_pr(settings, "a", 7)
    for name, count in [("one", 3), ("two", 5)]:
        add_signal(settings, f"Correction {name}", "x", kind="correction", count=count)
    assert titles(detect.detect(settings, TODAY)) == [
        "PR open 7 days: a",
        "Told Claude 5 times: two",
    ]


def test_same_evidence_from_two_detectors_is_one_blind_spot(settings):
    add_repo(settings, "claude")
    for number in range(3):
        add_signal(settings, f"s{number}", "claude")
    result = detect.detect(settings, TODAY)
    assert len(result["blind_spots"]) == 1
    assert result["blind_spots"][0]["detector"] == (
        "silence, strong_signal_low_attention"
    )


def test_blind_spot_note_written_then_updated_keeping_first_seen(settings):
    add_pr(settings, "claude", 7)
    detect.detect(settings, date(2026, 10, 8))
    path = settings.folder / "Blind spots" / "PR open 7 days claude.md"
    props, _ = vault.read_note(path)
    assert props["status"] == "open"
    assert props["evidence"] == ["[[PR claude 7]]"]
    assert props["first_seen"] == "2026-10-08"
    detect.detect(settings, TODAY)
    props, _ = vault.read_note(path)
    assert (props["first_seen"], props["last_seen"]) == ("2026-10-08", "2026-10-09")
    assert props["evidence_count"] == 1


def test_result_includes_note_name(settings):
    add_pr(settings, "claude", 7)
    spot = detect.detect(settings, TODAY)["blind_spots"][0]
    assert spot["note"] == "PR open 7 days claude"


def answered(settings, title_stem, status, evidence_at):
    path = settings.folder / "Blind spots" / f"{title_stem}.md"
    vault.write_note(
        path, {"type": "blind_spot", "status": status, "evidence_count": evidence_at}
    )
    vault.write_note(
        settings.folder / "Feedback" / "fb-0001.md",
        {
            "type": "feedback",
            "responds_to": f"[[{title_stem}]]",
            "response": status,
            "evidence_count_at": evidence_at,
            "date": "2026-10-01",
        },
    )


SILENT = "claude signals but no sessions in 14 days"


def silent_repo(settings, signals):
    add_repo(settings, "claude")
    for number in range(signals):
        add_signal(settings, f"s{number}", "claude")


def test_known_stays_quiet_until_evidence_grows(settings):
    silent_repo(settings, 1)
    answered(settings, SILENT, "known", 1)
    assert titles(detect.detect(settings, TODAY)) == []
    add_signal(settings, "s9", "claude")
    spot = detect.detect(settings, TODAY)["blind_spots"][0]
    assert not spot["why_missed"].startswith("Grew since")


def test_out_of_scope_status_stays_quiet_until_evidence_grows(settings):
    silent_repo(settings, 1)
    answered(settings, SILENT, "out_of_scope", 1)
    assert titles(detect.detect(settings, TODAY)) == []


def test_watch_resurfaces_only_when_evidence_grew(settings):
    silent_repo(settings, 1)
    answered(settings, SILENT, "watch", 1)
    assert titles(detect.detect(settings, TODAY)) == []
    add_signal(settings, "s9", "claude")
    spot = detect.detect(settings, TODAY)["blind_spots"][0]
    assert spot["why_missed"].startswith("Grew since you said watch: ")


def test_aging_prs_in_one_repo_are_one_commitment(settings):
    add_pr(settings, "claude", 9)
    add_pr(settings, "claude", 30)
    add_pr(settings, "claude", 3)
    result = detect.detect(settings, TODAY)
    assert titles(result) == ["2 PRs open, oldest 30 days: claude"]
    assert result["blind_spots"][0]["evidence"] == ["PR claude 30", "PR claude 9"]


def test_a_commitment_merged_with_silence_stays_a_commitment(settings):
    add_repo(settings, "quiet")
    add_pr(settings, "quiet", 9)
    spot = detect.detect(settings, TODAY)["blind_spots"][0]
    assert detect.is_commitment(spot)


def test_counts_read_as_singular_for_one(settings):
    add_repo(settings, "claude")
    add_signal(settings, "s1", "claude")
    spot = detect.detect(settings, TODAY)["blind_spots"][0]
    assert spot["why_missed"].startswith("1 open signal and")
