# Clean code

Readability decides every tie. A reader should follow any change from its entry point to its end without asking the author anything.

## Reuse first
Before adding a function, type or constant, search for one that already does the job: `git grep -w` on the likely name and on a key literal, and the LSP's workspace symbols. Use it, or extend it if it is close. Private copies drift: three `relativeTime()` helpers in one repo each ended up with a different output.

## Match the neighbours
Find the closest existing example of what you are adding and copy its shape: file layout, naming, error handling, test style.

## Small units
A function does one thing at one level of abstraction. New code stays within 30 lines, complexity 10 and 3 parameters; the clean-gate hook reports anything over. Split at a boundary you can name, never at an arbitrary line.

## Names carry the meaning
A name says what the thing is or does, in the domain's words. No abbreviations.

## Comments
A comment states a constraint the code cannot show, in one to three lines. Do not add comments or docstrings to code you did not change.

## Only what was asked
Validate only at system boundaries (user input, external APIs); no handling for cases that cannot happen. No helpers for one-time operations. No configurability nobody asked for.

## Show the reader the way
Every PR body has a "How to read this change" section: the entry point, then each step in call order as `path:line`.
