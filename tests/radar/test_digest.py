import json
import shutil
from pathlib import Path

import digest
import pytest
import vault

FIXTURES = Path(__file__).parent / "fixtures" / "transcripts"


@pytest.fixture
def settings(tmp_path):
    return vault.init_vault(tmp_path, tmp_path / "Notes")


def queue(settings, tmp_path, fixture, session_id):
    transcript = tmp_path / fixture
    if not transcript.exists():
        shutil.copy(FIXTURES / fixture, transcript)
    entry = {
        "transcript_path": str(transcript),
        "cwd": "/x",
        "session_id": session_id,
        "ended_at": "2026-10-09T00:00:00+00:00",
    }
    with (settings.folder / ".queue.jsonl").open("a") as stream:
        stream.write(json.dumps(entry) + "\n")
    return transcript


def test_normal_session_note_properties(settings, tmp_path):
    queue(settings, tmp_path, "normal.jsonl", "abcdef1234567890")
    written = digest.digest(settings, tmp_path)
    expected = settings.folder / "Sessions" / "2026-10-01 claude abcdef12.md"
    assert written == [expected]
    props, body = vault.read_note(expected)
    assert props == {
        "type": "session",
        "repo": "[[Repo - claude]]",
        "branch": "main",
        "session_id": "abcdef1234567890",
        "started": "2026-10-01T09:00:00Z",
        "ended": "2026-10-01T09:30:00Z",
        "prompts": 2,
        "lines_added": 42,
        "lines_removed": 7,
        "prs": ["https://github.com/acme/widgets/pull/12"],
        "not_done": ["Docs still missing", "Release notes"],
        "radar_only": False,
    }
    assert body.strip().splitlines() == ["- Fix the login bug", "- Now add tests"]


def test_repo_entity_note_is_created_once_and_kept(settings, tmp_path):
    queue(settings, tmp_path, "normal.jsonl", "abcdef1234567890")
    digest.digest(settings, tmp_path)
    entity = settings.folder / "Entities" / "Repo - claude.md"
    assert vault.read_note(entity)[0] == {"type": "entity", "kind": "repo"}


def test_worktree_cwd_names_the_main_repo(settings, tmp_path):
    queue(settings, tmp_path, "worktree.jsonl", "wt123456789")
    (path,) = digest.digest(settings, tmp_path)
    assert vault.read_note(path)[0]["repo"] == "[[Repo - claude]]"


def test_radar_only_session_is_flagged(settings, tmp_path):
    queue(settings, tmp_path, "radar_only.jsonl", "ro123456789")
    (path,) = digest.digest(settings, tmp_path)
    props = vault.read_note(path)[0]
    assert props["radar_only"] is True
    assert props["prompts"] == 2


def test_rerun_writes_nothing(settings, tmp_path):
    queue(settings, tmp_path, "normal.jsonl", "abcdef1234567890")
    assert len(digest.digest(settings, tmp_path)) == 1
    assert digest.digest(settings, tmp_path) == []


def test_grown_transcript_updates_the_same_note(settings, tmp_path):
    transcript = queue(settings, tmp_path, "normal.jsonl", "abcdef1234567890")
    (first,) = digest.digest(settings, tmp_path)
    extra = {
        "type": "user",
        "timestamp": "2026-10-02T09:00:00Z",
        "message": {"content": "One more thing"},
    }
    with transcript.open("a") as stream:
        stream.write(json.dumps(extra) + "\n")
    (second,) = digest.digest(settings, tmp_path)
    assert second == first
    props, body = vault.read_note(second)
    assert props["prompts"] == 3
    assert props["ended"] == "2026-10-02T09:00:00Z"
    assert "- One more thing" in body


def test_secrets_are_redacted(settings, tmp_path):
    queue(settings, tmp_path, "secrets.jsonl", "se123456789")
    (path,) = digest.digest(settings, tmp_path)
    body = vault.read_note(path)[1]
    assert "ghp_" not in body
    assert "hunter2" not in body
    assert body.strip() == "- use [redacted] and [redacted] please"


def test_prompt_text_none_writes_no_lines(settings, tmp_path):
    settings.config["capture"]["prompt_text"] = "none"
    queue(settings, tmp_path, "normal.jsonl", "abcdef1234567890")
    (path,) = digest.digest(settings, tmp_path)
    assert vault.read_note(path)[1].strip() == ""
    assert vault.read_note(path)[0]["prompts"] == 2


def test_prompt_text_full_keeps_every_line(settings, tmp_path):
    settings.config["capture"]["prompt_text"] = "full"
    queue(settings, tmp_path, "normal.jsonl", "abcdef1234567890")
    (path,) = digest.digest(settings, tmp_path)
    assert "Fix the login bug\n  second line" in vault.read_note(path)[1]


def test_first_line_is_truncated_to_120_characters(settings, tmp_path):
    transcript = tmp_path / "long.jsonl"
    long_prompt = {
        "type": "user",
        "timestamp": "2026-10-05T08:00:00Z",
        "message": {"content": "x" * 300},
    }
    transcript.write_text(json.dumps(long_prompt) + "\n")
    queue(settings, tmp_path, "long.jsonl", "lg123456789")
    (path,) = digest.digest(settings, tmp_path)
    assert vault.read_note(path)[1].strip() == "- " + "x" * 120


def test_deleted_transcript_is_dropped_from_the_queue(settings, tmp_path):
    gone = queue(settings, tmp_path, "normal.jsonl", "abcdef1234567890")
    queue(settings, tmp_path, "worktree.jsonl", "wt123456789")
    gone.unlink()
    digest.digest(settings, tmp_path)
    lines = (settings.folder / ".queue.jsonl").read_text().splitlines()
    assert [json.loads(line)["session_id"] for line in lines] == ["wt123456789"]


def friction_note(settings):
    return settings.folder / "Signals" / "Friction GitHub abcdef12.md"


def test_friction_note_counts_tool_result_matches(settings, tmp_path):
    queue(settings, tmp_path, "friction.jsonl", "abcdef1234567890")
    (session,) = digest.digest(settings, tmp_path)
    props = vault.read_note(friction_note(settings))[0]
    assert props == {
        "type": "signal",
        "source": "session",
        "kind": "friction",
        "about": ["[[Tool - GitHub]]"],
        "theme": None,
        "observed": "2026-10-03",
        "status": "open",
        "severity": 1,
        "count": 2,
        "session": f"[[{session.stem}]]",
    }
    assert vault.read_note(session)[0]["friction"] == {"GitHub": 2}
    tool = settings.folder / "Entities" / "Tool - GitHub.md"
    assert vault.read_note(tool)[0] == {"type": "entity", "kind": "tool"}


def test_no_friction_note_without_a_match(settings, tmp_path):
    queue(settings, tmp_path, "normal.jsonl", "abcdef1234567890")
    (session,) = digest.digest(settings, tmp_path)
    assert list((settings.folder / "Signals").glob("Friction*")) == []
    assert "friction" not in vault.read_note(session)[0]


def test_disabled_friction_source_writes_nothing(settings, tmp_path):
    settings.config["sources"]["session_friction"] = False
    queue(settings, tmp_path, "friction.jsonl", "abcdef1234567890")
    (session,) = digest.digest(settings, tmp_path)
    assert not friction_note(settings).exists()
    assert "friction" not in vault.read_note(session)[0]


def test_match_in_a_users_own_prompt_does_not_count(settings, tmp_path):
    queue(settings, tmp_path, "friction.jsonl", "abcdef1234567890")
    digest.digest(settings, tmp_path)
    assert vault.read_note(friction_note(settings))[0]["count"] == 2


def test_redigest_updates_the_friction_count(settings, tmp_path):
    transcript = queue(settings, tmp_path, "friction.jsonl", "abcdef1234567890")
    digest.digest(settings, tmp_path)
    extra = {
        "type": "user",
        "timestamp": "2026-10-03T11:00:00Z",
        "message": {"content": [{"type": "tool_result", "content": "gh: HTTP 500: x"}]},
    }
    with transcript.open("a") as stream:
        stream.write(json.dumps(extra) + "\n")
    digest.digest(settings, tmp_path)
    assert vault.read_note(friction_note(settings))[0]["count"] == 3
    assert len(list((settings.folder / "Signals").glob("Friction*"))) == 1
