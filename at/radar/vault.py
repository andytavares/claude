import copy
import json
import os
import re
import tempfile
from pathlib import Path
from typing import NamedTuple

import yaml

POINTER = Path(".claude") / "at-radar.json"
CONFIG_NOTE = "Radar Config.md"
FOLDERS = [
    "Sessions",
    "Signals",
    "Entities",
    "Themes",
    "Blind spots",
    "Feedback",
    "Briefs",
]
DEFAULTS = {
    "radar_folder": "Radar",
    "capture": {"sessions": True, "prompt_text": "first-line", "skip_paths": []},
    "sources": {"github": True, "linear": False, "memory_corrections": True},
    "windows": {"attention_days": 30, "signal_days": 90},
    "check_in": {"max_blind_spots": 3, "nudge_at_session_start": "daily"},
    "detectors": {"aging_pr_days": 7, "silence_days": 14, "repeated_correction": 3},
    "priorities": [],
    "out_of_scope": [],
}
CONFIG_BODY = """# Radar settings

The properties above are the radar's settings. Edit them here; the next check-in uses them.

- **radar_folder**: where the radar keeps its notes in this vault.
- **capture**: whether Claude sessions are recorded, how much of each prompt is kept
  (`none`, `first-line` or `full`), and repo paths never recorded.
- **sources**: extra signals to pull: your open GitHub PRs, Linear issues (when a
  session has the Linear connector), and corrections you gave Claude more than once.
- **windows**: how many days of sessions count as attention, and of signals as evidence.
- **check_in**: how many blind spots one check-in shows, and whether the first session
  of the day gets a one-line reminder (`off`, `daily` or `every`).
- **detectors**: when a PR counts as aging, a repo as silent, a correction as repeated.
- **priorities**: what you mean to spend time on, each with an `until` date.
- **out_of_scope**: topics never to raise; a blind spot whose title contains one is held back.
"""


class Settings(NamedTuple):
    vault: Path
    folder: Path
    config: dict


def load_settings(home=None):
    pointer = Path(home or Path.home()) / POINTER
    if not pointer.is_file():
        return None
    vault_dir = Path(json.loads(pointer.read_text())["vault"])
    config = merged(DEFAULTS, read_note(vault_dir / CONFIG_NOTE)[0])
    return Settings(vault_dir, vault_dir / config["radar_folder"], config)


def merged(defaults, overrides):
    result = copy.deepcopy(defaults)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merged(result[key], value)
        else:
            result[key] = value
    return result


def init_vault(home, vault_dir):
    pointer = Path(home) / POINTER
    pointer.parent.mkdir(parents=True, exist_ok=True)
    pointer.write_text(json.dumps({"vault": str(Path(vault_dir).resolve())}) + "\n")
    note = Path(vault_dir) / CONFIG_NOTE
    if not note.exists():
        write_note(note, DEFAULTS, CONFIG_BODY)
    settings = load_settings(home)
    for folder in FOLDERS:
        (settings.folder / folder).mkdir(parents=True, exist_ok=True)
    return settings


def read_note(path):
    path = Path(path)
    if not path.is_file():
        return {}, ""
    text = path.read_text()
    match = re.match(r"---\n(.*?)\n---\n?(.*)", text, re.DOTALL)
    if not match:
        return {}, text
    return yaml.safe_load(match.group(1)) or {}, match.group(2)


def write_note(path, properties, body=""):
    path = Path(path)
    existing, existing_body = read_note(path)
    keep_body = path.exists()
    front = yaml.safe_dump(
        {**existing, **properties}, sort_keys=False, allow_unicode=True
    )
    text = f"---\n{front}---\n{existing_body if keep_body else body}"
    atomic_write(path, text if text.endswith("\n") else text + "\n")


def atomic_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(handle, "w") as stream:
        stream.write(text)
    os.replace(temporary, path)


def notes(settings, folder):
    for path in sorted((settings.folder / folder).glob("*.md")):
        yield path, read_note(path)[0]


def note_name(text):
    cleaned = re.sub(r"[\\/]", "-", text)
    cleaned = re.sub(r"[^\w\s.-]", "", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()[:100]


def link(name):
    return f"[[{name}]]"


def load_state(settings):
    path = settings.folder / ".state.json"
    return json.loads(path.read_text()) if path.is_file() else {}


def save_state(settings, state):
    atomic_write(settings.folder / ".state.json", json.dumps(state, indent=2) + "\n")
