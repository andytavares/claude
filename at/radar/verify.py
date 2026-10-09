import re

import vault

NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?%?")
LINK = re.compile(r"\[\[([^\]|#]+)[^\]]*\]\]")
DATE_OR_WEEK = re.compile(r"\d{4}-(?:\d{2}-\d{2}|W\d{2})")
DURATION = re.compile(
    r"\d[\d,]*(?:\.\d+)?[ -]?(?:days?|weeks?|months?|quarters?|years?|hours?|minutes?)\b",
    re.IGNORECASE,
)
PERIOD = re.compile(r"\b(?:Q[1-4]|H[12])\b")
YEAR = re.compile(r"(?<![\d.,])(?:19[9]\d|20\d\d)(?![\d,]|\.\d)")
LIST_MARKER = re.compile(r"^\s*\d+[.)]\s")
LABEL = re.compile(r"\b(?:milestone|phase|step|option|stage)\s+\d+", re.IGNORECASE)


def digits(number):
    return number.replace(",", "").replace("%", "")


def numbers_in(text):
    return {digits(match) for match in NUMBER.findall(text)}


def without(text, patterns):
    for pattern in patterns:
        text = pattern.sub(" ", text)
    return text


def claimed_numbers(line):
    prose = without(line, [LIST_MARKER, LABEL, LINK, DATE_OR_WEEK, DURATION, PERIOD, YEAR])
    return list(dict.fromkeys(NUMBER.findall(prose)))


def evidence_numbers(settings, name):
    matches = sorted(settings.folder.rglob(f"{name}.md"))
    if not matches:
        return set()
    text = without(matches[0].read_text(), [DATE_OR_WEEK])
    return numbers_in(text)


def verify(settings, path):
    text = path.read_text()
    body = vault.read_note(path)[1]
    offset = len(text.splitlines()) - len(body.splitlines())
    failures = []
    for number_of_line, line in enumerate(body.splitlines(), start=offset + 1):
        failures += line_failures(settings, number_of_line, line)
    return failures


def line_failures(settings, number_of_line, line):
    names = LINK.findall(line)
    supported = set()
    for name in names:
        supported |= evidence_numbers(settings, name.strip())
    reason = "is not in a linked note" if names else "has no linked note on its line"
    return [
        f"line {number_of_line}: {digits(number)} {reason}"
        for number in claimed_numbers(line)
        if digits(number) not in supported
    ]
