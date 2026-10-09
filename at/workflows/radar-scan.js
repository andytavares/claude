export const meta = {
  name: 'radar-scan',
  description: 'Find multi-month, org-wide developer-experience projects in the radar vault, research and score them against your ladder, and write Opportunity notes',
  whenToUse: 'Monthly, or after adding a batch of radar notes',
  phases: [
    { title: 'Cluster', detail: 'themes and trends become project hypotheses; scope gate' },
    { title: 'Research', detail: 'options, prior art, owners and size for each candidate' },
    { title: 'Score', detail: 'rubric against Ladder.md, written as an Opportunity note' },
    { title: 'Critic', detail: 'every number traced, the case against argued' },
  ],
}

const SETUP = `The radar's vault path is in ~/.claude/at-radar.json ("vault"). Inside it: "Radar Config.md" (settings: opportunities, weights, out_of_scope, existing_programs, priorities), and under its radar_folder (default "Radar"): Signals/, Entities/, Themes/, Sessions/, Opportunities/, Feedback/, Context/Ladder.md, Context/Priorities.md. The \`radar\` command is on PATH: \`radar trends\` prints per-theme evidence as JSON and writes the numbers onto Entity and Theme notes; \`radar verify <note path>\` fails on any number not found in a note linked on the same line.

What counts as an opportunity: a project a staff engineer would lead toward a principal promotion. It runs at least opportunities.min_weeks weeks, affects at least opportunities.min_teams teams, makes developers' lives measurably better across the org, and demonstrates at least opportunities.min_ladder_criteria criteria from Context/Ladder.md. Example: "GitHub incidents are rising week over week; evaluate alternatives (self-hosting, GitLab, a mirror with CI fallback), prove one with a small POC". Never a single PR, a to-do, or anything finishable in under two weeks.`

const CANDIDATES = {
  type: 'object',
  required: ['candidates', 'held_back'],
  properties: {
    candidates: {
      type: 'array',
      items: {
        type: 'object',
        required: ['name', 'hypothesis', 'evidence_notes', 'why_now'],
        properties: {
          name: { type: 'string', description: 'Short project name, usable as a file name' },
          hypothesis: { type: 'string', description: 'If we <do X>, <these teams> get <measurable Z>' },
          evidence_notes: { type: 'array', items: { type: 'string' }, description: 'Note names (no brackets) of the Theme, Entity and Signal notes behind it' },
          why_now: { type: 'string' },
        },
      },
    },
    held_back: {
      type: 'array',
      items: { type: 'object', required: ['name', 'rule'], properties: { name: { type: 'string' }, rule: { type: 'string' } } },
    },
  },
}

const VERDICT = {
  type: 'object',
  required: ['verdict', 'issues'],
  properties: {
    verdict: { type: 'string', enum: ['keep', 'rework', 'drop'] },
    issues: { type: 'array', items: { type: 'string' } },
  },
}

phase('Cluster')
const clustered = await agent(`${SETUP}

Run \`radar trends\`. Read the settings note, Context/Ladder.md, Context/Priorities.md, the Feedback notes (corrections and directions especially), and the existing Opportunities notes.

Group the evidence into themes that point at the same underlying problem, and turn each into a project hypothesis. Prefer rising trends, broad breadth, high severity, and themes that match a stated priority. Merge with an existing Opportunity of the same problem rather than duplicating it (reuse its name).

Scope gate: drop anything matching out_of_scope or existing_programs, or that a Feedback note rejected, and list it under held_back with the rule that stopped it.

Return at most opportunities.scan_max_candidates candidates, strongest first. Return none rather than padding the list with task-sized items.`, { schema: CANDIDATES, effort: 'high' })

const candidates = clustered ? clustered.candidates : []
if (clustered) clustered.held_back.forEach(h => log(`Held back: ${h.name} (${h.rule})`))
log(`${candidates.length} candidates to research`)

const research = (candidate, issues) => agent(`${SETUP}

Research this candidate project:
Name: ${candidate.name}
Hypothesis: ${candidate.hypothesis}
Evidence notes: ${candidate.evidence_notes.join(', ')}
${issues ? `A critic rejected the previous draft for: ${issues.join('; ')}. Address these.` : ''}

Read the evidence notes. Then establish, citing a URL or note for each fact:
1. Options for solving it (e.g. alternative vendors, self-hosting, architecture changes), each with cost, migration effort, risk and lock-in. Check current vendor docs and pricing pages; never rely on memory for a product's existence or features.
2. Prior art: how other engineering orgs handled the same problem.
3. Who may already own it: search the vault's Signals and notes; say what you couldn't check.
4. Size: a realistic estimate in weeks, and which teams it touches.
5. The smallest POC that would prove the leading option viable, with a pass condition.
Return your findings as markdown with a Sources list.`, { label: `research ${candidate.name}`, phase: 'Research', effort: 'high' })

const scoreAndWrite = (candidate, findings) => agent(`${SETUP}

Score this candidate and write its Opportunity note.
Name: ${candidate.name}
Hypothesis: ${candidate.hypothesis}
Why now: ${candidate.why_now}
Evidence notes: ${candidate.evidence_notes.join(', ')}
Research:
${findings}

Score each rubric dimension 1-5 with the evidence for the score: impact (measured change in engineer-hours, incidents or dollars across the org), reach (teams affected and needing alignment), direction (a loosely defined problem where the lead sets an architecture others adopt), promo_fit (the Ladder.md criteria it demonstrates, favouring those Priorities.md or Feedback say the packet is weakest on). score = sum of weights × scores from the settings note; confidence = share of the four scores backed by a measured trend rather than a note or opinion. If any gate fails (fewer than min_weeks, fewer than min_teams, fewer than min_ladder_criteria criteria, or an existing owner), do not write a note; return "gate failed: <which>".

Otherwise write <vault>/<radar_folder>/Opportunities/${candidate.name}.md. If it exists, keep its body sections the user edited and set previous_score to its old score. Properties: type: opportunity, status: candidate (keep the existing status if the note exists), score, confidence, previous_score, weeks_estimate, teams (list of [[Team - name]] links), ladder_criteria (list), evidence (list of [[note]] links), first_seen (keep existing), last_scored (today), provisional (true if Context/Ladder.md has provisional: true). Body sections: Hypothesis; Why now; Evidence (one line per claim, each with the [[note]] it comes from on the same line, using only numbers that appear in that note); Rubric (table: dimension, score, evidence); Ladder criteria (each with how the project demonstrates it); Options; POC; Size and teams; Sources.

Run \`radar verify\` on the note and fix every failure. Return the note path, or the gate failure.`, { label: `score ${candidate.name}`, phase: 'Score', effort: 'high' })

const critique = (candidate, written) => agent(`${SETUP}

You are the critic for "${candidate.name}". The scorer reported: ${written}
Read the Opportunity note and every note it links. Run \`radar verify\` on it.
Try to refute it: is it really multi-month and multi-team, or a task dressed up? Does every number trace to its linked note? Are the scores inflated? Does someone already own this? Is the ladder mapping real or decorative? Is a cheaper fix hiding in plain sight?
verdict: keep if it holds; rework if fixable with more research (list the issues); drop if it is not a promotion-worthy project at all. Default to rework when unsure.`, { label: `critic ${candidate.name}`, phase: 'Critic', schema: VERDICT, effort: 'high' })

const markDropped = (candidate, issues) => agent(`${SETUP}

Set status: rejected on the Opportunity note "${candidate.name}" if it exists, and add a final body line "Critic: ${issues.join('; ').replace(/"/g, "'")}". Change nothing else.`, { label: `drop ${candidate.name}`, phase: 'Critic', effort: 'low' })

const evaluate = async (candidate) => {
  let issues = null
  for (let round = 0; round < 2; round++) {
    const findings = await research(candidate, issues)
    const written = await scoreAndWrite(candidate, findings)
    if (!written || written.startsWith('gate failed')) return { name: candidate.name, result: written || 'no result' }
    const verdict = await critique(candidate, written)
    if (!verdict || verdict.verdict === 'keep') return { name: candidate.name, result: written }
    if (verdict.verdict === 'drop') {
      await markDropped(candidate, verdict.issues)
      return { name: candidate.name, result: `dropped: ${verdict.issues.join('; ')}` }
    }
    issues = verdict.issues
  }
  await markDropped(candidate, issues)
  return { name: candidate.name, result: `dropped after two reworks: ${issues.join('; ')}` }
}

const results = await pipeline(candidates, evaluate)
return {
  held_back: clustered ? clustered.held_back : [],
  results: results.filter(Boolean),
}
