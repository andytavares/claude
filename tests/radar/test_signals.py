import signals
import vault


def make_settings(tmp_path):
    return vault.init_vault(tmp_path, tmp_path / "Notes")


def test_add_note_writes_a_signal_with_links(tmp_path):
    settings = make_settings(tmp_path)
    path = signals.add_note(
        settings, "Auth is flaky", {"about": ["Area - Auth"], "theme": "Reliability"}
    )
    props, body = vault.read_note(path)
    assert path.parent == settings.folder / "Signals"
    assert path.name.endswith(" Auth is flaky.md")
    assert props["type"] == "signal"
    assert props["source"] == props["kind"] == "note"
    assert props["about"] == ["[[Area - Auth]]"]
    assert props["theme"] == "[[Reliability]]"
    assert props["status"] == "open"
    assert props["severity"] == 2
    assert body.strip() == "Auth is flaky"


def test_add_note_without_theme_stores_null(tmp_path):
    settings = make_settings(tmp_path)
    path = signals.add_note(settings, "x", {})
    props, _ = vault.read_note(path)
    assert props["theme"] is None
    assert props["about"] == []


def test_add_note_creates_entities_and_theme(tmp_path):
    settings = make_settings(tmp_path)
    meta = {"about": ["Person - Sam", "Repo - claude", "Misc"], "theme": "Growth"}
    signals.add_note(settings, "t", meta)
    entities = settings.folder / "Entities"
    assert vault.read_note(entities / "Person - Sam.md")[0] == {
        "type": "entity",
        "kind": "person",
    }
    assert vault.read_note(entities / "Repo - claude.md")[0]["kind"] == "repo"
    assert vault.read_note(entities / "Misc.md")[0]["kind"] == "area"
    assert vault.read_note(settings.folder / "Themes" / "Growth.md")[0] == {
        "type": "theme"
    }


def test_add_note_keeps_an_edited_entity(tmp_path):
    settings = make_settings(tmp_path)
    entity = settings.folder / "Entities" / "Area - Auth.md"
    vault.write_note(entity, {"type": "entity", "kind": "area", "owner": "me"}, "mine")
    signals.add_note(settings, "t", {"about": ["Area - Auth"]})
    props, body = vault.read_note(entity)
    assert props["owner"] == "me"
    assert body.strip() == "mine"


def test_add_note_numbers_a_filename_collision(tmp_path):
    settings = make_settings(tmp_path)
    first = signals.add_note(settings, "same", {})
    second = signals.add_note(settings, "same", {})
    third = signals.add_note(settings, "same", {})
    assert second.name == first.name.replace(".md", " 2.md")
    assert third.name == first.name.replace(".md", " 3.md")


def test_entities_lists_sorted_names_from_entities_and_themes(tmp_path):
    settings = make_settings(tmp_path)
    signals.add_note(settings, "t", {"about": ["Repo - b", "Area - a"], "theme": "Zed"})
    assert signals.entities(settings) == ["Area - a", "Repo - b", "Zed"]


def test_add_note_records_the_pasted_source(tmp_path):
    settings = make_settings(tmp_path)
    path = signals.add_note(settings, "build red", {"source": "Buildkite"})
    props, _ = vault.read_note(path)
    assert props["source"] == "buildkite"
    assert props["kind"] == "note"
