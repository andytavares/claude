---
name: radar
description: Find and pitch multi-month, org-wide projects that make developers' lives better and demonstrate staff-to-principal criteria. Weekly check-in, pitches with POC and milestones, notes from any source, and answers that steer the ranking. Data lives in the Obsidian vault named at install.
argument-hint: "[pitch <opportunity> | note <text> [--source <name>] | answer <n> <kind> [--text …] | nothing for the check-in]"
disable-model-invocation: true
model: opus
effort: high
---
Radar: $ARGUMENTS

The `radar` command is on your PATH while this plugin is on. If it reports that the radar is not installed, say so, give `./install.sh --radar --vault <folder>`, and stop. The vault path is in `~/.claude/at-radar.json`; its notes live under the `radar_folder` set in the vault's `Radar Config.md`.

The radar exists to find projects a staff engineer would lead toward a principal promotion: months of work, several teams, a measurable change in developers' lives, and criteria from `Context/Ladder.md` demonstrated. Never present a single PR, a to-do, or anything finishable in under two weeks as an opportunity.

## No argument: the weekly check-in

If `sources.linear` is true in the settings note and the Linear tools are available, first add each Linear project or issue that shows a recurring or growing problem across teams as a note: `radar note "<title>: <url>" --source linear --about "Team - <team>"`.

Run `radar checkin`. It records new sessions, pulls the sources, recomputes trends, writes this week's note under `Briefs/`, and prints JSON. Show the user, in this order:

1. What changed because of their feedback.
2. Opportunities, numbered as in the JSON: name, score and confidence, status, weeks, the ladder criteria, "(provisional)" when it is, and the score change.
3. Rising trends and blind spots, one line each.
4. What was held back, and any source that failed.

When there are no opportunities, say so and suggest `/at:radar-scan` (it runs in the background and costs real tokens; the user decides). End with one line on how to act: `/at:radar pitch <name>` or `/at:radar answer 1 pursue`.

## `pitch <opportunity>`

Read `Opportunities/<opportunity>.md`, every note it links, `Context/Ladder.md` and `Context/Priorities.md`. Check anything external the pitch relies on (vendors, products, pricing, prior art) against current sources, citing a URL for each; if a product named in the note can't be confirmed, say so instead of describing it.

Write `Pitches/<opportunity>.md` with properties `type: pitch`, `opportunity: [[<opportunity>]]`, `date`, and these sections:

- **Problem and trend**: what developers lose today, with the numbers, each line linking the note it comes from.
- **Why now**.
- **Options**: a table comparing each option on cost, migration effort, risk and lock-in.
- **POC**: the smallest build that proves the leading option, its pass condition, and how long it takes.
- **Milestones**: by quarter, each with an exit test.
- **Risks**: each with a mitigation and how you'd know it's working.
- **Stakeholders**: affected teams, likely sponsor, partner teams needed.
- **Ladder mapping**: each criterion and how this project demonstrates it.
- **First two weeks**: what to do before asking anyone for time.
- **Sources**.

Run `radar verify` on the pitch and fix every failure before finishing. Set the opportunity's `status: pitched`. Reply with the pitch's path and one line on its strongest and weakest point. Suggest `/at:poc` with the POC section as the next step.

## `note <text>`

Run `radar entities` for names already in the vault. Pick the one to three things the text is about, reusing an existing name when one fits, else a new one: `Tool - <name>`, `Team - <name>`, `Area - <name>`, `Repo - <name>`, `Person - <name>` or `Project - <name>`. Add a theme only when the text clearly belongs to one already listed.

When the text came from another tool or the user names one (Buildkite, incident.io, a work Linear issue, Slack, an alert), pass it as `--source <name>`.

Run `radar note "<text>" --about "<name>" [--about "<name>"] [--theme "<name>"] [--source <name>]` with the user's words unchanged. Reply with the note's path and its links in one line.

## `answer <n> <kind> …`

Kinds: `pursue`, `park`, `reject`, `correction`, `exists`, `out_of_scope`, `direction` (with `--until`), `weight` (with `--weight dimension=value`). Pass `--text` for the reason and `--who manager` when someone else said it. Run `radar answer <n> <kind> [--text "<why>"] [--until <date>] [--who <who>] [--weight <dimension=value>]` and reply with the feedback note's path.
