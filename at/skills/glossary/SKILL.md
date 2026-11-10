---
name: glossary
description: Use before you ask about, explain or design inside a repo, to read its glossary and decision records, and when a term is fixed or a hard-to-reverse decision is made, to write them. The store is outside the repo.
---
The glossary and decision records live in `~/at-skills-data`, never in the repo.

Find the directory: run `bash "${CLAUDE_SKILL_DIR}/path.sh"`. It prints `~/at-skills-data/<host>/<org>/<repo>`, from the `origin` remote. A repo with no remote gets `local/<folder>`. Worktrees and clones of one repo share the directory.

Read `GLOSSARY.md` and `adr/*.md` there first, if they exist. Use the terms in them in all your text and code names. When you meet a term the glossary does not hold, or one used in two ways, ask once and fix it.

## Write

Create files only when you have something to write. On the first write, run `git init -q` in `~/at-skills-data` if it has no `.git`. After each write, run `git -C ~/at-skills-data add -A && git -C ~/at-skills-data commit -q -m "glossary(<org>/<repo>): <what changed>"`. If `git config user.email` prints nothing, add `-c user.name=at -c user.email=at@localhost` after `git -C ~/at-skills-data` in the commit, so the commit works without a git identity. This store has no remote. Do not add one.

`GLOSSARY.md`: one entry per term, in this form. No file paths, no code, no how it works inside.

```
**<Term>**: what it is, in one sentence. _Avoid_: <names that mean something else>.
```

`adr/NNNN-<slug>.md`: write one only when all three are true: the decision is hard to reverse, it is surprising without context, and it was a real trade-off. Use the next number. Sections: Context, Decision, Consequences, each one to three sentences.

Never write secrets, tokens or customer data to the store.

Adapted from mattpocock/skills (MIT): https://github.com/mattpocock/skills/tree/main/skills/engineering/domain-modeling
