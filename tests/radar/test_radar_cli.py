import json
import os
import subprocess
from pathlib import Path

import pytest

RADAR = Path(__file__).parents[2] / "at" / "bin" / "radar"


@pytest.fixture
def home(tmp_path):
    subprocess.run([RADAR, "init", tmp_path / "vault"], env=env(tmp_path), check=True)
    return tmp_path


def env(home, **extra):
    return {**os.environ, "HOME": str(home), **extra}


def capture(home, **extra):
    payload = json.dumps(
        {"transcript_path": "/x.jsonl", "cwd": "/x", "session_id": "s1"}
    )
    subprocess.run(
        [RADAR, "capture"], input=payload, text=True, env=env(home, **extra), check=True
    )
    return home / "vault" / "Radar" / ".queue.jsonl"


def test_capture_queues_an_ordinary_session(home):
    assert capture(home).read_text().count("\n") == 1


def test_capture_skips_a_foundry_agent_session(home):
    assert not capture(home, FOUNDRY_RUN="1").exists()


def test_nudge_is_silent_in_a_foundry_agent_session(home):
    opportunities = home / "vault" / "Radar" / "Opportunities"
    (opportunities / "Mirror.md").write_text(
        "---\ntype: opportunity\nstatus: candidate\nfirst_seen: '2026-10-01'\n---\n"
    )
    run = lambda **extra: subprocess.run(
        [RADAR, "nudge"],
        capture_output=True,
        text=True,
        env=env(home, **extra),
        check=True,
    )
    assert run(FOUNDRY_RUN="1").stdout == ""
    assert "Radar:" in run().stdout
