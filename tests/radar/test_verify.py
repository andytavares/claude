import pytest
import vault
import verify


@pytest.fixture
def settings(tmp_path):
    return vault.Settings(tmp_path, tmp_path / "Radar", {})


def evidence(settings, name, props=None, body=""):
    path = settings.folder / "Entities" / f"{name}.md"
    vault.write_note(path, props or {"type": "entity"}, body)


def pitch(settings, body):
    path = settings.folder / "Pitches" / "Pitch.md"
    vault.write_note(path, {"type": "pitch"}, body)
    return path


def check(settings, body):
    return verify.verify(settings, pitch(settings, body))


def test_number_found_in_linked_note_properties_passes(settings):
    evidence(settings, "Tool - GitHub", {"type": "entity", "signal_total": 14})
    assert check(settings, "14 incidents hit us [[Tool - GitHub]]") == []


def test_number_found_in_linked_note_body_passes(settings):
    evidence(settings, "Tool - GitHub", body="Cost was 250 per seat")
    assert check(settings, "Seats cost 250 [[Tool - GitHub]]") == []


def test_invented_number_fails_with_its_line(settings):
    evidence(settings, "Tool - GitHub", {"type": "entity", "signal_total": 14})
    result = check(settings, "intro\n99 incidents [[Tool - GitHub]]")
    assert result == ["line 5: 99 is not in a linked note"]


def test_number_without_a_link_fails(settings):
    assert check(settings, "We lost 12 builds") == [
        "line 4: 12 has no linked note on its line"
    ]


def test_link_to_a_missing_note_fails(settings):
    assert check(settings, "We lost 12 builds [[Nowhere]]") == [
        "line 4: 12 is not in a linked note"
    ]


@pytest.mark.parametrize(
    "line",
    [
        "Seen on 2026-10-03",
        "Week 2026-W41 was bad",
        "Planned for Q3 and H2",
        "Since 2024 it grew",
        "1. First step",
        "Read [[Tool - 2026 Plan]] now",
        "It takes 6 weeks",
        "It takes 6-month effort and 3 days",
        "About 2.5 quarters or 10 hours",
    ],
)
def test_ignored_forms_pass_without_a_link(settings, line):
    assert check(settings, line) == []


def test_commas_and_percent_are_ignored_when_matching(settings):
    evidence(settings, "Tool - GitHub", body="1234 builds failed, 40 were retried")
    assert check(settings, "1,234 builds [[Tool - GitHub]]") == []
    assert check(settings, "40% retried [[Tool - GitHub]]") == []


def test_dates_in_evidence_do_not_support_a_number(settings):
    evidence(settings, "Tool - GitHub", body="seen 2026-10-03")
    assert check(settings, "03 cases [[Tool - GitHub]]") == [
        "line 4: 03 is not in a linked note"
    ]


def test_a_link_on_another_line_does_not_count(settings):
    evidence(settings, "Tool - GitHub", {"type": "entity", "signal_total": 14})
    assert check(settings, "[[Tool - GitHub]]\n14 incidents") == [
        "line 5: 14 has no linked note on its line"
    ]
