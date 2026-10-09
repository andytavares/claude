from datetime import date

import feedback
import pytest
import vault

TODAY = date(2026, 10, 9)


@pytest.fixture
def settings(tmp_path):
    settings = vault.init_vault(tmp_path, tmp_path / "Notes")
    for name in ["Replace GitHub", "Speed up CI"]:
        vault.write_note(
            settings.folder / "Opportunities" / f"{name}.md",
            {"type": "opportunity", "status": "candidate"},
        )
    state = vault.load_state(settings)
    vault.save_state(
        settings, {**state, "last_checkin": ["Replace GitHub", "Speed up CI"]}
    )
    return settings


def opportunity(settings, name):
    return vault.read_note(settings.folder / "Opportunities" / f"{name}.md")[0]


def config(settings):
    return vault.read_note(settings.vault / vault.CONFIG_NOTE)


def test_feedback_note_has_contract_props_and_numbering(settings):
    reply = {"number": 2, "kind": "pursue", "text": "yes", "until": None}
    path = feedback.answer(settings, reply, TODAY)
    assert path == settings.folder / "Feedback" / "fb-0001.md"
    assert vault.read_note(path)[0] == {
        "type": "feedback",
        "kind": "pursue",
        "target": "[[Speed up CI]]",
        "text": "yes",
        "until": None,
        "who": "me",
        "date": "2026-10-09",
    }
    again = feedback.answer(settings, {"number": 1, "kind": "park"}, TODAY)
    assert again.name == "fb-0002.md"


@pytest.mark.parametrize(
    ("kind", "status"),
    [("pursue", "pursuing"), ("park", "parked"), ("reject", "rejected")],
)
def test_status_kinds_update_the_opportunity(settings, kind, status):
    feedback.answer(settings, {"number": 1, "kind": kind}, TODAY)
    assert opportunity(settings, "Replace GitHub")["status"] == status
    assert opportunity(settings, "Speed up CI")["status"] == "candidate"


def test_correction_only_writes_the_note(settings):
    path = feedback.answer(
        settings, {"number": 1, "kind": "correction", "text": "wrong team"}, TODAY
    )
    assert vault.read_note(path)[0]["text"] == "wrong team"
    assert opportunity(settings, "Replace GitHub")["status"] == "candidate"


def test_exists_rejects_and_records_program_keeping_config_body(settings):
    body = config(settings)[1]
    reply = {"number": 1, "kind": "exists", "text": "Platform owns it"}
    feedback.answer(settings, reply, TODAY)
    props, after = config(settings)
    assert props["existing_programs"] == [
        {"name": "Replace GitHub", "note": "Platform owns it"}
    ]
    assert after == body
    assert opportunity(settings, "Replace GitHub")["status"] == "rejected"


def test_out_of_scope_appends_area(settings):
    feedback.answer(
        settings, {"number": 2, "kind": "out_of_scope", "text": "Infra owns CI"}, TODAY
    )
    feedback.answer(
        settings, {"number": 1, "kind": "out_of_scope", "text": "Legal"}, TODAY
    )
    assert config(settings)[0]["out_of_scope"] == [
        {"area": "Speed up CI", "reason": "Infra owns CI"},
        {"area": "Replace GitHub", "reason": "Legal"},
    ]
    assert opportunity(settings, "Speed up CI")["status"] == "rejected"


def test_direction_needs_no_target_and_defaults_until_to_quarter_end(settings):
    reply = {"number": None, "kind": "direction", "text": "Cut build times"}
    path = feedback.answer(settings, reply, TODAY)
    assert vault.read_note(path)[0]["target"] is None
    assert config(settings)[0]["priorities"] == [
        {"text": "Cut build times", "who": "me", "until": "2026-12-31"}
    ]


def test_direction_keeps_given_until_and_who(settings):
    reply = {"kind": "direction", "text": "x", "until": "2027-01-15", "who": "VP"}
    feedback.answer(settings, reply, TODAY)
    assert config(settings)[0]["priorities"] == [
        {"text": "x", "who": "VP", "until": "2027-01-15"}
    ]


def test_weight_sets_one_dimension_and_keeps_the_others(settings):
    body = config(settings)[1]
    feedback.answer(settings, {"kind": "weight", "weight": "impact=0.4"}, TODAY)
    props, after = config(settings)
    assert props["weights"] == {
        "impact": 0.4,
        "reach": 0.2,
        "direction": 0.2,
        "promo_fit": 0.3,
    }
    assert after == body


def test_unknown_weight_dimension_names_valid_ones(settings):
    with pytest.raises(SystemExit) as error:
        feedback.answer(settings, {"kind": "weight", "weight": "luck=1"}, TODAY)
    assert "impact" in str(error.value)
    assert "promo_fit" in str(error.value)
    assert not list((settings.folder / "Feedback").glob("*.md"))


@pytest.mark.parametrize("number", [0, 3])
def test_number_out_of_range_names_valid_range(settings, number):
    with pytest.raises(SystemExit) as error:
        feedback.answer(settings, {"number": number, "kind": "pursue"}, TODAY)
    assert "1 to 2" in str(error.value)
    assert not list((settings.folder / "Feedback").glob("*.md"))
