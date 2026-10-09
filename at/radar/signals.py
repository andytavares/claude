from datetime import datetime

import vault

ENTITY_KINDS = {"repo", "area", "person", "project"}


def today():
    return datetime.now().astimezone().date()


def add_note(settings, text, meta):
    props = {
        "type": "signal",
        "source": meta.get("source", "note").lower(),
        "kind": "note",
        "about": [vault.link(name) for name in meta.get("about", [])],
        "theme": vault.link(meta["theme"]) if meta.get("theme") else None,
        "observed": today().isoformat(),
        "status": "open",
        "severity": 2,
    }
    for name in meta.get("about", []):
        ensure_note(
            settings.folder / "Entities" / f"{name}.md",
            {"type": "entity", "kind": kind_of(name)},
        )
    if meta.get("theme"):
        ensure_note(
            settings.folder / "Themes" / f"{meta['theme']}.md", {"type": "theme"}
        )
    path = free_path(settings, text)
    vault.write_note(path, props, text)
    return path


def kind_of(name):
    prefix = name.split(" - ", 1)[0].lower() if " - " in name else ""
    return prefix if prefix in ENTITY_KINDS else "area"


def ensure_note(path, props):
    if not path.exists():
        vault.write_note(path, props)


def free_path(settings, text):
    stem = f"{today().isoformat()} {vault.note_name(text[:60])}"
    folder = settings.folder / "Signals"
    path = folder / f"{stem}.md"
    number = 2
    while path.exists():
        path = folder / f"{stem} {number}.md"
        number += 1
    return path


def entities(settings):
    names = []
    for folder in ("Entities", "Themes"):
        names += [p.stem for p, _ in vault.notes(settings, folder)]
    return sorted(names)
