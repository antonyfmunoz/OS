# Vitest — Creator-Level Best Practices (19-Section Protocol)

Anthony Fu's Vite-native test runner. Reference covers Vitest 2.1.x and 3.0.x,
@testing-library/react v16, @testing-library/user-event v14, MSW v2.

## Authentication

**N/A — Vitest is a local Node test runner.** No network surface, no API keys,
no OAuth, no scopes, no rate limits, no webhooks. The package installs to
`node_modules` and runs entirely in worker threads on the developer's
machine or in CI. Telemetry is opt-in.

The "auth-equivalent" discipline is **version pinning**: lock `vitest`,
`@vitest/coverage-v8`, `@vitest/ui`, and `@vitest/browser` to the same exact
minor in `package.json`. Mismatched minors throw resolver errors with
unhelpful stack traces ("Cannot find module 'vitest/node'") that look like
install corruption but are actually version skew.

## Core Operations

**Run modes.**
- `vitest` — watch mode, default. HMR-style: only affected tests rerun.
- `vitest run` — single-pass for CI. No watch.
- `vitest run --coverage` — single-pass with coverage report.
- `vitest --ui` — browser UI at http://localhost:51204/__vitest__/.
- `vitest --reporter=verbose` — full test name list (CI logs).
- `vitest --project=unit` — run only the named workspace project.
- `vitest related src/lib/foo.ts` — run only tests touching that file.
- `vitest bench` — benchmark mode using `bench()` from `vitest`.

**Test definition.**
```ts
import { describe, it, test, expect, beforeAll, afterAll, beforeEach, afterEach } from "vitest";

describe("LeadForm", () => {
  beforeAll(async () => { /* one-time setup */ });
  afterAll(() => { /* one-time teardown */ });
  beforeEach(() => { /* per-test setup */ });
  afterEach(() => { /* per-test teardown */ });

  it("submits valid input", async () => { /* ... */ });
  test.skip("future feature", () => {});
  test.only("focused debug", () => {});
  test.todo("not implemented yet");
  test.fails("known broken — passes when this throws", () => { throw new Error(); });
  test.concurrent("runs in parallel within describe.concurrent", async () => {});
  test.each([[1, 2, 3], [2, 3, 5]])("adds %i + %i = %i", (a, b, sum) => {
    expect(a + b).toBe(sum);
  });
});
```

**Mocking surface (`vi.*`).** See `## SDK Idioms` for the full table.

## Pagination

**N/A — Vitest is a test runner, not an API client.** There is no result
pagination. The closest analog is **test sharding** for distributed CI:
`vitest run --shard=1/4` runs 25% of test files. Use this with GitHub Actions
matrix builds when your suite exceeds ~5 minutes wall time. Sharding is
file-level, not test-level — files within a shard run normally.

## Rate Limits

**N/A — no external service.** The closest analog is **worker concurrency**.
Vitest defaults to one worker per CPU core. On a constrained CI runner this
swamps the box. Tune with:

```ts
test: {
  poolOptions: {
    threads: { minThreads: 1, maxThreads: 4, singleThread: false },
  },
  fileParallelism: true, // false = run files sequentially (debug only)
  testTimeout: 5000,     // per-test default; bump for slow integrations
  hookTimeout: 10000,
}
```

**Pool choice.** `pool: "threads"` (default, fast, isolated worker threads),
`pool: "forks"` (slower, full process isolation — use when native modules
break in workers), `pool: "vmThreads"` (experimental, isolated VM contexts).

## Error Codes

**N/A — Vitest throws regular JavaScript errors with stack traces.** No
numeric error codes. Common error patterns and meanings:

| Error pattern | Cause | Fix |
|---|---|---|
| `Cannot access 'X' before initialization` (in `vi.mock` factory) | Closing over a top-level variable in a hoisted mock factory | Wrap variable creation in `vi.hoisted(() => ...)` |
| `ReferenceError: document is not defined` | Test file uses DOM APIs but `environment: "node"` | Set `environment: "jsdom"` or add `// @vitest-environment jsdom` to file |
| `Error: Failed to load url X` | Vite plugin or alias missing in test config | Reuse `vite.config.ts` via `mergeConfig` or duplicate `resolve.alias` |
| `TypeError: Cannot read properties of null (reading 'hasPointerCapture')` | Radix UI on jsdom | Stub `Element.prototype.hasPointerCapture` in setup file |
| `Error: scrollIntoView is not a function` | Radix Select/Combobox on jsdom | Stub `Element.prototype.scrollIntoView = vi.fn()` |
| `Snapshot file not written` in CI | `--run` mode with `--passWithNoTests=false` and no existing snapshot | Run locally first or use `--update` (carefully) |
| `Error: Test timed out in 5000ms` | Slow async or missing `await` | Increase `testTimeout` OR fix the missing await (usually the latter) |
| `Module did not self-register` | Native module loaded in worker thread | Switch to `pool: "forks"` |

## SDK Idioms

**Mock module (hoisted, top of file).**
```ts
vi.mock("@/lib/api", () => ({
  createLead: vi.fn().mockResolvedValue({ id: 1, name: "Mock" }),
  deleteLead: vi.fn(),
}));
import { createLead } from "@/lib/api"; // resolves to the mock
```

**Mock with `vi.hoisted` (when factory needs a shared ref).**
```ts
const { mockCreate } = vi.hoisted(() => ({ mockCreate: vi.fn() }));
vi.mock("@/lib/api", () => ({ createLead: mockCreate }));
// now mockCreate is callable in tests AND resolved at hoist time
```

**Partial mock — keep real exports, override one.**
```ts
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, createLead: vi.fn().mockResolvedValue({ id: 1 }) };
});
```

**Spy on real implementation.**
```ts
const errSpy = vi.spyOn(console, "error").mockImplementation(() => {});
// ... test ...
errSpy.mockRestore();
```

**Fake timers (async-aware, userEvent-compatible).**
```ts
beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true, toFake: ["setTimeout", "setInterval", "Date"] }));
afterEach(() => vi.useRealTimers());

await vi.advanceTimersByTimeAsync(1000); // advances + flushes microtasks
vi.setSystemTime(new Date("2026-01-01"));
```

**Stub globals and env.**
```ts
vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("ok")));
vi.stubEnv("VITE_API_URL", "http://test.local");
afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); });
```

**Eventual consistency.**
```ts
await expect.poll(() => store.getState().count, { timeout: 2000, interval: 50 }).toBe(5);
await vi.waitFor(() => expect(spy).toHaveBeenCalled(), { timeout: 1000 });
await vi.waitUntil(() => element.isConnected, { timeout: 500 });
```

**Snapshot variants.**
```ts
expect(obj).toMatchSnapshot();          // file snapshot
expect(obj).toMatchInlineSnapshot();    // inline — auto-filled by --update
expect(html).toMatchFileSnapshot("./__snapshots__/output.html"); // external file
```

**Concurrent describe.**
```ts
describe.concurrent("parallel suite", () => {
  it("a", async ({ expect }) => { /* destructure expect for isolation */ });
  it("b", async ({ expect }) => {});
});
```

## Anti-Patterns

See `references/anti_patterns.md`. Top five:

1. **Mocking `fetch` directly** instead of using MSW v2. Brittle, untyped,
   misses request validation, breaks when code switches to `axios`.
2. **Sharing a `QueryClient` across tests.** Order-dependent failures.
3. **Querying by `data-testid` when `getByRole` works.** Tests implementation,
   not user experience.
4. **Snapshot testing complex components.** Locks visual structure;
   regenerated on every refactor; nobody reads the diff.
5. **Forgetting `await` on `userEvent.click()`.** Silent flakes.

## Data Model

**N/A — Vitest does not have a domain data model.** The closest analog is
the **test runner's internal model**: a tree of `Suite → Suite → Test`
nodes with `TaskState` (`run`, `pass`, `fail`, `skip`, `todo`, `only`).
You interact with this via reporters (`--reporter=json` emits the tree)
and the programmatic API in `vitest/node` (`startVitest`, `Vitest.state`).

## Webhooks

**N/A — local test runner.** The closest analog is the **reporter API**:
custom reporters receive lifecycle events (`onTestStart`, `onTestFinish`,
`onCollected`, `onFinished`) and can push results anywhere — Slack, GitHub
checks, a database, an LLM critic. Implement `Reporter` interface from
`vitest/reporters`.

```ts
// custom-reporter.ts
import type { Reporter } from "vitest/reporters";
export default class SlackReporter implements Reporter {
  onFinished(files, errors) {
    if (errors.length) fetch(SLACK_WEBHOOK, { method: "POST", body: JSON.stringify({ text: `${errors.length} failures` }) });
  }
}
// vitest.config.ts → test.reporters: ["default", "./custom-reporter.ts"]
```

## Limits

**Soft limits to know:**
- **Default test timeout:** 5000ms. Bump per-test: `it("slow", { timeout: 30000 }, async () => {})`.
- **Hook timeout:** 10000ms. Same per-hook override.
- **Concurrent tests in `describe.concurrent`:** bounded by `maxConcurrency`
  (default 5).
- **Worker count:** defaults to CPU count. Hard cap via `poolOptions.threads.maxThreads`.
- **Snapshot file size:** no limit, but >50KB snapshots are a smell — split or move to file snapshot.
- **Coverage report size on monorepo:** v8 is ~3x faster and ~5x smaller than istanbul on a 50k LOC codebase.

## Cost Model

**N/A — Vitest is free and runs locally.** The real cost is **CI minutes**.
Optimization levers in priority order:
1. Sharding across runners (`--shard=1/4`).
2. `vitest run --changed` to test only changed files in PRs.
3. Drop snapshot tests that nobody reads.
4. Move slow integration suites to a separate workspace project that runs
   on-demand, not on every PR.
5. Switch coverage provider from istanbul to v8 (3x faster).
6. Cache `node_modules` and `.vite/` between runs.

## Version Pinning

**Pin exact versions.** Vitest 2.x and 3.x ship breaking changes between
minors. Recommended package.json (as of 2026-04-06):

```json
{
  "devDependencies": {
    "vitest": "2.1.9",
    "@vitest/coverage-v8": "2.1.9",
    "@vitest/ui": "2.1.9",
    "@testing-library/react": "16.1.0",
    "@testing-library/user-event": "14.5.2",
    "@testing-library/jest-dom": "6.6.3",
    "jsdom": "25.0.1",
    "msw": "2.7.0"
  }
}
```

Vitest 3.0 (Jan 2026) is the cutting edge but ships a redesigned reporter
API that breaks custom reporters. Stay on 2.1 until 3.x stabilizes
ecosystem packages.

## Design Intent

Anthony Fu's thesis: **the test runner should be a Vite plugin, not a
parallel toolchain.** Pre-Vitest, every Vite app needed Jest + ts-jest +
babel-jest + a separate `jest.config.js` that re-implemented the
resolve.alias and transform pipeline already present in `vite.config.ts`.
That duplication was the actual problem — not test speed, not API ergonomics.

By making the runner reuse Vite's transform pipeline:
- Tests use the **same alias resolution** as production.
- Tests pay the **same transform cost** as the dev server (which is near zero
  because Vite caches aggressively).
- Tests inherit **every Vite plugin** automatically (SVG-as-component,
  MDX, Vue SFC, etc.).
- ESM is **first-class** instead of bolted on with `--experimental-vm-modules`.

The Jest-compatible API (`describe/it/expect/vi`) is a **migration affordance**,
not the design center. Anthony's stated goal: "make migration cost near zero
so people actually try it." It worked — Vitest passed Jest in monthly downloads
in mid-2024.

## Problem-Solution Map

| Problem | Vitest solution |
|---|---|
| ts-jest takes 30s to start | Vite transform pipeline; ~200ms cold start |
| `transformIgnorePatterns` ESM hell | Vitest is ESM-first; no patterns needed |
| Two configs (vite + jest) drift | One config; `test:` block in `vite.config.ts` |
| Snapshot diffs unreadable | Inline snapshots auto-fill via `--update` |
| Async race conditions | `vi.waitFor`, `expect.poll`, async fake timers |
| Slow CI | Sharding + `--changed` + v8 coverage |
| Component tests fake DOM | Browser mode runs real Chromium via Playwright |
| Migrate from Jest | API compat — find/replace `jest` → `vi` |
| Test utility code without test files | In-source testing via `if (import.meta.vitest)` |
| Multiple test configs in one repo | Workspace projects |

## Operational Behavior

**Watch mode dependency graph.** Vitest builds a module graph from Vite's
own graph. When you save `src/lib/foo.ts`, Vitest reruns every test file
that imports `foo.ts` directly or transitively — usually 2-5 files instead
of the whole suite. This is the killer feature.

**Worker isolation.** Each test file runs in its own worker thread by
default. Module state, mocks, and timers are isolated per file. Within a
file, tests share state unless `describe.concurrent` is used.

**Mock hoisting.** `vi.mock()` calls are hoisted to the top of the file
**before** any imports. This is the same as Jest, but Vitest does it via
the Vite transform plugin (not Babel). The implication: factory closures
must use `vi.hoisted()` for any references that would otherwise be
temporal-dead-zone.

**Snapshot updates.** `vitest run --update` (or `-u`) regenerates all
snapshots. In watch mode, press `u` to update for the failing test only.

**Coverage v8 vs istanbul.** v8 uses native V8 coverage counters — fast,
no source instrumentation, slightly looser branch coverage. istanbul
instruments source — slower, exact branches, slightly different line
counts. Most teams run v8.

## Ecosystem Position

**Vitest is the default test runner for any Vite-based project in 2026.**
Adoption signals:
- shadcn/ui templates ship Vitest, not Jest.
- Astro, SvelteKit, Nuxt, SolidStart all default to Vitest.
- Next.js still defaults to Jest because Next is webpack/turbopack-based
  (not Vite), but the Next docs now include a Vitest setup guide.
- Storybook 8 added a `@storybook/experimental-addon-test` powered by
  Vitest browser mode — stories become tests.

**Boundaries.**
- **Vitest = unit + integration tests.** Component logic, hooks, utilities,
  form validation, API mocks via MSW.
- **Playwright = end-to-end + visual regression.** Real browser, real
  network, real auth flows, multi-page user journeys.
- **Vitest browser mode** sits between the two — real browser, real DOM,
  but single-component scope. Use it when jsdom can't simulate the API
  (e.g., real `getBoundingClientRect`, real focus management, real
  pointer events for Radix).

**Competitors.**
- Jest — still the largest installed base, slower, CJS-first, ts-jest tax.
- node:test — built-in to Node 20+, minimal API, no jsdom, no React tooling.
  Good for pure-Node libraries; not for React apps.
- Mocha + Chai — legacy, no React tooling, no built-in mocks.
- Bun test — fast, Bun-only, limited React tooling.

## Trajectory

**Where Vitest is going (2026 and beyond):**
- **Vitest 3.0** (released Jan 2026): redesigned reporter API, faster
  watch mode, native browser mode out of experimental, workspace projects
  renamed to "test projects" with simpler config, deprecated `vi.mocked`
  signature.
- **Browser mode going GA** as the default for component testing once
  Playwright integration stabilizes. The pitch: jsdom is a lie; test in
  a real browser, fast.
- **AI-assisted test generation** via Vitest's structured task tree —
  reporters can feed test results to an LLM critic that proposes
  additional cases. Several plugins shipping in 2026.
- **Server Component testing** via `@testing-library/react` v17 +
  Vitest's experimental RSC environment. Still rough; expect production
  readiness late 2026.
- **Convergence with Storybook 8 Test addon** — stories as tests, tests
  as stories, single source of truth.

## Conceptual Model

Think of Vitest as **Vite with a `test` command bolted on**. Same module
graph, same transform pipeline, same plugin system, same alias resolution.
The test runner is just another consumer of the Vite dev server — it
imports your code via Vite's resolver, runs it in a worker, and asserts
on the result.

Mental model layers (top to bottom):
1. **CLI / UI / Watch mode** — orchestrates runs, watches files.
2. **Vite dev server** — resolves modules, applies transforms, caches.
3. **Worker pool** — runs test files in isolated threads.
4. **Test environment** (`jsdom` / `happy-dom` / `node` / `browser`) —
   provides globals like `document`, `window`, `Element`.
5. **Test runtime** — `describe`, `it`, `expect`, `vi`, lifecycle hooks.
6. **Reporters** — consume task tree, emit output (default, verbose, json,
   junit, custom).

The unifying insight: **your tests run the exact same code path as your
production build minus minification.** No second toolchain to drift.

## Industry Expert

**Anthony Fu** — Vitest creator, Vite core team, Nuxt core team, VueUse
creator, UnoCSS creator. Based in Shanghai. Prolific OSS maintainer with a
distinctive philosophy:

1. **Tools should compose, not duplicate.** Vitest reuses Vite. UnoCSS
   reuses PostCSS. Nuxt DevTools reuses Vite plugins. Anti-monolith.
2. **Migration cost is the real adoption barrier.** Vitest's Jest-compatible
   API was a deliberate bet that "API parity beats API perfection."
3. **DX is a feature.** Vitest UI, inline snapshots, `--changed`, watch
   mode HMR — all DX investments that competitors deprioritized.
4. **OSS as a public craft.** Anthony streams development on Twitch and
   blogs every Vitest release in detail. Read the v2.0 and v3.0 release
   notes for design rationale that doesn't appear in docs.

**Other voices to follow:**
- **Vladimir Sheremet (@sheremet-va)** — Vitest core maintainer, owns the
  mocking and module graph internals. Best source on `vi.mock` semantics.
- **Kent C. Dodds** — Testing Library author. His "test behavior, not
  implementation" thesis is the philosophical backbone of every modern
  React test suite. Read "Common Mistakes with React Testing Library."
- **Artem Zakharchenko** — MSW author. His "request handlers as the API
  contract" model is why MSW v2 replaced `nock` and direct fetch mocks.
- **Kettanaito** — MSW maintainer; writes the deepest material on why
  network-level mocking beats function-level mocking.

Read these four people and you have the entire 2026 React testing
worldview.
