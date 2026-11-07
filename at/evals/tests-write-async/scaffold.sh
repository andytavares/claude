#!/usr/bin/env bash
# Builds a tiny TypeScript + Vitest project. No install: the graders read the written test file.
set -euo pipefail
mkdir -p src
cat > package.json <<'JSON'
{
  "name": "debounce-demo",
  "private": true,
  "type": "module",
  "scripts": { "test": "vitest run" },
  "devDependencies": { "typescript": "5.6.3", "vitest": "2.1.4" }
}
JSON
cat > src/debounce.ts <<'TS'
export function debounce<Args extends unknown[]>(
  callback: (...args: Args) => void,
  delayMs: number,
): (...args: Args) => void {
  let timer: ReturnType<typeof setTimeout> | undefined;
  return (...args: Args) => {
    if (timer !== undefined) clearTimeout(timer);
    timer = setTimeout(() => callback(...args), delayMs);
  };
}
TS
git init -q && git add -A && git -c user.email=eval@example.com -c user.name=eval commit -q -m init
