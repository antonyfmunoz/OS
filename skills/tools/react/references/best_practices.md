# React — Creator-Level Best Practices

Source: https://react.dev
API Version: React 18.3 (React 19 awareness noted)
SDK Version: react@18.3.1 / react-dom@18.3.1
Last Researched: 2026-04-06

React is not an app framework. It is a **rendering library with a
component model**. Understanding that distinction is the difference
between fighting React and flowing with it.

---

# Tier 1 — Technical Mastery

## Authentication

React has no authentication surface — it is a client-side library
distributed on npm as `react` and `react-dom`. The analogue of "auth"
for a library is **version identity and integrity**:

1. **Pin exact versions.** `"react": "18.3.1"` not `"^18.3.1"`.
   Minor drifts between `react` and `react-dom` cause "Invalid hook
   call" errors that look like bugs in user code.
2. **Single copy of React.** Duplicated copies (from bad hoisting,
   symlinked monorepos, or peer-dep mismatches) break hooks because
   each copy has its own hook dispatcher closure. Diagnose with
   `npm ls react`.
3. **DevTools** — React DevTools is the runtime inspector. Public,
   free, install from the browser extension store. No accounts.
4. **react.dev** account is not required to read docs.

For anything server-rendered (Next.js, Remix), auth happens at the
framework layer — React itself is unaware of users.

## Core Operations with Exact Signatures

### Creating and rendering a tree

```ts
import { createRoot } from "react-dom/client";
const root = createRoot(document.getElementById("root")!);
root.render(<App />);
// later
root.unmount();
```

`createRoot` is the React 18 replacement for `ReactDOM.render`.
It enables concurrent features. Using the legacy API opts you out.

### Hook API (React 18.3)

| Hook | Signature | Purpose |
|------|-----------|---------|
| `useState<T>` | `(initial: T \| (() => T)) => [T, (v: T \| ((p: T) => T)) => void]` | Local state. |
| `useReducer<S,A>` | `(reducer: (s:S,a:A)=>S, init: S, initFn?) => [S, (a:A)=>void]` | State machine. |
| `useEffect` | `(fn: () => void \| (() => void), deps?: any[]) => void` | Sync with external systems. |
| `useLayoutEffect` | same signature | Fires synchronously after DOM mutation, before paint. |
| `useMemo<T>` | `(fn: () => T, deps: any[]) => T` | Memoize expensive computation. |
| `useCallback<F>` | `(fn: F, deps: any[]) => F` | Memoize function identity. |
| `useRef<T>` | `(initial: T) => { current: T }` | Mutable value that doesn't trigger re-renders. |
| `useContext<T>` | `(ctx: Context<T>) => T` | Read nearest provider value. |
| `useTransition` | `() => [boolean, (fn: () => void) => void]` | Mark updates as non-urgent. |
| `useDeferredValue<T>` | `(v: T) => T` | Return a delayed copy of a value for expensive subtrees. |
| `useId` | `() => string` | Stable SSR-safe unique id for a11y. |
| `useSyncExternalStore<T>` | `(subscribe, getSnapshot, getServerSnapshot?) => T` | Subscribe to external store (Redux, Zustand). |
| `useImperativeHandle<T>` | `(ref, () => T, deps) => void` | Customize what parent refs see. |

### Rules of Hooks (enforced by `eslint-plugin-react-hooks`)

1. Only call hooks at the top level of a function component or custom hook.
2. Never call hooks inside conditionals, loops, or nested functions.
3. Custom hooks must start with `use`.

These rules exist because React identifies hooks by **call order**.
Breaking order corrupts the hook state list.

## Pagination Patterns

React itself doesn't paginate — but the rendering analogue is
**windowing / virtualization**. For lists over ~100 items use
`react-window` or `@tanstack/react-virtual`. Only the visible rows are
rendered, not the whole list. Pagination of server data is handled by
React Query (`useInfiniteQuery`):

```ts
const q = useInfiniteQuery({
  queryKey: ["leads"],
  queryFn: ({ pageParam = 0 }) => fetchLeads(pageParam),
  getNextPageParam: (last) => last.nextCursor,
  initialPageParam: 0,
});
```

## Rate Limits

React has no network rate limit. The relevant constraint is the
**render budget** — the browser gives you ~16ms per frame at 60fps.
React 18 concurrent rendering lets you exceed that budget for
non-urgent updates without blocking input:

- `startTransition(() => setX(...))` — marks an update as
  interruptible. If a higher-priority update (typing) arrives, React
  discards the partial transition render.
- `useDeferredValue(x)` — returns `x` that lags behind by one render,
  which lets expensive subtrees render in a lower priority.
- **Automatic batching** — React 18 batches state updates across
  promises, timeouts, and native event handlers. In React 17 only
  synchronous event handlers were batched.

Hard practical limits:
- A single component that renders >10,000 DOM nodes will stutter. Virtualize.
- `useEffect` running on every render with a state update creates an
  infinite loop — enforced by React with a warning.
- `setState` inside render body throws ("Cannot update during an
  existing state transition").

## Error Codes and Recovery

React has a small set of runtime errors. The most common:

| Error | Cause | Fix |
|-------|-------|-----|
| `Invalid hook call` | Multiple copies of React, or hook called outside a component | `npm ls react`, move call to top level |
| `Rendered more/fewer hooks than previous render` | Hook called conditionally | Remove the conditional |
| `Cannot update a component while rendering a different component` | `setState` during render of another component | Move to `useEffect` or event handler |
| `Maximum update depth exceeded` | `setState` in render or effect without guard | Add dependency or condition |
| `Each child in a list should have a unique "key" prop` | Missing `key` in mapped array | Add stable id key |
| `Can't perform a React state update on an unmounted component` | Async resolved after unmount (pre-18) | Use AbortController or React Query |
| `Hydration failed` (SSR) | Server HTML ≠ client first render | Remove non-deterministic render (Date.now, Math.random), use `useId` |

Recovery pattern — **Error Boundaries**:

```tsx
class ErrorBoundary extends React.Component<
  { fallback: ReactNode; children: ReactNode },
  { error: Error | null }
> {
  state = { error: null };
  static getDerivedStateFromError(error: Error) { return { error }; }
  componentDidCatch(err: Error, info: React.ErrorInfo) {
    console.error(err, info);
  }
  render() {
    return this.state.error ? this.props.fallback : this.props.children;
  }
}
```

Error boundaries must still be class components in React 18. Wrap
route components and risky subtrees. They don't catch errors in event
handlers, async code, or the boundary itself.

## SDK Idioms

- **Function components only.** Classes are legacy (needed only for
  error boundaries). No `this`, no lifecycle methods.
- **Functional `setState`** when next state depends on previous:
  `setCount(c => c + 1)`. Never `setCount(count + 1)` inside closures.
- **Lift state up, then push state down.** State lives at the lowest
  common ancestor of components that need it.
- **Composition over inheritance.** Always. React has no component
  inheritance model by design.
- **Children as a slot.** `children: ReactNode` is the simplest
  composition primitive — prefer it over render props when possible.
- **Custom hooks for logic reuse.** Any time two components share
  stateful logic, extract a `useX` hook.
- **Keys on Fragment** when mapping: `<React.Fragment key={id}>` or
  the shorthand `<>` without key if no list.
- **`as const` for discriminated unions** in reducer actions for
  exhaustive type checking.
- **Controlled forms** — value + onChange. Uncontrolled only when
  perf matters (RHF uses uncontrolled by default).

## Anti-Patterns

See `references/anti_patterns.md` for the full list. Highlights:

- **Fetching in `useEffect`.** Use React Query.
- **Deriving state with `useEffect` + `setState`.** Compute during render.
- **Copying props into state.** Breaks the update flow.
- **Index as key.** Breaks list reorders.
- **Overusing `useMemo` / `useCallback`.** Memoization has a cost;
  most components don't need it.
- **Context for everything.** Context re-renders all consumers on any
  change. Use it for truly tree-wide values (theme, user) and pair
  with a selector lib (`use-context-selector`) or external store for
  frequently-changing data.
- **Huge components.** Split by responsibility, not by file size.
- **Disabling `react-hooks/exhaustive-deps`.** The warning is almost
  always right. If you need to ignore a dep, use `useRef`.

## Data Model

React's data model is the **Fiber tree** — an internal linked list of
"fibers," each representing a component instance, a DOM element, or a
Fragment. Every render produces a new work-in-progress fiber tree;
reconciliation diffs it against the current tree and generates an
effect list for commit.

Key invariants:
- Each fiber has an `alternate` pointer to its work-in-progress copy.
- Hook state is stored on the fiber as a linked list — `useState` is
  literally "grab the next slot."
- `key` and `type` determine fiber identity. Change either → unmount
  old subtree, mount new one (state resets).
- Context is looked up by walking up the fiber tree at read time.
- Refs are assigned during commit, not render.

## Webhooks and Events

React has no webhooks, but its **synthetic event system** is the
analogue. React attaches a single delegated listener at the root and
dispatches synthesized events (`SyntheticEvent`) through the component
tree. Key differences from DOM events:

- `onClick` etc. use camelCase.
- `preventDefault()` must be explicit — no `return false`.
- Events are **pooled** in React <17; in React 18+ they're not.
- `e.currentTarget` vs `e.target` — same rules as DOM.
- Passive event listeners for `onTouchStart`/`onWheel` must be
  attached via `useEffect` with `{ passive: false }` if you need
  `preventDefault`.

For cross-component event flow, the real-time analogue is
**Suspense boundaries** and `useSyncExternalStore` for subscribing to
external event sources.

## Limits

- **DOM node count** — practical cap ~5-10k visible nodes before
  paint/layout stutters. Virtualize above this.
- **Component tree depth** — no hard limit, but deep trees slow
  reconciliation. Flat trees render faster.
- **Hook count per component** — no hard limit, but >15 is a smell —
  extract custom hooks.
- **Context providers** — unlimited, but every consumer re-renders on
  any value change. Split providers by update frequency.
- **Bundle size of `react` + `react-dom`** — ~45KB gzipped. Real app
  size comes from your code and libraries.
- **React 18 concurrent rendering** runs cooperative scheduling with
  5ms time slices.

## Cost Model

React is MIT-licensed and free. The cost model to reason about is
**bundle size and render cost**:

1. **Bundle size** — every dependency adds KB. Use `rollup-plugin-visualizer`
   or `vite-bundle-visualizer` to audit. Tree-shake unused exports. Prefer
   named imports.
2. **Render cost** — every state change re-renders the component and
   its children. Profile with React DevTools Profiler. Memoize only
   the hot paths.
3. **Mount cost** — dominated by DOM creation and initial layout.
   Virtualize long lists.
4. **Hydration cost (SSR)** — React must attach listeners to every
   node. Selective hydration (React 18) lets Suspense boundaries
   hydrate independently.

"Make it work, make it right, make it fast" — in that order.
Premature memoization is the number-one waste of React dev time.

## Version Pinning

- **React 18.3** is the current stable branch as of 2026-04.
- **React 19** is released and stable but adoption is gradual.
  Key React 19 additions to know: Actions, `useActionState`,
  `useOptimistic`, `use()` hook for reading promises/context,
  ref as a prop (no more `forwardRef`), `<form action>` integration.
- **Server Components** ship via Next.js App Router and future Remix.
  Not applicable to Vite-based SPAs (EOS SaaS) yet.
- Pin `react` and `react-dom` to the **exact same version**.
- Pin `@types/react` and `@types/react-dom` to matching majors.
- React follows **semver** — patch releases are safe; major releases
  have migration guides. Follow `react@18 → 19` migration guide when
  upgrading.

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

React was created at Facebook by Jordan Walke in 2011, open-sourced
in 2013. The founding insight: **the DOM is imperative, but UI is
declarative**. Every UI framework before React (Backbone, Angular 1,
Knockout) asked the developer to write code that *mutates* the DOM in
response to state changes. React inverted it: you describe what the
UI should look like for the current state, and the library handles
the mutations.

Deliberate tradeoffs:
- **JSX over templates.** JSX is JavaScript. Loops, conditionals, and
  composition are just language features, not template directives.
  This is why React has no `v-if`/`ng-for` — it doesn't need them.
- **Virtual DOM over direct DOM.** An extra diff step costs CPU but
  makes the programming model pure-functional.
- **One-way data flow.** Props go down, events go up. No two-way
  binding. More boilerplate, fewer bugs.
- **Component as function.** Once hooks landed (2018), components
  became literally `(props) => JSX`. This made React a functional
  programming library for UI.
- **Reconciliation by type + key, not by path.** Enables efficient
  list updates and sibling reordering.
- **Hooks over HOCs and render props.** Hooks compose linearly;
  HOCs and render props nested. Hooks won.

The cost of this model: understanding it. React punishes developers
who think imperatively. Its biggest bugs (stale closures, effect
loops, derived-state-in-useState) all come from leaking imperative
thinking into a declarative model.

## Problem-Solution Map and Hidden Capabilities

| Problem | React's answer |
|---------|----------------|
| Keeping UI in sync with state | `UI = f(state)` via render |
| Avoiding full DOM rewrites | Virtual DOM + reconciliation |
| Sharing logic between components | Custom hooks |
| Deep prop drilling | Context |
| Expensive recomputation | `useMemo`, `useDeferredValue` |
| Blocking input on heavy renders | `startTransition`, concurrent rendering |
| Loading states during navigation | Suspense + `useTransition` |
| Integrating external stores | `useSyncExternalStore` |
| Focus / measurement after DOM mutation | `useLayoutEffect`, refs |
| Resetting component state on identity change | `key` prop |
| Portaling to outside the tree | `createPortal` |
| SSR unique IDs | `useId` |
| Imperative child APIs | `useImperativeHandle` + `forwardRef` |

Hidden capabilities most devs miss:
- **`key` as a state reset mechanism** — change `key` on a component
  to remount and discard all its state. Cleaner than `useEffect(() => reset(), [id])`.
- **`useReducer` returns stable dispatch.** Unlike `setState`, dispatch
  identity never changes, so you don't need to memoize it in deps.
- **`useSyncExternalStore`** — the official hook for any external
  store. Handles tearing during concurrent renders.
- **Server-only code via Server Components** (framework-mediated) —
  runs on the server, never ships to the client, can talk to the DB
  directly.
- **`flushSync`** — force a synchronous DOM update when you need to
  measure immediately after a state change (rare).

## Operational Behavior and Edge Cases

- **Strict Mode** in development double-invokes component bodies,
  `useState` initializers, `useMemo`/`useReducer` functions, and runs
  effects mount→unmount→mount. Production runs once. This catches
  impure renders and missing cleanups.
- **Automatic batching (React 18)** — state updates inside promises,
  setTimeout, native handlers are batched into one re-render. Opt out
  with `flushSync`.
- **Concurrent rendering** — React can abandon a render if higher
  priority work arrives. Your render function **must be pure**
  because it may run multiple times per commit.
- **Fast Refresh** (Vite HMR) preserves hook state across edits but
  resets on structural changes. If state vanishes on save, check that
  the component is the default export or named properly.
- **Events and refs** fire in this order on update:
  render → DOM mutation → `useLayoutEffect` → browser paint → `useEffect`.
- **Tearing** — concurrent renders can see different values of an
  external store at different times. `useSyncExternalStore` prevents this.

## Ecosystem Position and Composition

React sits at the **rendering layer**. Everything above and beside it
is ecosystem:

- **Bundlers** — Vite (EOS), Webpack, Turbopack, Parcel.
- **Meta-frameworks** — Next.js, Remix, TanStack Start, Astro.
- **State** — Zustand, Jotai, Redux Toolkit, Recoil, Valtio.
- **Server state** — TanStack Query (EOS), SWR, Apollo.
- **Forms** — React Hook Form (EOS), Formik, TanStack Form.
- **Validation** — Zod (EOS), Yup, Valibot, Joi.
- **Styling** — Tailwind (EOS), CSS Modules, Emotion, Styled Components, vanilla-extract.
- **UI primitives** — Radix (under shadcn), Headless UI, Ariakit, React Aria.
- **Component libraries** — shadcn/ui (EOS), Mantine, MUI, Chakra.
- **Routing** — React Router, TanStack Router, Wouter, Next Router.
- **Animation** — Framer Motion, React Spring, Motion One.
- **Testing** — Vitest/Jest + React Testing Library + Playwright.

Composition rule for EOS: **prefer single-purpose libraries that do
one thing well** over mega-frameworks. Vite + React Query + RHF + Zod
composes to replace 80% of what Next.js gives you, with more control
and faster builds.

## Trajectory and Evolution

- **React 16 (2017)** — Fiber reconciler rewrite, error boundaries, portals, fragments.
- **React 16.8 (2019)** — Hooks. The biggest shift since component classes.
- **React 17 (2020)** — no new features; delegated root setup, enabling gradual upgrades.
- **React 18 (2022)** — concurrent rendering, Suspense for data, `useTransition`, automatic batching, Strict Mode effects double-run.
- **React 19 (2024-2025)** — Actions, `useActionState`, `useOptimistic`, `use()` hook, ref as prop, `<form action>`, React Compiler (Babel plugin that auto-memoizes).
- **React Compiler** — the biggest trajectory shift. Manual `useMemo`/`useCallback` become unnecessary for most code; the compiler inserts memoization automatically. Currently experimental; stable adoption likely 2026.
- **Server Components** — React's attempt to unify server rendering with the component model. Available in Next.js App Router; expanding to Remix/TanStack Start. Not relevant for Vite SPAs yet.
- **Suspense expansion** — more integrations for data fetching frameworks.

Direction: make React "just work" without developers needing to
hand-optimize. The Compiler is the clearest expression of this —
"write idiomatic React, let the tool make it fast."

## Conceptual Model and Solution Recipes

**The unifying model: React is a memoized pure function from state
to a description of UI.** Every problem becomes: "what is my state,
and what function maps it to JSX?"

Recipes:
- **"My component re-renders too much"** — 1) profile first, 2) split
  children into siblings with `children` prop, 3) memoize expensive
  children, 4) use `useDeferredValue` for heavy subtrees, 5) move
  state down.
- **"My effect runs in a loop"** — check deps. An object/array/function
  in deps is always new. Memoize it or lift it out.
- **"My input is laggy when typing"** — the expensive work is blocking
  paint. Wrap the expensive state update in `startTransition`.
- **"My modal keeps its state after closing"** — the component isn't
  unmounting. Use `key` to force reset, or unmount conditionally.
- **"Fetched data flashes old value"** — your query is keyed on stale
  state. React Query key should include the dynamic parameters.
- **"Form loses focus on every keystroke"** — you're defining the form
  component inside another component's render. Move it outside.
- **"Two effects race each other"** — consolidate them, or use a
  single effect with AbortController. Better: move to React Query.

## Industry Expert and Cutting-Edge Usage

Frontier patterns the top 5% are using:

- **Compound components.** Expose a parent component with attached
  children: `<Tabs><Tabs.List/><Tabs.Panel/></Tabs>`. Radix and
  shadcn are built on this. Cleaner than props-as-config.
- **Headless components.** Logic in hooks, markup in consumers.
  Radix, Headless UI, React Aria. Enables infinite UI variation
  without forking the logic.
- **State machines with XState** for complex UI flows (checkout,
  multi-step forms, onboarding). Eliminates impossible states.
- **Server-driven UI** — shape of UI comes from backend JSON, React
  just renders it. Used by Airbnb, Shopify.
- **Islands architecture** (Astro) — ship React only where needed,
  static HTML for the rest. Dramatic bundle size wins.
- **Render-as-you-fetch with Suspense.** Kick off data requests at
  navigation time, render as they resolve. TanStack Router and
  Next App Router enable this.
- **Selective hydration.** React 18 SSR hydrates Suspense boundaries
  independently in priority order.
- **Partial Pre-rendering** (Next.js) — static shell + streamed dynamic regions.
- **React Compiler for zero-memo code.** Write naive React, let the
  compiler insert memoization.
- **TkDodo's React Query patterns** — query keys as hierarchies,
  invalidate-by-prefix, optimistic updates with rollback.
- **Dan Abramov's "You might not need an effect"** — the canonical
  post on when NOT to use useEffect. Required reading.

Experts writing React in 2026:
- **Dan Abramov** (overreacted.io) — mental models.
- **TkDodo** (tkdodo.eu) — React Query and idiomatic patterns.
- **Kent C. Dodds** — testing, composition, common mistakes.
- **Ryan Florence / Michael Jackson** — React Router, Remix, data loading.
- **shadcn** — headless composition via Radix + Tailwind.
- **Rick Hanlon, Andrew Clark, Sebastian Markbåge** — React core team.

---

## EOS Usage Patterns

- All new components are function components with TypeScript.
- All data fetching goes through React Query. No `useEffect` fetch.
- All forms use React Hook Form + Zod + shadcn `<Form>` wrapper.
- UI primitives come from `components/ui/` (shadcn). Never install
  a second component library alongside shadcn.
- Strict Mode is enabled in every app. Keep it.
- Custom hooks in `hooks/` prefixed `use-` (kebab-case filename,
  camelCase export).
- Named exports preferred for components; default exports only for
  route/page components when the router requires it.
- Any async operation that touches the server uses React Query's
  `useMutation` with `onSuccess` invalidation — never a raw fetch.

## Gotchas

- Strict Mode double-runs effects in dev — always return a cleanup.
- `useEffect` with a fetch causes races; use React Query.
- Object/array literals as deps create infinite loops — memoize.
- `react` and `react-dom` version mismatch → Invalid hook call.
- Array index as `key` breaks reorders.
- `useState(props.x)` doesn't update when prop changes.
- Memoizing everything is slower than memoizing nothing.
- Context causes all consumers to re-render on any value change.
- `useLayoutEffect` warns during SSR — use isomorphic variant.
- `startTransition` doesn't defer the input itself, only the update.
- Fast Refresh resets state if the component isn't a proper export.
- `forwardRef` required in React 18 for ref forwarding (React 19 lets
  ref be a normal prop — don't mix the two styles in the same file).
