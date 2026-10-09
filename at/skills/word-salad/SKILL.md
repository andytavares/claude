---
name: word-salad
description: Rewrite a wall of text so a person can read it in one pass. Plain words, short sentences, one line of thought, simple examples. Takes text or a file path; with no argument, rewrites your previous response.
argument-hint: "[text | file path]  (default: your previous response)"
disable-model-invocation: true
model: opus
effort: medium
---
Input: $ARGUMENTS

If the input is a file path, rewrite that file's text. If it is text, rewrite it. If it is empty, rewrite your previous response in this conversation.

Write for a reader who is smart, busy and new to the topic. Keep every fact, decision, number, path, command and link that matters. Drop everything else.

## Lead with the point
Decide in one sentence what the reader needs to know or do. Open with that. Everything after it supports it, in the order the reader needs it.

## One line of thought
- Go from what it is, to why it matters, to what to do. Keep related things together and never double back.
- One idea per paragraph, one point per sentence.
- Cut anything that repeats: recaps, "in short", a summary of the summary.
- Use a short list for parallel items and sentences for reasoning.

## Plain words
- Use the everyday word: "use" not "leverage", "start" not "initialize", "about" not "approximately".
- Remove jargon. When a technical term is the only accurate word, keep it and say what it means the first time.
- Spell out abbreviations or drop them.
- Name things by what the reader sees, not how the system works inside.
- Active voice, present tense, "you" for the reader.

## Short
- Keep sentences under about 20 words. Split any that run on with "and", "which", dashes or semicolons.
- Delete filler: "it's worth noting", "essentially", "basically", "in order to", needless hedges, restating the question, closing offers.
- No asides in dashes or parentheses.

## Simple examples
- One example per idea, the smallest that shows it. Use real names from the material (actual files, functions, values), never `foo`, `X` or `A/B/C`.
- If an example needs its own explanation, find a simpler one.
- For a flow or structure of more than three steps, use numbered steps or a small diagram instead of a paragraph.

## Keep exactly
Code, commands, paths, URLs and numbers stay as they were. Add no new facts, opinions or caveats. If the original contradicts itself or looks wrong, keep its content and flag that in one line at the end.

## Output
Only the rewritten text: no preamble, no "here's a simpler version", no list of changes. It should be clearly shorter than the original. If the original is already clear, say so in one line instead.
