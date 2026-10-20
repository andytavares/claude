set -e
mkdir -p services/orders services/catalog services/pricing gateway
for s in orders catalog pricing; do echo "export const handler = () => {}; // queries shared db directly" > services/$s/index.ts; done
echo "export const route = () => {};" > gateway/index.ts
echo '{ "scripts": { "test": "echo ok" } }' > package.json
git init -q && git add -A && git -c user.email=e@e -c user.name=e commit -qm init
