# Vitest — Integrations with the EOS Stack

How Vitest composes with every other tool in `/opt/OS/saas/*`.

## vite

**Relationship: same toolchain.** Vitest IS Vite with a `test` command.

- Reuse `vite.config.ts` via `mergeConfig` from `vitest/config`.
- Every Vite plugin (react, svgr, mdx, tsconfig-paths) is automatically
  active in tests. No second registration.
- `resolve.alias` carries over — `@/lib/foo` resolves the same way in
  prod and tests.
- `define` carries over — `import.meta.env.VITE_*` works in tests.
- **Gotcha:** if you have a separate `vitest.config.ts`, it does NOT
  inherit from `vite.config.ts` automatically. Use `mergeConfig` or
  duplicate the relevant fields.

## react

**Relationship: tested via @testing-library/react v16.**

- React 18 + concurrent mode supported. React 19 supported in
  @testing-library/react v16+.
- Use `render` from `@testing-library/react`, NOT `react-dom/test-utils`.
- Strict mode double-render is on by default in dev — wrap `render` in
  `<StrictMode>` to catch effect cleanup bugs in tests too.
- Server Components: experimental support via Vitest 3.x +
  `@testing-library/react` v17 (still rough as of Apr 2026).

## typescript

**Relationship: zero-config via Vite's esbuild transform.**

- No `ts-jest`, no `@swc/jest`. Vite handles TS via esbuild.
- `tsconfig.json` paths are picked up via `vite-tsconfig-paths` plugin.
- Type-checking is NOT done by Vitest — run `tsc --noEmit` separately,
  or use `vitest --typecheck` (slower, uses `vue-tsc`/`tsc` under the
  hood).
- Test types: install `@types/node` and Vitest's `globals: true` adds
  `describe/it/expect` to the global type space (via `vitest/globals`).

## react_hook_form

**Relationship: form tests are the most common Vitest test in EOS SaaS.**

- Use `userEvent.type()` for controlled inputs. Synthetic `fireEvent.change`
  often misses RHF's internal state updates.
- After submit, use `findByText` (not `getByText`) for validation errors —
  Zod resolution is async.
- For `<Controller>` wrapping Radix Select: requires the jsdom pointer
  stubs (see `examples.md` §2).
- Mock `react-hook-form`'s `useForm` ONLY when testing a parent that
  consumes `form` props — usually you should test the form end-to-end.

```tsx
const user = userEvent.setup();
await user.type(screen.getByLabelText(/email/i), "x@y.com");
await user.click(screen.getByRole("button", { name: /submit/i }));
expect(await screen.findByText(/created/i)).toBeInTheDocument();
```

## zod

**Relationship: tested via the form, not in isolation.**

- Test the user experience: "submit invalid → see error message".
- Don't test `schema.parse(badInput)` in unit tests — that tests Zod,
  not your code.
- DO unit-test custom refinements and transforms with `safeParse`.

## tanstack_react_query

**Relationship: fresh QueryClient per test, retry off, MSW for the network.**

```tsx
function makeQc() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: Infinity, staleTime: Infinity },
      mutations: { retry: false },
    },
  });
}
```

- **NEVER** share a QueryClient across tests.
- Set `retry: false` or tests wait the full 3-retry exponential backoff
  (~7 seconds) on every error case.
- For `useSuspenseQuery`: wrap in `<Suspense fallback={...}>` and assert
  on the fallback first, then `findBy*` for resolved data.
- For mutations: assert on the side effect (toast, redirect, cache
  update), not on the mutation function call.

## shadcn_ui

**Relationship: tested via Radix primitives — needs jsdom stubs.**

- Every shadcn component built on Radix (Select, Dialog, Popover,
  DropdownMenu, Combobox, Tooltip, Sheet, Drawer, AlertDialog) requires
  the pointer/scrollIntoView/Observer stubs in `setup.ts`.
- Without stubs you get: `TypeError: target.hasPointerCapture is not a
  function` or `Element.prototype.scrollIntoView is undefined`.
- For Tooltip tests, wrap in `<TooltipProvider>` (custom render does this).
- For Toast (Sonner) tests, mock `sonner` at the module level — testing
  the actual Toaster mount in jsdom is fragile.

## tailwind

**Relationship: do NOT load Tailwind CSS in jsdom.**

- Set `test.css: false` in vitest config.
- Tailwind class strings are opaque in tests. Don't assert on them.
- Test computed accessibility (`toBeDisabled`, `toHaveAccessibleName`)
  not visual styles.
- Visual regression goes to Playwright or Storybook + Chromatic.

## playwright

**Relationship: complementary, not competing.**

- **Vitest** = unit + integration. Component logic, hooks, utilities,
  form validation, MSW-mocked API. Fast (200ms cold), thousands of
  tests, runs on every save.
- **Playwright** = end-to-end. Real browser, real network, real auth,
  multi-page user journeys. Slow (seconds per test), tens of tests,
  runs on PR + nightly.
- **Vitest browser mode** = the middle ground. Real browser, real DOM,
  but single-component scope. Use when jsdom can't simulate the API
  (real `getBoundingClientRect`, focus management, pointer events).
- Don't try to do e2e in Vitest. Don't try to do unit tests in Playwright.

## msw (Mock Service Worker v2)

**Relationship: the network mocking layer for every Vitest test.**

- v2 syntax: `http.get(url, () => HttpResponse.json(...))`. The v1
  `rest.get` API is removed.
- `setupServer(...handlers)` from `msw/node` for Vitest (Node env).
- `setupWorker` from `msw/browser` for Vitest browser mode.
- Start in `beforeAll`, reset in `afterEach`, close in `afterAll`.
- `onUnhandledRequest: "error"` makes any unstubbed request fail loudly —
  catches forgotten handlers.
- Per-test overrides via `server.use(http.get(...))` — automatically
  cleared by `server.resetHandlers()`.
- TypeScript: import `HttpResponse` not `rest`. Type request bodies with
  `await request.json() as MyType`.

## sonner

**Relationship: mock the module in tests, assert on the spy.**

```ts
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(), error: vi.fn(), info: vi.fn(),
    warning: vi.fn(), loading: vi.fn(), promise: vi.fn(),
    dismiss: vi.fn(),
  },
}));
```

Then `expect(toast.success).toHaveBeenCalledWith("Lead created")`.
Testing the actual `<Toaster />` render in jsdom is fragile and
not what you care about anyway.

## storybook (boundary note)

Storybook 8 ships `@storybook/experimental-addon-test` powered by
Vitest browser mode. Stories become tests automatically. If you adopt
this, Vitest is the runner for both your `*.test.tsx` files AND your
`*.stories.tsx` files via a workspace project.

## ci (github actions)

```yaml
- run: npm ci
- run: npm run test:run -- --coverage --reporter=verbose --reporter=junit --outputFile=junit.xml
- uses: codecov/codecov-action@v4
  with: { files: ./coverage/lcov.info }
```

For sharded suites:
```yaml
strategy:
  matrix: { shard: [1, 2, 3, 4] }
steps:
  - run: npm run test:run -- --shard=${{ matrix.shard }}/4
```
