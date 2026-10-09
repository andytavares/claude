from datetime import timedelta

import detect
import vault

SECTIONS = [
    "What changed because of your feedback",
    "Commitments",
    "Blind spots",
    "Held back",
    "Sources",
]


def run_digest(settings, home):
    import digest

    digest.digest(settings, home)


def run_pull(settings, home):
    import sources

    sources.pull(settings, home)


def recent_feedback(settings, today):
    start = str(today - timedelta(days=7))
    return [
        (path.stem, props)
        for path, props in vault.notes(settings, "Feedback")
        if str(props["date"])[:10] >= start
    ]


SHOWN_EVIDENCE = 5


def links(names):
    shown = ", ".join(vault.link(name) for name in names[:SHOWN_EVIDENCE])
    hidden = len(names) - SHOWN_EVIDENCE
    return f"{shown} and {hidden} more" if hidden > 0 else shown


def feedback_lines(applied):
    return [
        f"- {vault.link(stem)}: {props['response']} {props['responds_to']}"
        for stem, props in applied
    ]


def commitment_lines(commitments):
    return [
        f"{number}. {spot['title']} ({links(spot['evidence'])})"
        for number, spot in enumerate(commitments, 1)
    ]


def blind_spot_lines(spots, first_number):
    lines = []
    for number, spot in enumerate(spots, first_number):
        lines += [
            f"{number}. {spot['title']}",
            f"   - Detector: {spot['detector']}",
            f"   - Why it was missed: {spot['why_missed']}",
            f"   - Evidence: {links(spot['evidence'])}",
        ]
    return lines


def held_lines(held):
    return [f"- {spot['title']} (out of scope: {spot['matched']})" for spot in held]


def source_line(name, status):
    if status["ok"]:
        return f"- {name}: ok, {status['count']} items"
    return f"- {name}: failed: {status['error']}"


def source_lines(health):
    return [source_line(name, status) for name, status in health.items()]


def render(week, sections):
    parts = [f"# Radar check-in {week}"]
    for heading in SECTIONS:
        parts += ["", f"## {heading}", "", *(sections[heading] or ["None."])]
    return "\n".join(parts) + "\n"


def write_brief(settings, today, sections):
    year, week, _ = today.isocalendar()
    path = settings.folder / "Briefs" / f"{year}-W{week:02d}.md"
    vault.write_note(path, {"type": "brief", "date": str(today)})
    text = path.read_text()
    front = text[: text.index("\n---\n", 3) + 5]
    vault.atomic_write(path, front + render(f"{year}-W{week:02d}", sections))
    return path


def section_lines(spots, held, applied_and_health):
    applied, health = applied_and_health
    commitments = [spot for spot in spots if detect.is_commitment(spot)]
    others = [spot for spot in spots if not detect.is_commitment(spot)]
    return {
        SECTIONS[0]: feedback_lines(applied),
        SECTIONS[1]: commitment_lines(commitments),
        SECTIONS[2]: blind_spot_lines(others, len(commitments) + 1),
        SECTIONS[3]: held_lines(held),
        SECTIONS[4]: source_lines(health),
    }


def checkin(settings, home, today):
    run_digest(settings, home)
    run_pull(settings, home)
    found = detect.detect(settings, today)
    spots, held = found["blind_spots"], found["suppressed"]
    applied = recent_feedback(settings, today)
    health = vault.load_state(settings).get("sources", {})
    lines = section_lines(spots, held, (applied, health))
    path = write_brief(settings, today, lines)
    state = vault.load_state(settings)
    vault.save_state(settings, {**state, "last_checkin": [s["note"] for s in spots]})
    return {
        "brief": str(path),
        "blind_spots": spots,
        "suppressed": held,
        "feedback_applied": [stem for stem, _ in applied],
        "sources": health,
    }


def open_blind_spots(settings):
    return sum(
        props.get("status") == "open"
        for _, props in vault.notes(settings, "Blind spots")
    )


def due_today(settings, today):
    mode = settings.config["check_in"]["nudge_at_session_start"]
    if mode == "every":
        return True
    return mode == "daily" and vault.load_state(settings).get("nudged_on") != str(today)


def nudge(settings, today):
    count = open_blind_spots(settings)
    if not count or not due_today(settings, today):
        return None
    state = vault.load_state(settings)
    vault.save_state(settings, {**state, "nudged_on": str(today)})
    items, pronoun = (
        ("1 open item", "it") if count == 1 else (f"{count} open items", "them")
    )
    return f"Radar: {items}. Run /at:radar to see {pronoun}."
