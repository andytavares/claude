DEFAULTS = {
    "radar_folder": "Radar",
    "capture": {"sessions": True, "prompt_text": "first-line", "skip_paths": []},
    "sources": {"status_pages": True, "session_friction": True, "linear": False},
    "status_pages": [{"name": "GitHub", "url": "https://www.githubstatus.com"}],
    "friction_patterns": [
        {"tool": "GitHub", "pattern": r"gh: HTTP 5\d\d|github\.com\S{0,80} 50[234]\b"},
    ],
    "windows": {"attention_days": 30, "signal_days": 90},
    "opportunities": {
        "min_weeks": 6,
        "min_teams": 2,
        "min_ladder_criteria": 2,
        "scan_max_candidates": 5,
    },
    "weights": {"impact": 0.3, "reach": 0.2, "direction": 0.2, "promo_fit": 0.3},
    "check_in": {
        "max_opportunities": 5,
        "max_blind_spots": 3,
        "nudge_at_session_start": "daily",
    },
    "priorities": [],
    "out_of_scope": [],
    "existing_programs": [],
}

CONFIG_BODY = """# Radar settings

The properties above are the radar's settings. Edit them here; the next run uses them.

- **radar_folder**: where the radar keeps its notes in this vault.
- **capture**: whether Claude sessions are recorded, how much of each prompt is kept
  (`none`, `first-line` or `full`), and repo paths never recorded.
- **sources**: which signals to pull: vendor status pages, friction in your own
  sessions (errors matching `friction_patterns`), and Linear when a session has it.
- **status_pages**: Atlassian Statuspage sites for tools developers depend on.
  Each pull keeps the incidents, so trends can run longer than the page's own history.
- **friction_patterns**: regular expressions that count as friction with a tool
  when they appear in a Claude session.
- **windows**: how many days of sessions count as attention, and of signals as evidence.
- **opportunities**: what a project must clear to be shown: at least `min_weeks` of
  work, at least `min_teams` teams affected, at least `min_ladder_criteria` criteria
  from `Context/Ladder.md`; and how many candidates a scan researches.
- **weights**: how much each rubric dimension counts. They add up to 1.
- **check_in**: how many opportunities and blind spots a check-in shows, and whether
  the first session of the day gets a one-line reminder (`off`, `daily` or `every`).
- **priorities**: what leadership or you mean to focus on, each with an `until` date.
- **out_of_scope**: areas never to recommend; the reason and who owns them.
- **existing_programs**: work that already exists; only improvements to it are raised.
"""

LADDER = """# Next-level criteria

Replace this with your own ladder's criteria for the level you're going for. Until
you do, every promotion-fit score is provisional. Set `provisional: false` when it's yours.

These defaults come from published principal-engineer expectations:

- Sets the technical direction for their part of the organization.
- Plans with at least a six-month view.
- Makes proposals across several teams and aligns them.
- Has measurable impact on the work of many teams, not just their own.
- Owns loosely defined, critical problems with multi-year impact.

Sources:
- https://handbook.gitlab.com/job-families/engineering/development/management/principal-engineer/
- Dropbox principal engineer postings, e.g.
  https://jobs.accel.com/companies/dropbox/jobs/72227863-principal-software-engineer-corporate-ai
"""

PRIORITIES = """# Priorities

What leadership, your manager or you want focused on. One line each, with who said it
and until when, e.g. "Cut CI cost this half (manager, until 2026-12-31)". The scan reads
this when it scores visibility and promotion fit.
"""

BOARD = """filters:
  and:
    - file.inFolder("{folder}/Opportunities")
properties:
  file.name:
    displayName: Opportunity
views:
  - type: table
    name: Opportunities
    order:
      - file.name
      - status
      - score
      - confidence
      - weeks_estimate
      - last_scored
"""
