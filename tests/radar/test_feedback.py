from datetime import date

import feedback
import pytest
import vault

TODAY = date(2026, 10, 9)


@pytest.fixture
def settings(tmp_path):
    settings = vault.init_vault(tmp_path, tmp_path / "Notes")
    for name, count in [("First spot", 2), ("Second spot", 5)]:
        vault.write_note(
            settings.folder / "Blind spots" / f"{name}.md",
            {"type": "blind_spot", "status": "open", "evidence_count": count},
        )
    state = vault.load_state(settings)
    vault.save_state(settings, {**state, "last_checkin": ["First spot", "Second spot"]})
    return settings


def test_answer_writes_numbered_feedback_and_updates_status(settings):
    path = feedback.answer(
        settings, {"number": 2, "response": "watch", "note": "keep an eye"}, TODAY
    )
    assert path == settings.folder / "Feedback" / "fb-0001.md"
    props, _ = vault.read_note(path)
    assert props == {
        "type": "feedback",
        "responds_to": "[[Second spot]]",
        "response": "watch",
        "evidence_count_at": 5,
        "date": "2026-10-09",
        "note": "keep an eye",
    }
    spot, _ = vault.read_note(settings.folder / "Blind spots" / "Second spot.md")
    assert spot["status"] == "watch"


def test_second_answer_gets_next_number(settings):
    feedback.answer(settings, {"number": 1, "response": "known", "note": None}, TODAY)
    path = feedback.answer(
        settings, {"number": 2, "response": "act", "note": None}, TODAY
    )
    assert path.name == "fb-0002.md"


@pytest.mark.parametrize("number", [0, 3])
def test_number_out_of_range_names_valid_range(settings, number):
    with pytest.raises(SystemExit) as error:
        feedback.answer(
            settings, {"number": number, "response": "known", "note": None}, TODAY
        )
    assert "1 to 2" in str(error.value)
    assert not list((settings.folder / "Feedback").glob("*.md"))


def test_no_checkin_yet_is_a_plain_message(tmp_path):
    settings = vault.init_vault(tmp_path, tmp_path / "Notes")
    with pytest.raises(SystemExit) as error:
        feedback.answer(
            settings, {"number": 1, "response": "known", "note": None}, TODAY
        )
    assert "check-in" in str(error.value)
