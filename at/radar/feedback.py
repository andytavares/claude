import vault


def next_number(settings):
    numbers = [
        int(path.stem.removeprefix("fb-"))
        for path, _ in vault.notes(settings, "Feedback")
    ]
    return max(numbers, default=0) + 1


def blind_spot_for(settings, number):
    names = vault.load_state(settings).get("last_checkin", [])
    if not names:
        raise SystemExit(
            "There are no blind spots to answer yet. Run a check-in first."
        )
    if not 1 <= number <= len(names):
        raise SystemExit(f"No blind spot number {number}. Choose 1 to {len(names)}.")
    return names[number - 1]


def answer(settings, reply, today):
    response, note = reply["response"], reply.get("note")
    name = blind_spot_for(settings, reply["number"])
    spot_path = settings.folder / "Blind spots" / f"{name}.md"
    count = vault.read_note(spot_path)[0].get("evidence_count", 0)
    path = settings.folder / "Feedback" / f"fb-{next_number(settings):04d}.md"
    vault.write_note(
        path,
        {
            "type": "feedback",
            "responds_to": vault.link(name),
            "response": response,
            "evidence_count_at": count,
            "date": str(today),
            "note": note,
        },
    )
    vault.write_note(spot_path, {"status": response})
    return path
