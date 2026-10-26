set -e
mkdir -p src
cat > src/total.ts <<'J'
export function formatTotal(cents: number): string {
  return `$${(cents / 100).toFixed(2)}`;
}
export const receiptLine = (cents: number) => `Total: ${formatTotal(cents)}`;
J
echo '{ "scripts": { "test": "tsc --noEmit" } }' > package.json
git init -q && git add -A && git -c user.email=e@e -c user.name=e commit -qm init
