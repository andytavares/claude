import json

import pytest
import vault


@pytest.fixture
def home(tmp_path):
    vault_dir = tmp_path / "Notes"
    vault_dir.mkdir()
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "at-radar.json").write_text(
        json.dumps({"vault": str(vault_dir)})
    )
    return tmp_path


def test_no_pointer_file_means_radar_is_off(tmp_path):
    assert vault.load_settings(tmp_path) is None


def test_defaults_apply_without_a_config_note(home):
    settings = vault.load_settings(home)
    assert settings.folder == home / "Notes" / "Radar"
    assert settings.config["check_in"]["max_blind_spots"] == 3


def test_config_note_overrides_one_key_and_keeps_the_rest(home):
    (home / "Notes" / "Radar Config.md").write_text(
        "---\ncheck_in:\n  max_blind_spots: 5\nradar_folder: Watch\n---\nBody\n"
    )
    settings = vault.load_settings(home)
    assert settings.config["check_in"]["max_blind_spots"] == 5
    assert settings.config["check_in"]["nudge_at_session_start"] == "daily"
    assert settings.folder == home / "Notes" / "Watch"


def test_write_note_creates_properties_and_body(tmp_path):
    path = tmp_path / "Signals" / "a.md"
    vault.write_note(path, {"type": "signal", "about": ["[[Repo - claude]]"]}, "hello")
    props, body = vault.read_note(path)
    assert props == {"type": "signal", "about": ["[[Repo - claude]]"]}
    assert body.strip() == "hello"


def test_write_note_updates_its_properties_and_keeps_user_edits(tmp_path):
    path = tmp_path / "a.md"
    vault.write_note(path, {"type": "signal", "count": 1}, "original")
    path.write_text(path.read_text().replace("original", "my own words"))
    path.write_text(path.read_text().replace("count: 1", "count: 1\nmine: kept"))
    vault.write_note(path, {"count": 2}, "replacement body")
    props, body = vault.read_note(path)
    assert props == {"type": "signal", "count": 2, "mine": "kept"}
    assert body.strip() == "my own words"


def test_read_note_without_front_matter(tmp_path):
    path = tmp_path / "plain.md"
    path.write_text("just text\n")
    assert vault.read_note(path) == ({}, "just text\n")


def test_note_name_is_filename_safe():
    assert vault.note_name('Fix: a/b "quoted" #1?') == "Fix a-b quoted 1"


def test_link_wraps_a_note_name():
    assert vault.link("Repo - claude") == "[[Repo - claude]]"


def test_notes_lists_notes_of_one_folder_with_properties(home):
    settings = vault.load_settings(home)
    vault.write_note(settings.folder / "Signals" / "one.md", {"type": "signal"}, "")
    found = list(vault.notes(settings, "Signals"))
    assert [(p.name, props["type"]) for p, props in found] == [("one.md", "signal")]


def test_init_vault_creates_folders_and_never_overwrites_the_config_note(tmp_path):
    vault_dir = tmp_path / "Notes"
    vault_dir.mkdir()
    settings = vault.init_vault(tmp_path, vault_dir)
    assert (settings.folder / "Opportunities").is_dir()
    note = vault_dir / "Radar Config.md"
    note.write_text(
        note.read_text().replace("max_blind_spots: 3", "max_blind_spots: 7")
    )
    settings = vault.init_vault(tmp_path, vault_dir)
    assert settings.config["check_in"]["max_blind_spots"] == 7


def test_state_round_trips_and_starts_empty(home):
    settings = vault.load_settings(home)
    assert vault.load_state(settings) == {}
    vault.save_state(settings, {"nudged_on": "2026-10-09"})
    assert vault.load_state(settings) == {"nudged_on": "2026-10-09"}


def test_init_vault_creates_a_missing_folder_as_an_obsidian_vault(tmp_path):
    vault_dir = tmp_path / "new" / "Notes"
    vault.init_vault(tmp_path, vault_dir)
    assert (vault_dir / ".obsidian").is_dir()
    assert (vault_dir / "Radar Config.md").is_file()


def test_init_vault_seeds_context_notes_and_board_once(tmp_path):
    vault_dir = tmp_path / "Notes"
    settings = vault.init_vault(tmp_path, vault_dir)
    ladder = settings.folder / "Context" / "Ladder.md"
    props, body = vault.read_note(ladder)
    assert props["provisional"] is True
    assert "handbook.gitlab.com" in body
    assert (settings.folder / "Context" / "Priorities.md").is_file()
    board = (settings.folder / "Board.base").read_text()
    assert 'file.inFolder("Radar/Opportunities")' in board
    ladder.write_text("my ladder\n")
    vault.init_vault(tmp_path, vault_dir)
    assert ladder.read_text() == "my ladder\n"


def test_defaults_describe_opportunities_not_tasks(tmp_path):
    settings = vault.init_vault(tmp_path, tmp_path / "Notes")
    assert settings.config["opportunities"]["min_weeks"] == 6
    assert settings.config["status_pages"][0]["url"] == "https://www.githubstatus.com"
    assert "detectors" not in settings.config
    assert (settings.folder / "Opportunities").is_dir()
    assert not (settings.folder / "Blind spots").exists()
