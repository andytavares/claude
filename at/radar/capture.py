import fnmatch
import json
from datetime import datetime
from pathlib import Path

QUEUE = ".queue.jsonl"


def capture(settings, payload):
    options = settings.config["capture"]
    transcript = payload.get("transcript_path")
    if not options["sessions"] or not transcript:
        return
    if is_skipped(payload.get("cwd", ""), options["skip_paths"]):
        return
    entry = {
        "transcript_path": transcript,
        "cwd": payload.get("cwd", ""),
        "session_id": payload.get("session_id", ""),
        "ended_at": datetime.now().astimezone().isoformat(),
    }
    settings.folder.mkdir(parents=True, exist_ok=True)
    with (settings.folder / QUEUE).open("a") as stream:
        stream.write(json.dumps(entry) + "\n")


def is_skipped(cwd, patterns):
    return any(fnmatch.fnmatch(cwd, str(Path(p).expanduser())) for p in patterns)
