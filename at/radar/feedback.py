import vault

STATUS_FOR_KIND = {
    "pursue": "pursuing",
    "park": "parked",
    "reject": "rejected",
    "exists": "rejected",
    "out_of_scope": "rejected",
}
UNTARGETED = {"direction", "weight"}
QUARTER_END = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}


def next_number(settings):
    numbers = [
        int(path.stem.removeprefix("fb-"))
        for path, _ in vault.notes(settings, "Feedback")
    ]
    return max(numbers, default=0) + 1


def opportunity_for(settings, number):
    names = vault.load_state(settings).get("last_checkin", [])
    if not names:
        raise SystemExit("There are no opportunities to answer yet. Run a check-in.")
    if number is None or not 1 <= number <= len(names):
        raise SystemExit(f"No opportunity number {number}. Choose 1 to {len(names)}.")
    return names[number - 1]


def config_path(settings):
    return settings.vault / vault.CONFIG_NOTE


def append_to_config(settings, key, entry):
    props = vault.read_note(config_path(settings))[0]
    vault.write_note(config_path(settings), {key: [*props.get(key, []), entry]})


def set_weight(settings, assignment):
    dimension, _, value = assignment.partition("=")
    weights = settings.config["weights"]
    if dimension not in weights:
        valid = ", ".join(weights)
        raise SystemExit(f"Unknown weight '{dimension}'. Choose one of: {valid}.")
    vault.write_note(
        config_path(settings), {"weights": {**weights, dimension: float(value)}}
    )


def quarter_end(today):
    return f"{today.year}-{QUARTER_END[(today.month - 1) // 3 + 1]}"


def apply_config_effect(settings, reply, today):
    kind, text = reply["kind"], reply.get("text")
    name = reply.get("name")
    if kind == "exists":
        append_to_config(settings, "existing_programs", {"name": name, "note": text})
    elif kind == "out_of_scope":
        append_to_config(settings, "out_of_scope", {"area": name, "reason": text})
    elif kind == "direction":
        until = reply.get("until") or quarter_end(today)
        entry = {"text": text, "who": reply.get("who", "me"), "until": until}
        append_to_config(settings, "priorities", entry)


def write_feedback(settings, reply, name_and_date):
    name, today = name_and_date
    path = settings.folder / "Feedback" / f"fb-{next_number(settings):04d}.md"
    vault.write_note(
        path,
        {
            "type": "feedback",
            "kind": reply["kind"],
            "target": vault.link(name) if name else None,
            "text": reply.get("text"),
            "until": reply.get("until"),
            "who": reply.get("who", "me"),
            "date": str(today),
        },
    )
    return path


def answer(settings, reply, today):
    kind = reply["kind"]
    if kind == "weight":
        set_weight(settings, reply.get("weight") or "")
        return write_feedback(settings, reply, (None, today))
    name = None if kind in UNTARGETED else opportunity_for(settings, reply["number"])
    apply_config_effect(settings, {**reply, "name": name}, today)
    if kind in STATUS_FOR_KIND:
        path = settings.folder / "Opportunities" / f"{name}.md"
        vault.write_note(path, {"status": STATUS_FOR_KIND[kind]})
    return write_feedback(settings, reply, (name, today))
