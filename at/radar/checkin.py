from datetime import timedelta

import vault

SECTIONS = [
    "What changed because of your feedback",
    "Opportunities",
    "Rising",
    "Blind spots",
    "Held back",
    "Sources",
]
NO_OPPORTUNITIES = "None yet. Run /at:radar-scan to find some from the evidence below."
SHOWN_OPPORTUNITIES = {"candidate", "pitched", "pursuing"}
HELD_STATUSES = {"parked", "rejected"}
RISING_SHOWN = 3
WEEKS_SHOWN = 4
BLIND_MIN_OPEN = 3
BLIND_MAX_SESSIONS = 1


def run_digest(settings, home):
    import digest

    digest.digest(settings, home)


def run_pull(settings, home):
    import sources

    sources.pull(settings, home)


def run_trends(settings, today):
    import trends

    return trends.trends(settings, today)


def recent_feedback(settings, today):
    start = str(today - timedelta(days=7))
    return [
        (path.stem, props)
        for path, props in vault.notes(settings, "Feedback")
        if str(props["date"])[:10] >= start
    ]


def open_opportunities(settings):
    found = [
        {"name": path.stem, **props}
        for path, props in vault.notes(settings, "Opportunities")
        if props.get("status") in SHOWN_OPPORTUNITIES
    ]
    found.sort(key=lambda found_one: found_one.get("score", 0), reverse=True)
    return found[: settings.config["check_in"]["max_opportunities"]]


def rising(trends):
    moving = [trend for trend in trends if trend["slope"] > 0]
    return sorted(moving, key=lambda trend: -trend["slope"])[:RISING_SHOWN]


def blind_spots(settings, trends):
    quiet = [
        trend
        for trend in trends
        if trend["signals_open"] >= BLIND_MIN_OPEN
        and trend["sessions"] <= BLIND_MAX_SESSIONS
    ]
    quiet.sort(key=lambda trend: -trend["signals_open"])
    return quiet[: settings.config["check_in"]["max_blind_spots"]]


def latest_feedback_text(settings):
    texts = {}
    for _, props in vault.notes(settings, "Feedback"):
        if props.get("target"):
            texts[props["target"]] = props.get("text")
    return texts


def held_back(settings):
    texts = latest_feedback_text(settings)
    held = [
        {"name": path.stem, "status": props["status"], "text": texts[link]}
        for path, props in vault.notes(settings, "Opportunities")
        if props.get("status") in HELD_STATUSES
        and texts.get(link := vault.link(path.stem))
    ]
    return held + list(settings.config["out_of_scope"])


def opportunity_lines(opportunities):
    lines = []
    for number, found in enumerate(opportunities, 1):
        score = f"score {found.get('score')}, confidence {found.get('confidence')}"
        previous = found.get("previous_score")
        if previous is not None and previous != found.get("score"):
            score += f" (was {previous})"
        tail = " (provisional)" if found.get("provisional") else ""
        weeks = f"{found.get('weeks_estimate')} weeks"
        lines.append(
            f"{number}. {found['name']}: {score}, {found['status']}, {weeks}{tail}"
        )
        lines += [f"   - {criterion}" for criterion in found.get("ladder_criteria", [])]
    return lines or [NO_OPPORTUNITIES]


def rising_lines(entries):
    lines = []
    for trend in entries:
        recent = [trend["weekly"][week] for week in sorted(trend["weekly"])]
        counts = ", ".join(str(count) for count in recent[-WEEKS_SHOWN:])
        lines.append(
            f"- {trend['name']}: {counts} per week, {trend['signals_open']} open"
        )
    return lines


def blind_spot_lines(settings, entries):
    days = settings.config["windows"]["attention_days"]
    return [
        f"- {trend['name']}: {trend['signals_open']} open signals, "
        f"{trend['sessions']} sessions in {days} days"
        for trend in entries
    ]


def held_line(item):
    if "area" in item:
        return f"- {item['area']} (out of scope): {item['reason']}"
    return f"- {item['name']} ({item['status']}): {item['text']}"


def source_line(name, status):
    if status["ok"]:
        return f"- {name}: ok, {status['count']} items"
    return f"- {name}: failed: {status['error']}"


def feedback_line(stem, props):
    return f"- {vault.link(stem)}: {props['kind']} {props.get('target') or ''}".rstrip()


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


def section_lines(settings, found, health):
    return dict(
        zip(
            SECTIONS,
            [
                [feedback_line(*item) for item in found["feedback_applied"]],
                opportunity_lines(found["opportunities"]),
                rising_lines(found["rising"]),
                blind_spot_lines(settings, found["blind_spots"]),
                [held_line(item) for item in found["held_back"]],
                [source_line(name, status) for name, status in health.items()],
            ],
            strict=True,
        )
    )


def gather(settings, today):
    trends = run_trends(settings, today)
    return {
        "opportunities": open_opportunities(settings),
        "rising": rising(trends),
        "blind_spots": blind_spots(settings, trends),
        "held_back": held_back(settings),
        "feedback_applied": recent_feedback(settings, today),
    }


def checkin(settings, home, today):
    run_digest(settings, home)
    run_pull(settings, home)
    found = gather(settings, today)
    health = vault.load_state(settings).get("sources", {})
    path = write_brief(settings, today, section_lines(settings, found, health))
    names = [item["name"] for item in found["opportunities"]]
    vault.save_state(settings, {**vault.load_state(settings), "last_checkin": names})
    stems = [stem for stem, _ in found["feedback_applied"]]
    return {**found, "brief": str(path), "feedback_applied": stems, "sources": health}


def new_candidates(settings, nudged_on):
    return sum(
        props.get("status") == "candidate"
        and (nudged_on is None or str(props.get("first_seen")) > nudged_on)
        for _, props in vault.notes(settings, "Opportunities")
    )


def due_today(settings, today):
    mode = settings.config["check_in"]["nudge_at_session_start"]
    if mode == "every":
        return True
    return mode == "daily" and vault.load_state(settings).get("nudged_on") != str(today)


def nudge(settings, today):
    if not due_today(settings, today):
        return None
    count = new_candidates(settings, vault.load_state(settings).get("nudged_on"))
    if not count:
        return None
    vault.save_state(settings, {**vault.load_state(settings), "nudged_on": str(today)})
    noun, pronoun = ("opportunity", "it") if count == 1 else ("opportunities", "them")
    return f"Radar: {count} new {noun}. Run /at:radar to see {pronoun}."
