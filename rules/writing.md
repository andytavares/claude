# Writing

These rules apply to all text you write: chat replies, PR descriptions, tickets, commit messages, code comments, review comments, docs, and briefs or prompts for other agents. Follow them unless the user asks for a different style or format. The reader acts on what you write, so text that can mean two things causes wrong work.

## Every word earns its place
- Write the minimum text that makes the point. If you can remove a word and the meaning stays, remove it.
- No preamble, no flattery, no hype ("this changes everything", "powerful", "seamless"), no closing offers.
- State facts. Give the source of each fact: a `path:line`, a command and its output, or a link.
- One meaning only. If a sentence can be read two ways, rewrite it.

## Simplified Technical English
Follow ASD-STE100. Apply these rules to every sentence:
- One topic per sentence. Procedural sentences: at most 20 words. Descriptive sentences: at most 25 words.
- Active voice. Imperative for instructions ("Run `install.sh`", not "`install.sh` should be run").
- One word, one meaning. Use the same term for the same thing in all the text. Do not use synonyms for variety.
- Use the simple, common verb: "use", not "leverage"; "start", not "initialize"; "show", not "surface".
- Do not use phrasal verbs when one verb has the same meaning: "find", not "figure out".
- Keep articles ("the", "a"). No noun clusters of more than three words.
- Say what is true, not what is possibly true. Use "can" or "must", not "might", "should" or "may", unless the uncertainty is the fact.

Only these two STE rules are relaxed:
- Technical names (functions, files, tools, error text) are always allowed. Write them exactly as they are.
- You do not have to use only the STE dictionary. Use the everyday technical word the reader knows.

## PR descriptions
Describe the PR in this format, you do not need section headings writing this as parahgaphs is fine as long as it follows the rules:

```markdown
## Current state
1–3 short sentences: what the code does now, or what is wrong.

## This PR
Fixes: or Part Of: link to the one ticket this PR closes.
1–3 short sentences: what changes.

## Reviewer notes [OPTIONAL]
- Short bullets: risks, decisions, what was not done, what to check by hand.
- Do not include this section unless it adds value to a human reviewer.
```

- Omit "Reviewer notes" when there is nothing to say.
- For a complex change, or a flow that is hard to follow in text, you may add a mermaid diagram if it helps with understanding.

## Tickets
Use these sections, in this order:

```markdown
# Summary
What the work is and why, for a reader with no technical knowledge. Fewer than 150 words.

# Context
Optional. For complex work: the problem, the solution, what is asked and why. Short bullets. Technical detail is allowed here.

# Acceptance Criteria
- [ ] Each item is one result a reviewer can check as true or false.
- [ ] All items together are the definition of done.

# Dev Hints
Optional. Links, file paths, approaches and traps that help the implementer. Short bullets.
```

- Omit an optional section when it has no content. Do not write "N/A".
- An acceptance criterion states a result ("`/at:brief LIN-123` writes `briefs/LIN-123.md`"), not a task ("Update the brief skill").
