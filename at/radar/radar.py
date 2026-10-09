#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml==6.0.2"]
# ///
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import vault

NOT_INSTALLED = "Radar is not installed: run ./install.sh --radar --vault <dir>"


def today():
    return datetime.now().astimezone().date()


def run_init(args, home):
    settings = vault.init_vault(home, args.vault)
    print(f"Radar uses {settings.vault}; settings in {vault.CONFIG_NOTE}")


def run_capture(args, settings, home):
    import capture

    capture.capture(settings, json.loads(sys.stdin.read() or "{}"))


def run_digest(args, settings, home):
    import digest

    print(f"{len(digest.digest(settings, home))} sessions digested")


def run_pull(args, settings, home):
    import sources

    print(json.dumps(sources.pull(settings, home), indent=2))


def run_note(args, settings, home):
    import signals

    meta = {"about": args.about, "theme": args.theme, "source": args.source}
    print(signals.add_note(settings, args.text, meta))


def run_entities(args, settings, home):
    import signals

    print(json.dumps(signals.entities(settings), indent=2))


def run_checkin(args, settings, home):
    import checkin

    print(json.dumps(checkin.checkin(settings, home, today()), indent=2))


def run_answer(args, settings, home):
    import feedback

    print(feedback.answer(settings, args.number, args.response, args.note, today()))


def run_nudge(args, settings, home):
    import checkin

    line = checkin.nudge(settings, today())
    if line:
        context = {"hookEventName": "SessionStart", "additionalContext": line}
        print(json.dumps({"hookSpecificOutput": context}))


COMMANDS = {
    "capture": run_capture,
    "digest": run_digest,
    "pull": run_pull,
    "note": run_note,
    "entities": run_entities,
    "checkin": run_checkin,
    "answer": run_answer,
    "nudge": run_nudge,
}


def parse_args():
    parser = argparse.ArgumentParser(prog="radar")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init").add_argument("vault")
    for name in ["capture", "digest", "pull", "entities", "checkin", "nudge"]:
        commands.add_parser(name)
    note = commands.add_parser("note")
    note.add_argument("text")
    note.add_argument("--about", action="append", default=[])
    note.add_argument("--theme")
    note.add_argument("--source", default="note")
    answer = commands.add_parser("answer")
    answer.add_argument("number", type=int)
    answer.add_argument("response", choices=["act", "watch", "known", "out_of_scope"])
    answer.add_argument("--note")
    return parser.parse_args()


def main():
    args, home = parse_args(), Path.home()
    if args.command == "init":
        return run_init(args, home)
    settings = vault.load_settings(home)
    if settings is not None:
        return COMMANDS[args.command](args, settings, home)
    if args.command not in ("capture", "nudge"):
        sys.exit(NOT_INSTALLED)


if __name__ == "__main__":
    main()
