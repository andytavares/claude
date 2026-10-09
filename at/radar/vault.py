import copy
import json
import os
import re
import tempfile
from pathlib import Path
from typing import NamedTuple

import seeds
import yaml

POINTER = Path(".claude") / "at-radar.json"
CONFIG_NOTE = "Radar Config.md"
FOLDERS = [
    "Sessions",
    "Signals",
    "Entities",
    "Themes",
    "Opportunities",
    "Pitches",
    "Context",
    "Feedback",
    "Briefs",
]
DEFAULTS = seeds.DEFAULTS


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
    (Path(vault_dir) / ".obsidian").mkdir(parents=True, exist_ok=True)
    pointer = Path(home) / POINTER
    pointer.parent.mkdir(parents=True, exist_ok=True)
    pointer.write_text(json.dumps({"vault": str(Path(vault_dir).resolve())}) + "\n")
    note = Path(vault_dir) / CONFIG_NOTE
    if not note.exists():
        write_note(note, DEFAULTS, seeds.CONFIG_BODY)
    settings = load_settings(home)
    for folder in FOLDERS:
        (settings.folder / folder).mkdir(parents=True, exist_ok=True)
    seed_context(settings)
    return settings


def seed_context(settings):
    context = settings.folder / "Context"
    if not (context / "Ladder.md").exists():
        write_note(
            context / "Ladder.md",
            {"type": "context", "provisional": True},
            seeds.LADDER,
        )
    if not (context / "Priorities.md").exists():
        write_note(context / "Priorities.md", {"type": "context"}, seeds.PRIORITIES)
    board = settings.folder / "Board.base"
    if not board.exists():
        atomic_write(board, seeds.BOARD.format(folder=settings.config["radar_folder"]))


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
