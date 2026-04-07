---
name: vitest
description: "Use when writing, debugging, configuring, or running unit/integration tests with Vitest — including React component tests with @testing-library, React Hook Form + Zod form tests, React Query async tests with fresh QueryClient wrappers, MSW v2 API mocking, vi.mock/vi.spyOn/vi.useFakeTimers patterns, jsdom + Radix pointer/scrollIntoView stubs, coverage v8 configuration with thresholds, in-source testing, workspace projects, browser mode, or migrating a Jest test suite to Vitest."
allowed-tools: "Read, Write, Edit, Bash, WebFetch, WebSearch"
version: 1.0
trigger: both
effort: high
context: fork
last_researched: "2026-04-06"
last_updated: "2026-04-06"
api_version: "2.x-3.x"
sdk_version: "vitest@2.1.x and 3.0.x"
source_url: "https://vitest.dev/"
speed_category: "fast"
sources:
  - "https://vitest.dev/guide/"
  - "https://vitest.dev/api/vi"
  - "https://vitest.dev/config/"
  - "https://vitest.dev/guide/mocking.html"
  - "https://vitest.dev/guide/coverage.html"
  - "https://vitest.dev/guide/browser/"
  - "https://vitest.dev/guide/in-source.html"
  - "https://vitest.dev/guide/migration.html"
  - "https://testing-library.com/docs/react-testing-library/intro/"
  - "https://mswjs.io/docs/"
---

# Tool: Vitest — The Vite-Native Test Runner

Vitest is **the test runner for every TypeScript/React app in `/opt/OS/saas`.**
Built by Anthony Fu (Vite, VueUse, Nuxt DevTools) on top of Vite. The pitch is
unification: your test runner uses the **exact same Vite config, plugins, and
transform pipeline** that ships your production bundle. No second toolchain. No
ts-jest. No babel-jest. No `transformIgnorePatterns` ESM pain. Tests start in
~200ms because Vite already had to parse the graph anyway.

The API is intentionally Jest-compatible (`describe/it/expect/vi`) so migration
is mostly find-and-replace `jest` → `vi`. The differences that matter are
mock hoisting semantics, ESM-first defaults, and a richer async toolkit
(`expect.poll`, `vi.waitFor`, `vi.advanceTimersByTimeAsync`).

## What Vitest Is

A Vite-powered test runner that:

1. Reuses `vite.config.ts` (resolve.alias, plugins, define, env) — one config.
2. Runs tests in worker threads with HMR-style watch mode (only affected
   tests rerun on file change).
3. Ships with `expect`, `vi` (mocks/spies/timers), snapshot, coverage (v8 and
   istanbul), and a browser mode that runs real component tests in real
   browsers via Playwright/WebdriverIO.
4. Is ESM-first. CJS still works but TLA, top-level imports, and Vite plugins
   are first-class.

## EOS Integration

Vitest lives in every SaaS workspace under `/opt/OS/saas/*`:

- `vitest.config.ts` (or `vite.config.ts` with a `test:` block) at app root.
- `src/test/setup.ts` — `@testing-library/jest-dom` matchers, MSW server
  start/stop, Radix pointer/scrollIntoView stubs.
- `src/test/test-utils.tsx` — custom `render()` that wraps every test
  component in `<QueryClientProvider>`, `<ThemeProvider>`, `<TooltipProvider>`.
- `src/mocks/handlers.ts` + `src/mocks/server.ts` — MSW v2 handlers shared
  across tests; per-test overrides via `server.use(...)`.
- `*.test.tsx` colocated with source. CI runs `vitest run --coverage` with
  v8 provider and 80%/70%/80%/80% thresholds.

**Stack partners:** Vite (config + transform), React 18, TypeScript,
@testing-library/react v16, @testing-library/user-event v14, MSW v2,
React Hook Form + Zod (form tests), TanStack Query (async tests), shadcn/ui
+ Radix UI (jsdom stub gotchas), Playwright (e2e boundary — Vitest stops
where Playwright starts).

## Authentication

**N/A — Vitest is a local test runner.** Zero network surface, no API keys,
no tokens, no rate limits, nothing to authenticate. The package installs to
`node_modules`, runs in Node worker threads, and never phones home. Telemetry
is opt-in only via `--reporter`.

The "auth-like" concerns that matter:

- **Version pinning.** Vitest 2.x and 3.x ship breaking changes between
  minors. Pin exact in `package.json` (`"vitest": "2.1.9"`) and bump
  intentionally with `@vitest/coverage-v8` and `@vitest/ui` matched to the
  same minor. Mismatched versions throw obscure resolver errors.
- **Peer Vite.** Vitest 2.x requires Vite ≥5. Vitest 3.x requires Vite ≥5.4.
  If your app is on Vite 4, stay on Vitest 1.x or upgrade Vite first.
- **Node version.** Vitest 2.x requires Node 18.17+ or 20.5+. Older Node
  fails on `node:test` reporter and `--experimental-vm-modules`.

## Quick Reference

### Minimal config (React + jsdom + setup file)

```ts
// vitest.config.ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: false,
    restoreMocks: true,
    clearMocks: true,
    coverage: {
      provider: "v8",
      reporter: ["text", "html", "lcov"],
      exclude: ["**/*.config.*", "**/*.d.ts", "src/main.tsx"],
      thresholds: { lines: 80, functions: 80, branches: 70, statements: 80 },
    },
  },
});
```

### The five canonical patterns

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// 1. Component render + interaction (userEvent.setup() once per test)
it("submits form", async () => {
  const user = userEvent.setup();
  render(<LeadForm onSubmit={vi.fn()} />);
  await user.type(screen.getByLabelText(/name/i), "Antony");
  await user.click(screen.getByRole("button", { name: /submit/i }));
  expect(await screen.findByText(/created/i)).toBeInTheDocument();
});

// 2. Module mock (HOISTED — top of file, before imports use it)
vi.mock("@/lib/api", () => ({ createLead: vi.fn().mockResolvedValue({ id: 1 }) }));

// 3. Spy on real implementation
const spy = vi.spyOn(console, "error").mockImplementation(() => {});

// 4. Fake timers — async-aware
beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }));
await vi.advanceTimersByTimeAsync(1000);

// 5. expect.poll for eventual consistency
await expect.poll(() => store.getState().count, { timeout: 2000 }).toBe(5);
```

## Gotchas

See `references/best_practices.md` for full creator-level protocol and
`references/anti_patterns.md` for failure modes. Highlights:

- **`vi.mock` is HOISTED to the top of the file.** Variables you reference
  inside the factory must either be inside `vi.hoisted(() => ...)` or be
  imported. Closing over a top-level `const mockFn = vi.fn()` throws
  `Cannot access 'mockFn' before initialization`. Use `vi.hoisted`.

- **Never share a `QueryClient` across tests.** Create a fresh one per test
  with `retry: false, gcTime: Infinity`. A shared client leaks cache
  between tests and produces order-dependent failures.

- **Always `await` every `userEvent` call.** userEvent v14 returns promises
  for every interaction. Forgetting `await` produces silent flakes that
  pass locally and fail in CI under load.

- **jsdom is missing `hasPointerCapture`, `scrollIntoView`, `ResizeObserver`,
  and `IntersectionObserver`.** Radix UI primitives (Select, Dialog,
  Popover, DropdownMenu) crash on these. Stub them in `setup.ts` (see
  `references/examples.md`).

- **Tailwind CSS does not load in jsdom.** `getByRole` works because it
  reads ARIA, but querying by computed class is meaningless. Test behavior,
  not classNames.

- **MSW v2 handlers must use the new `http.get(url, () => HttpResponse.json(...))`
  syntax** — the v1 `rest.get` API is gone. Mocking `fetch` directly
  instead of using MSW is the #1 anti-pattern in 2026 React test suites.

- **`vi.useFakeTimers()` without `shouldAdvanceTime: true` breaks
  `userEvent`** because userEvent uses `setTimeout(0)` for keystrokes.
  Either pass `{ advanceTimers: vi.advanceTimersByTime }` to
  `userEvent.setup()` or use `shouldAdvanceTime`.

- **`restoreMocks: true` in config restores `vi.spyOn` originals, but does
  NOT reset `vi.fn()` implementations.** Use `clearMocks: true` for call
  history and `mockReset: true` if you also want implementations cleared.

- **Snapshot tests are a smell for components.** They lock you into
  implementation. Snapshot only stable, presentational, prop-driven
  output. Test behavior with `getByRole` instead.

- **Coverage v8 is faster than istanbul** but reports slightly different
  branch coverage because it uses native V8 counters. Pick one and stick
  with it for thresholds.

- **`environment: "jsdom"` is set globally**, but you can override per file
  with `// @vitest-environment node` at the top. Useful for pure logic
  files that should not pay the jsdom startup cost.

- **In-source testing (`if (import.meta.vitest)`)** is great for utility
  modules but the import is stripped in production builds only if you
  set `define: { "import.meta.vitest": "undefined" }` in
  `vite.config.ts`. Forget this and your test code ships to prod.

## References

- `references/best_practices.md` — full 19-section creator-level protocol.
- `references/examples.md` — runnable test code: RHF+Zod, React Query,
  MSW v2, Radix stubs, fake timers, coverage, in-source, table tests.
- `references/anti_patterns.md` — real failure modes and fixes.
- `references/integrations.md` — vite, react, typescript, react_hook_form,
  zod, tanstack_react_query, shadcn_ui, tailwind, playwright, msw.
