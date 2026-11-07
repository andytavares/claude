---
type: regex
target: { source: file, path: src/debounce.test.ts }
match: not_contains
pattern: 'setTimeout\(|sleep\(|waitForTimeout|new Promise\(\s*\(?r'
---
