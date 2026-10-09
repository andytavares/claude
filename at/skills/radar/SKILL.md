---
name: radar
description: Check in on blind spots (strong signal, little of your attention), add something you noticed from any source, or answer a blind spot. Data lives in the Obsidian vault named at install.
argument-hint: "[note <text> [--source <name>] | answer <n> act|watch|known|out_of_scope [why] | nothing for the check-in]"
disable-model-invocation: true
model: opus
effort: medium
---
Radar: $ARGUMENTS

The `radar` command is on your PATH while this plugin is on. If it reports that the radar is not installed, say so, give `./install.sh --radar --vault <folder>`, and stop.

## No argument: the check-in

If `sources.linear` is true in the vault's `Radar Config.md` and the Linear tools are available, first add each of the user's open Linear issues that is overdue or untouched for 14 days: `radar note "<title>: <url>" --source linear --about "Project - <project>"`.

Run `radar checkin`. It digests new sessions, pulls the sources turned on in the settings note, finds blind spots, writes the week's note under `Briefs/`, and prints JSON. Show the user, in this order:

1. What changed because of their feedback, by feedback note.
2. Commitments.
3. Blind spots, numbered as in the JSON: title, why it was likely missed, and the evidence as note names.
4. What was held back by `out_of_scope`, one line each.
5. Any source that failed, with its error.

The list comes from the command. Don't add blind spots of your own or rank them differently. End with one line on how to answer: `/at:radar answer 2 watch`.

## `note <text>`

Run `radar entities` for the names already in the vault. Pick the one to three things the text is about, reusing an existing name when one fits, else a new one in the form `Repo - <name>`, `Area - <name>`, `Person - <name>` or `Project - <name>`. Add a theme only when the text clearly belongs to one already listed.

When the text came from another tool or the user names one (Buildkite, incident.io, a work Linear issue, Slack, an alert), pass it as `--source <name>`.

Run `radar note "<text>" --about "<name>" [--about "<name>"] [--theme "<name>"] [--source <name>]` with the user's words unchanged. Reply with the note's path and its links in one line.

## `answer <n> <response> [why]`

Run `radar answer <n> <response> --note "<why>"` (omit `--note` when no reason was given) and reply with the feedback note's path.
