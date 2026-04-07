# Vitest — Anti-Patterns and Failure Modes

Real failures that show up in EOS SaaS code review. Each entry: the
anti-pattern, why it bites, the fix.

## 1. Mocking `fetch` directly instead of MSW

```ts
// BAD
global.fetch = vi.fn().mockResolvedValue({
  ok: true, json: async () => ({ id: 1 }),
} as Response);
```

**Why it bites:** untyped, doesn't validate URL/method/body, breaks the
moment code switches from `fetch` to `axios` or adds an interceptor,
leaks across tests, no request assertion possible.

**Fix:** MSW v2 with `setupServer`. Mocks at the network layer, type-safe,
contract-driven, survives library swaps.

```ts
// GOOD
server.use(http.get("/api/leads", () => HttpResponse.json([{ id: 1 }])));
```

## 2. Sharing a QueryClient across tests

```tsx
// BAD — module-level singleton
const queryClient = new QueryClient();
beforeEach(() => render(<QueryClientProvider client={queryClient}>...));
```

**Why it bites:** cache persists between tests. Test A populates
`["leads"]`, test B reads stale data, test C fails depending on order.
Hidden coupling = order-dependent flakes.

**Fix:** fresh client per test with retry off.

```tsx
// GOOD
beforeEach(() => {
  qc = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: Infinity } } });
});
```

## 3. Querying by `data-testid` when role works

```tsx
// BAD
screen.getByTestId("submit-btn");
```

**Why it bites:** tests implementation, not user experience. Screen
readers don't see `data-testid`. If your test passes but a blind user
can't use the button, the test is lying.

**Fix:** query by accessible role/label/text. If you can't, the
component has an a11y bug — fix it.

```tsx
// GOOD
screen.getByRole("button", { name: /submit/i });
```

Query priority (Testing Library official): `getByRole` > `getByLabelText`
> `getByPlaceholderText` > `getByText` > `getByDisplayValue` > `getByAltText`
> `getByTitle` > `getByTestId` (last resort).

## 4. Not awaiting userEvent calls

```tsx
// BAD
const user = userEvent.setup();
user.click(btn); // returns Promise — no await
expect(spy).toHaveBeenCalled(); // race condition
```

**Why it bites:** userEvent v14 is async for every interaction. Without
`await`, assertions run before the click handler resolves. Passes
locally on a fast machine, fails in CI under load.

**Fix:** `await user.click(btn)`. Always.

## 5. Snapshot testing complex components

```tsx
// BAD
expect(container).toMatchSnapshot(); // 200 lines of HTML
```

**Why it bites:** every refactor regenerates the snapshot. Reviewers
rubber-stamp the diff. The snapshot stops catching real regressions and
becomes review noise.

**Fix:** test behavior. Snapshot only stable, atomic, prop-driven
components (Badge, Avatar, Icon). For complex components, assert specific
behavior with `getByRole` + `toHaveTextContent`.

## 6. Leaking timers across tests

```ts
// BAD
beforeEach(() => vi.useFakeTimers());
// ...no afterEach restore
```

**Why it bites:** the next test file inherits fake timers. Real
`setTimeout` no longer fires. Tests hang or pass for the wrong reason.

**Fix:** always pair with `afterEach(() => vi.useRealTimers())` AND set
`restoreMocks: true` in config.

## 7. Closing over a top-level variable in vi.mock factory

```ts
// BAD
const mockFn = vi.fn();
vi.mock("@/lib/api", () => ({ createLead: mockFn })); // ReferenceError
```

**Why it bites:** `vi.mock` is hoisted to the top of the file BEFORE
imports and top-level declarations. `mockFn` is in the temporal dead
zone when the factory runs.

**Fix:** `vi.hoisted`.

```ts
// GOOD
const { mockFn } = vi.hoisted(() => ({ mockFn: vi.fn() }));
vi.mock("@/lib/api", () => ({ createLead: mockFn }));
```

## 8. Asserting on Tailwind classNames

```tsx
// BAD
expect(button).toHaveClass("bg-blue-500"); // CSS doesn't load in jsdom anyway
```

**Why it bites:** Tailwind is purged at build time and CSS doesn't load
in jsdom. The class string is just opaque text. Refactor `bg-blue-500` →
`bg-primary` and the test breaks without any behavior change.

**Fix:** test computed accessibility, not class names. `toHaveAttribute("aria-pressed", "true")`,
`toBeDisabled()`, `toHaveAccessibleName("Submit")`. Use Playwright/Storybook
visual regression for actual visual checks.

## 9. Test pollution from module-level state

```ts
// BAD
// src/lib/cache.ts
const cache = new Map<string, unknown>();
export function set(k: string, v: unknown) { cache.set(k, v); }
```

```ts
// test
import { set } from "@/lib/cache";
it("a", () => { set("k", 1); /* leaks to test b */ });
```

**Why it bites:** module-level state survives between tests within the
same file. Order matters. Flaky.

**Fix:** export a `reset()` function and call it in `beforeEach`, OR use
`vi.resetModules()` to force re-import per test, OR refactor to
dependency injection.

## 10. Missing Radix UI jsdom stubs

```tsx
// Radix Select crashes: TypeError: target.hasPointerCapture is not a function
```

**Why it bites:** jsdom doesn't implement pointer capture, scrollIntoView,
ResizeObserver, IntersectionObserver. Radix primitives use all four.

**Fix:** stub them in `setup.ts` (see `examples.md` §2). Without these
stubs, ~80% of shadcn/ui components are untestable in jsdom.

## 11. Asserting on console.error/warn instead of catching the cause

```ts
// BAD
const errSpy = vi.spyOn(console, "error");
render(<Component />);
expect(errSpy).toHaveBeenCalled(); // "test passes" but bug is real
```

**Why it bites:** silences React's actually-useful warnings (key prop,
hydration mismatch). Tests pass while production breaks.

**Fix:** spy to silence noise from intentional errors, but assert on the
actual user-visible failure mode (error toast, error boundary fallback,
disabled button).

## 12. Snapshotting volatile output

```ts
// BAD
expect({ id: crypto.randomUUID(), createdAt: new Date() }).toMatchSnapshot();
```

**Why it bites:** non-deterministic. Snapshot regenerates every run.

**Fix:** stub `Date.now`, `crypto.randomUUID`, `Math.random`. Use
`expect.objectContaining` + `expect.any(String)` for stable assertions.

```ts
// GOOD
expect(result).toEqual({
  id: expect.any(String),
  createdAt: expect.any(Date),
  name: "Antony",
});
```

## 13. Running real network requests in tests

```ts
// BAD
it("fetches real data", async () => {
  const res = await fetch("https://api.real.com/leads");
});
```

**Why it bites:** flaky (network), slow, leaks credentials, hits rate
limits. CI breaks when the API has an outage that has nothing to do with
your code.

**Fix:** MSW. Always. Reserve real network for Playwright e2e against a
staging environment.

## 14. Using `act()` manually around React Testing Library

```tsx
// BAD
import { act } from "react-dom/test-utils";
act(() => { render(<X />); });
```

**Why it bites:** RTL already wraps `render` in `act`. Wrapping again
either does nothing or hides the real warning.

**Fix:** trust RTL. If you see an `act` warning, the cause is usually a
missing `await` on `userEvent` or an unwrapped state update inside a
`useEffect`.

## 15. Importing from `@testing-library/jest-dom` instead of `/vitest`

```ts
// BAD (works but emits deprecation in jest-dom v6)
import "@testing-library/jest-dom";
```

**Fix:**
```ts
// GOOD
import "@testing-library/jest-dom/vitest";
```

The `/vitest` entry point registers matchers via Vitest's `expect.extend`,
not Jest's. Eliminates a deprecation warning and ensures matcher types
resolve.
