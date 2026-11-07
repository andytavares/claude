# Runner controls

Read the installed version of each tool before you set an option (`npm ls <name>`, `uv pip show <name>`). Options change between majors; then read that version's docs. Each item names the rule it enforces and the doc it came from. `[UNVERIFIED]` means no doc confirmed it.

"More workers than cores": set the worker count to twice the core count (`sysctl -n hw.ncpu` on macOS, `nproc` on Linux).

## pytest

- **Shuffle and seed replay** (T-ALONE): pytest-randomly shuffles on install and prints `Using --randomly-seed=<n>`. Replay with `pytest -p randomly --randomly-seed=<n>`, or `--randomly-seed=last`. It also reseeds `random` before each test. Turn it off with `-p no:randomly`. https://github.com/pytest-dev/pytest-randomly
- **Repeat** (T-ALONE): pytest-repeat, `pytest --count=30 <file>`; `--repeat-scope` is `function` by default. https://github.com/pytest-dev/pytest-repeat
- **Workers**: pytest-xdist, `pytest -n <2 × cores>`. [UNVERIFIED] not checked in Context7.
- **Network block** (T-BOUNDARY): pytest-socket. Unit: `pytest --disable-socket`. Integration and E2E: `pytest --disable-socket --allow-hosts=127.0.0.1`. Put the flags in `addopts` in `pytest.ini` or `pyproject.toml`. `--force-enable-socket` and `@pytest.mark.enable_socket` undo the block; find them in the audit. https://github.com/miketheman/pytest-socket
- **Mock and env restore** (T-CLEAN-SLATE): the `monkeypatch` fixture undoes `setattr`, `setenv` and `delenv` after each test. Use `tmp_path` for files. https://docs.pytest.org/en/stable/how-to/monkeypatch.html
- **Fake time** (T-CONTROL-TIME): no core fixture. Use the project's library, such as `time-machine` or `freezegun`. [UNVERIFIED] options not checked.
- **Retries off** (T-NO-RETRY): find `--reruns` and `@pytest.mark.flaky` (pytest-rerunfailures) in config and CI. [UNVERIFIED] flag names not checked in Context7.
- **Lint** (T-READABLE, T-CAN-FAIL): ruff `[tool.ruff.lint] select = ["PT"]`. Rules include PT009, PT011, PT012, PT015, PT016, PT018, PT027. https://docs.astral.sh/ruff/rules/

## Vitest

- **Shuffle and seed replay** (T-ALONE): `vitest run --sequence.shuffle --sequence.seed=<n>`, or `sequence: { shuffle: true }` in config. The seed defaults to `Date.now()`. Always pass `--sequence.seed` so the run has a known seed. [UNVERIFIED] whether Vitest prints the seed. https://vitest.dev/config/sequence
- **Repeat** (T-ALONE): `vitest run <file> --repeats=29` runs each test 30 times. Config: `repeats`. A test fails if any repeat fails. https://vitest.dev/config/repeats
- **Workers**: `--maxWorkers=<n>`, a number or a percentage. https://vitest.dev/config/maxworkers
- **Network block** (T-BOUNDARY): Vitest has no socket block. Use MSW with unhandled requests as errors (see MSW).
- **Mock, env and global restore** (T-CLEAN-SLATE): `test: { restoreMocks: true, unstubEnvs: true, unstubGlobals: true }`. https://vitest.dev/config/restoremocks, https://vitest.dev/config/unstubenvs, https://vitest.dev/config/unstubglobals
- **Fake timers** (T-CONTROL-TIME): `vi.useFakeTimers()`, `vi.setSystemTime(date)`, config `fakeTimers.toFake`. https://vitest.dev/api/vi
- **Wait on a condition** (T-WAIT-CONDITION): `await expect.poll(() => value).toBe(expected)`. https://vitest.dev/guide/recipes/wait-for
- **Retries off** (T-NO-RETRY): `retry` defaults to `0`. Find `retry` in config and `--retry` in scripts and CI. https://vitest.dev/config/retry

## Jest

- **Shuffle and seed replay** (T-ALONE): `jest --randomize --seed=<n>`. `--randomize` prints the seed. Config: `randomize: true` in the root config only. jest-circus runner only. https://jestjs.io/docs/cli#--randomize
- **Repeat** (T-ALONE): no repeat flag found. Run the file 30 times in a loop, each with `--randomize`. [UNVERIFIED] no repeat option.
- **Workers**: `--maxWorkers=<n>`. [UNVERIFIED] not checked in Context7.
- **Mock restore** (T-CLEAN-SLATE): `restoreMocks: true` in config, or `--restoreMocks`. https://jestjs.io/docs/cli#--restoremocks
- **Fake timers** (T-CONTROL-TIME): `fakeTimers: { enableGlobally: true }` in config. https://jestjs.io/docs/configuration#faketimers-object
- **Retries off** (T-NO-RETRY): find `jest.retryTimes` in tests and setup files. [UNVERIFIED] not checked in Context7.

## Testing Library

- **Wait for the target** (T-READY-TARGET, T-WAIT-CONDITION): `await screen.findByRole(...)`, not `waitFor(() => getBy...)`. https://testing-library.com/docs/dom-testing-library/api-async
- **User input** (T-READABLE): `const user = userEvent.setup()`, then `await user.click(...)`. https://testing-library.com/docs/user-event/intro
- **Lint**: eslint-plugin-testing-library, flat config `testingLibrary.configs['flat/react']` (also `flat/dom`, `flat/vue`, `flat/angular`, `flat/svelte`, `flat/marko`). Rules: `prefer-find-by`, `prefer-user-event`, `prefer-screen-queries`, `prefer-presence-queries`, `await-async-queries`, `no-wait-for-side-effects`, `no-wait-for-multiple-assertions`, `no-node-access`. https://github.com/testing-library/eslint-plugin-testing-library

## Playwright

- **Shuffle and seed replay** (T-ALONE): `npx playwright test --shuffle [seed]`. It prints the seed. Check that the installed version has the flag. https://playwright.dev/docs/test-cli
- **Repeat** (T-ALONE): `npx playwright test <file> --repeat-each=5 --retries=0 --workers=<n>`. https://playwright.dev/docs/test-cli
- **Retries off** (T-NO-RETRY): `retries: 0` in `playwright.config.ts`. The default is no retries. https://playwright.dev/docs/api/class-testconfig#test-config-retries
- **Network block** (T-BOUNDARY): in a fixture or `beforeEach`, `await context.route(url => !['localhost', '127.0.0.1'].includes(url.hostname), route => route.abort())`. `page.route` misses Service Worker requests; set `serviceWorkers: 'block'`. https://playwright.dev/docs/api/class-page#page-route, https://playwright.dev/docs/network
- **Clock** (T-CONTROL-TIME): `await page.clock.install({ time })`, then `page.clock.fastForward(...)` or `pauseAt(...)`. https://playwright.dev/docs/clock
- **Lint**: eslint-plugin-playwright rules `playwright/no-wait-for-timeout` and `playwright/missing-playwright-await`. https://github.com/mskelton/eslint-plugin-playwright

## MSW

- **Unhandled requests as errors** (T-BOUNDARY): MSW 2.x: `server.listen({ onUnhandledRequest: 'error' })`. MSW 3.x renamed it: `server.listen({ onUnhandledFrame: 'error' })`. Check the installed major with `npm ls msw`. https://mswjs.io/docs/migrations/2.x-to-3.x
- **Restore** (T-CLEAN-SLATE): `afterEach(() => server.resetHandlers())`, `afterAll(() => server.close())`. https://mswjs.io/docs/quick-start
- MSW intercepts HTTP clients in the process. It does not block raw sockets.

## ESLint rules for tests

- **Fixed delays** (T-WAIT-CONDITION): in the test-file override,
  `"no-restricted-syntax": ["error", { "selector": "CallExpression[callee.property.name='waitForTimeout']", "message": "Wait on a condition (T-WAIT-CONDITION)." }, { "selector": "CallExpression[callee.name='setTimeout']", "message": "Use fake timers or a retrying assertion (T-WAIT-CONDITION)." }]`.
  https://eslint.org/docs/latest/rules/no-restricted-syntax
- **Floating promises** (T-AWAIT-ALL): `"@typescript-eslint/no-floating-promises": "error"`. It needs type information: `parserOptions: { projectService: true }`. https://typescript-eslint.io/getting-started/typed-linting

## Other runners

For a runner not listed here, such as Go `go test`, JUnit or RSpec, find the same controls in that runner's docs: shuffle with a seed, repeat, network block, state restore, fake time, retries off and lint rules. Put the doc link beside each control you use. In the report, name each rule that could not be checked by a program for that runner, and the reason.
