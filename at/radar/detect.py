import re
from datetime import date, datetime, timedelta
from typing import NamedTuple

import vault

GREW_PREFIX = "Grew since you said watch: "
MIN_SHARED_WORDS = 3
NOT_DONE_AFTER_DAYS = 2


class World(NamedTuple):
    settings: object
    today: date
    sessions: list
    signals: list
    repos: list


def as_day(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def repo_of(link_text):
    match = re.fullmatch(r"\[\[Repo - (.+)\]\]", str(link_text))
    return match.group(1) if match else None


def load_sessions(settings):
    return [
        {
            "stem": path.stem,
            "path": path,
            "repo": repo_of(props.get("repo")),
            "started": str(props["started"]),
            "day": as_day(props["started"]),
            "not_done": props.get("not_done") or [],
        }
        for path, props in vault.notes(settings, "Sessions")
        if not props.get("radar_only")
    ]


def load_signals(settings):
    signals = []
    for path, props in vault.notes(settings, "Signals"):
        if props.get("status") == "open":
            about = [repo_of(item) for item in props.get("about") or []]
            signals.append(
                {**props, "stem": path.stem, "repos": [r for r in about if r]}
            )
    return signals


def load_world(settings, today):
    repos = [
        path.stem.removeprefix("Repo - ")
        for path, props in vault.notes(settings, "Entities")
        if props.get("kind") == "repo"
    ]
    return World(
        settings, today, load_sessions(settings), load_signals(settings), repos
    )


def candidate(detector, title, **details):
    return {"title": title, "detector": detector, **details}


def since(world, days):
    return world.today - timedelta(days=days)


def repo_signals(world, repo):
    start = since(world, world.settings.config["windows"]["signal_days"])
    return [
        signal
        for signal in world.signals
        if repo in signal["repos"] and as_day(signal["observed"]) >= start
    ]


def repo_sessions(world, repo, days):
    start = since(world, days)
    return [s for s in world.sessions if s["repo"] == repo and s["day"] >= start]


def aging_commitments(world):
    limit = world.settings.config["detectors"]["aging_pr_days"]
    return [
        candidate(
            "aging_commitments",
            f"PR open {signal['age_days']} days: {', '.join(signal['repos'])}",
            evidence=[signal["stem"]],
            why_missed="Nothing has touched it since it opened",
            score=signal["age_days"] / limit,
        )
        for signal in world.signals
        if signal.get("kind") == "aging_pr" and signal["age_days"] >= limit
    ]


def silence(world):
    days = world.settings.config["detectors"]["silence_days"]
    found = []
    for repo in world.repos:
        signals = repo_signals(world, repo)
        if signals and not repo_sessions(world, repo, days):
            found.append(
                candidate(
                    "silence",
                    f"{repo}: signals but no sessions in {days} days",
                    evidence=[signal["stem"] for signal in signals],
                    why_missed=f"{len(signals)} open signals and no session since "
                    f"{since(world, days)}",
                    score=len(signals),
                )
            )
    return found


def repeated_correction(world):
    limit = world.settings.config["detectors"]["repeated_correction"]
    return [
        candidate(
            "repeated_correction",
            f"Told Claude {signal['count']} times: "
            f"{signal['stem'].removeprefix('Correction ')}",
            evidence=[signal["stem"]],
            why_missed="The same correction keeps coming back, so the underlying cause "
            "may not be fixed",
            score=signal["count"],
        )
        for signal in world.signals
        if signal.get("kind") == "correction" and signal["count"] >= limit
    ]


def words(text):
    return set(re.findall(r"[a-z]{4,}", str(text).lower()))


def addressed_later(world, session, item):
    for later in world.sessions:
        if later["repo"] != session["repo"] or later["started"] <= session["started"]:
            continue
        for line in vault.read_note(later["path"])[1].splitlines():
            if len(words(item) & words(line)) >= MIN_SHARED_WORDS:
                return True
    return False


def not_done_again(world):
    cutoff = since(world, NOT_DONE_AFTER_DAYS)
    return [
        candidate(
            "not_done_again",
            f"Left not done: {item}",
            evidence=[session["stem"]],
            why_missed="No later session in this repo mentions it",
            score=1,
        )
        for session in world.sessions
        if session["day"] < cutoff
        for item in session["not_done"]
        if not addressed_later(world, session, item)
    ]


def strong_signal_low_attention(world):
    days = world.settings.config["windows"]["attention_days"]
    found = []
    for repo in world.repos:
        signals = repo_signals(world, repo)
        sessions = repo_sessions(world, repo, days)
        if len(signals) >= 3 and len(sessions) <= 1:
            found.append(
                candidate(
                    "strong_signal_low_attention",
                    f"{repo}: {len(signals)} open signals, {len(sessions)} sessions "
                    f"in {days} days",
                    evidence=[signal["stem"] for signal in signals],
                    why_missed="Plenty of signals point here but you have barely "
                    "worked in it",
                    score=len(signals) / (1 + len(sessions)),
                )
            )
    return found


DETECTORS = [
    aging_commitments,
    silence,
    repeated_correction,
    not_done_again,
    strong_signal_low_attention,
]


def split_out_of_scope(settings, candidates):
    kept, held = [], []
    for found in candidates:
        title = found["title"].lower()
        hit = next(
            (e for e in settings.config["out_of_scope"] if e.lower() in title), None
        )
        if hit:
            held.append({**found, "matched": hit})
        else:
            kept.append(found)
    return kept, held


def answered_counts(settings):
    counts = {}
    for _, props in vault.notes(settings, "Feedback"):
        counts[str(props["responds_to"]).strip("[]")] = props["evidence_count_at"]
    return counts


def blind_spot_path(settings, name):
    return settings.folder / "Blind spots" / f"{name}.md"


def drop_answered(settings, candidates):
    answered = answered_counts(settings)
    kept = []
    for found in candidates:
        props = vault.read_note(blind_spot_path(settings, found["note"]))[0]
        status = props.get("status")
        if status not in ("known", "out_of_scope", "watch"):
            kept.append(found)
            continue
        seen = answered.get(found["note"], props.get("evidence_count", 0))
        if len(found["evidence"]) <= seen:
            continue
        if status == "watch":
            found = {**found, "why_missed": GREW_PREFIX + found["why_missed"]}
        kept.append(found)
    return kept


def record(settings, found, today):
    path = blind_spot_path(settings, found["note"])
    props = {
        "type": "blind_spot",
        "title": found["title"],
        "detector": found["detector"],
        "evidence": [vault.link(name) for name in found["evidence"]],
        "evidence_count": len(found["evidence"]),
        "why_missed": found["why_missed"],
        "last_seen": str(today),
        "score": round(found["score"], 2),
    }
    if not path.exists():
        props.update(status="open", first_seen=str(today))
    vault.write_note(path, props)


def detect(settings, today):
    world = load_world(settings, today)
    found = [item for detector in DETECTORS for item in detector(world)]
    found = [{**item, "note": vault.note_name(item["title"])} for item in found]
    kept, held = split_out_of_scope(settings, found)
    kept = sorted(drop_answered(settings, kept), key=lambda item: -item["score"])
    kept = kept[: settings.config["check_in"]["max_blind_spots"]]
    for item in kept:
        record(settings, item, today)
    return {"blind_spots": kept, "suppressed": held}
