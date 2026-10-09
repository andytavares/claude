import re
from collections import Counter
from datetime import date, datetime, timedelta

import vault

RECENT_WEEKS = 4


def to_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def iso_week(day):
    year, week, _ = day.isocalendar()
    return f"{year}-W{week:02d}"


def link_target(text):
    match = re.match(r"\[\[([^\]|#]+)", str(text or ""))
    return match.group(1).strip() if match else None


def week_labels(start, today):
    labels = []
    for offset in range((today - start).days + 1):
        label = iso_week(start + timedelta(days=offset))
        if label not in labels:
            labels.append(label)
    return labels


def mean(values):
    return sum(values) / len(values) if values else 0


def slope_of(counts):
    recent = counts[-RECENT_WEEKS:]
    before = counts[-2 * RECENT_WEEKS : -RECENT_WEEKS]
    return round(mean(recent) - mean(before), 2)


def signals_by_note(settings, window_start):
    grouped = {}
    for _, props in vault.notes(settings, "Signals"):
        if props.get("type") != "signal" or to_date(props["observed"]) < window_start:
            continue
        targets = [*(props.get("about") or []), props.get("theme")]
        for name in {link_target(target) for target in targets} - {None}:
            grouped.setdefault(name, []).append(props)
    return grouped


def note_kinds(settings):
    kinds = {}
    for path, props in vault.notes(settings, "Entities"):
        kinds[path.stem] = props.get("kind", "area")
    for path, _ in vault.notes(settings, "Themes"):
        kinds[path.stem] = "theme"
    return kinds


def session_repos(settings):
    repos = {}
    for path, props in vault.notes(settings, "Sessions"):
        repos[path.stem] = link_target(props.get("repo")) or props.get("repo")
    return repos


def breadth_of(signals, repos):
    components = {c for s in signals for c in s.get("components") or []}
    sessions = {link_target(s.get("session")) for s in signals if s.get("session")}
    return len(components) + len({repos[s] for s in sessions if s in repos})


def recent_sessions(settings, today):
    cutoff = today - timedelta(days=settings.config["windows"]["attention_days"])
    found = []
    for path, props in vault.notes(settings, "Sessions"):
        if props.get("radar_only") or date.fromisoformat(path.stem[:10]) < cutoff:
            continue
        found.append((link_target(props.get("repo")), vault.read_note(path)[1]))
    return found


def count_sessions(row, sessions):
    name = row["name"]
    short = name.split(" - ", 1)[-1]
    if row["kind"] == "repo":
        return sum(1 for repo, _ in sessions if repo in (name, short))
    return sum(1 for _, body in sessions if short.lower() in body.lower())


def trend_row(note, signals, context):
    start, today = context["start"], context["today"]
    weekly = dict.fromkeys(week_labels(start, today), 0)
    weekly.update(Counter(iso_week(to_date(s["observed"])) for s in signals))
    observed = sorted(to_date(s["observed"]) for s in signals)
    return {
        **note,
        "signal_total": len(signals),
        "signals_open": sum(1 for s in signals if s.get("status") == "open"),
        "slope": slope_of(list(weekly.values())),
        "breadth": breadth_of(signals, context["repos"]),
        "weekly": weekly,
        "by_impact": dict(Counter(s["impact"] for s in signals if s.get("impact"))),
        "first_signal": observed[0].isoformat(),
        "last_signal": observed[-1].isoformat(),
    }


def note_path(settings, name, kind):
    folder = "Themes" if kind == "theme" else "Entities"
    return settings.folder / folder / f"{name}.md"


def trends(settings, today):
    start = today - timedelta(days=settings.config["windows"]["signal_days"])
    context = {"start": start, "today": today, "repos": session_repos(settings)}
    kinds = note_kinds(settings)
    sessions = recent_sessions(settings, today)
    rows = []
    for name, signals in signals_by_note(settings, start).items():
        if name not in kinds:
            continue
        row = trend_row({"name": name, "kind": kinds[name]}, signals, context)
        row["sessions"] = count_sessions(row, sessions)
        stored = {**row, "trend_updated": today.isoformat()}
        vault.write_note(note_path(settings, name, kinds[name]), stored)
        rows.append(row)
    return sorted(rows, key=lambda row: -row["signal_total"])
