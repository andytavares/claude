set -e
mkdir -p src/routes src/export test
cat > src/routes/orders.ts <<'J'
import { listOrders } from "../db";
export function registerOrderRoutes(app: any) {
  app.get("/orders.json", (_req: any, res: any) => res.json(listOrders()));
}
J
echo 'export const listOrders = () => [{ id: 1, cents: 1250 }];' > src/db.ts
echo 'import test from "node:test"; test("json route", () => {});' > test/orders.test.ts
echo '{ "scripts": { "test": "node --test test/" } }' > package.json
git init -q && git add -A && git -c user.email=e@e -c user.name=e commit -qm init
