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

Only these STE rules are relaxed:
- Technical names (functions, files, tools, error text) are always allowed. Write them exactly as they are.
- A step a person runs names a command they can type or a URL they can open. Your own tool calls, such as an MCP tool, are not commands. Write the CLI command or URL that gets the same output, and run it once first.
- You do not have to use only the STE dictionary. Use the everyday technical word the reader knows.

## UI and UX changes
Every artifact or spec that changes something the user sees shows a before and an after rendering of each changed screen or state. This includes a web or app UI, a TUI, and CLI output.
- Put the two renderings side by side, or one directly after the other, at the same size.
- Before: a screenshot of the current UI, or the captured output of the current TUI or CLI. If there is no current UI, write "New screen" and show only the after.
- After: a mockup or screenshot of the changed UI, or the expected TUI or CLI output.
- Under each pair, list each change, why it is made, and what the user now sees or does differently.

## PR descriptions
Write the PR description as two short paragraphs with no headings for them, then a "Reviewer notes" section.

```markdown
Paragraph one: what the code does now, or what is wrong. 1–3 short sentences.

Paragraph two: what this PR changes, starting with the ticket link as "Fixes: <link>" or "Part Of: <link>" on its own line when the work has a ticket. 1–3 short sentences.

## Reviewer notes
- Merge danger: one-way door or two-way door, and what breaks if this is wrong.
- Short bullets for risks, decisions, what was not done, what to check by hand.
```

- Example. "Today PR descriptions have a heading for the current state and another for the proposed change." Then, as the second paragraph: "This PR writes both as two plain paragraphs, so the description reads naturally and still says what was and what is."
- The link is never an incident or paging link, and never a placeholder like "No ticket yet". With no ticket, and when the user said none is needed, leave the line out.
- "Reviewer notes" is always present. Its first bullet is "Merge danger". A one-way door is a change that cannot be undone by reverting the PR (a migration, a deleted resource, a published artifact). Add the other bullets only when they help a human reviewer.
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
- An acceptance criterion states a result ("`/at:research --prd` prints the artifact URL"), not a task ("Update the research skill").
