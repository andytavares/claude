import json

import capture
import pytest
import vault


@pytest.fixture
def settings(tmp_path):
    return vault.init_vault(tmp_path, tmp_path / "Notes")


def queue_lines(settings):
    path = settings.folder / ".queue.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()]


def payload(**overrides):
    return {
        "transcript_path": "/t/a.jsonl",
        "cwd": "/x/repos/claude",
        "session_id": "abc12345-1",
        "reason": "exit",
        **overrides,
    }


def test_capture_appends_one_json_line_per_session(settings):
    capture.capture(settings, payload())
    capture.capture(settings, payload(session_id="second"))
    lines = queue_lines(settings)
    assert [line["session_id"] for line in lines] == ["abc12345-1", "second"]
    assert lines[0]["transcript_path"] == "/t/a.jsonl"
    assert lines[0]["cwd"] == "/x/repos/claude"
    assert lines[0]["ended_at"].startswith("20")


def test_capture_creates_the_folder(tmp_path):
    folder = tmp_path / "Notes" / "Radar"
    settings = vault.Settings(
        tmp_path / "Notes", folder, {"capture": {"sessions": True, "skip_paths": []}}
    )
    capture.capture(settings, payload())
    assert (folder / ".queue.jsonl").is_file()


def test_capture_does_nothing_when_disabled(settings):
    settings.config["capture"]["sessions"] = False
    capture.capture(settings, payload())
    assert not (settings.folder / ".queue.jsonl").exists()


def test_capture_does_nothing_without_a_transcript(settings):
    capture.capture(settings, {"cwd": "/x", "session_id": "s"})
    assert not (settings.folder / ".queue.jsonl").exists()


def test_capture_skips_matching_paths(settings):
    settings.config["capture"]["skip_paths"] = ["/x/private/*", "~/secret/*"]
    capture.capture(settings, payload(cwd="/x/private/thing"))
    capture.capture(
        settings, payload(cwd=str(__import__("pathlib").Path.home() / "secret/a"))
    )
    assert not (settings.folder / ".queue.jsonl").exists()
    capture.capture(settings, payload(cwd="/x/public"))
    assert len(queue_lines(settings)) == 1
