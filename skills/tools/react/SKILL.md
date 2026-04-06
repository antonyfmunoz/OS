---
name: react
description: "Use when creating, modifying, or debugging React components, hooks, or rendering behavior in the EOS SaaS codebase (/opt/OS/saas) — building UI with React 18 + TypeScript, wiring state with hooks, integrating React Query for server state, composing shadcn/ui primitives, handling forms with React Hook Form + Zod, diagnosing re-render loops, stale closures, Strict Mode double-invocation, Suspense boundaries, or concurrent rendering issues. Also use when deciding between client state and server state, writing custom hooks, or planning a migration path toward React 19 / Server Components."
allowed-tools: "Read, Write, Edit, Bash, WebFetch, WebSearch"
version: 1.0
source_url: "https://react.dev"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "18.3"
sdk_version: "react@18.3"
speed_category: "fast"
trigger: both
effort: high
context: fork
---

# Tool: React

React is the UI primitive for every EOS SaaS surface. The Initiate Arena
admin, the CreatorOS dashboards, Empyrean Studio client portals — all
React 18 + TypeScript on Vite, styled with Tailwind, composed from
shadcn/ui, with React Query for server state and Zod-validated forms.

This skill exists so agents working in `/opt/OS/saas` write React the way
the React team intended — declarative, top-down, with hooks as the
composition primitive and rendering treated as a pure function of state.

## What This Tool Does

React is a JavaScript library for building user interfaces by describing
UI as a pure function of state. You write components; React computes a
virtual tree, diffs it against the last tree, and commits the minimal
set of DOM mutations. The mental model is:

    UI = f(state)

Everything else — hooks, Suspense, concurrent rendering, Server
Components — is machinery that preserves this model as apps grow.

Core capabilities:
- **Components** — reusable, composable units. Function components only in new code.
- **Hooks** — `useState`, `useReducer`, `useEffect`, `useMemo`, `useCallback`,
  `useRef`, `useContext`, `useTransition`, `useDeferredValue`, `useId`,
  `useSyncExternalStore`, `useLayoutEffect`, `useImperativeHandle`.
- **Concurrent rendering (React 18)** — interruptible renders,
  automatic batching, `startTransition`, Suspense for data fetching.
- **Strict Mode** — development-time double-invocation of renders,
  effects, and state initializers to surface impurity.
- **Reconciliation** — keyed diffing of virtual DOM trees.
- **Portals, Refs, Context** — escape hatches for DOM, imperative handles, and tree-wide values.

## EOS Integration

**Where React lives:**
- `/opt/OS/saas/` — every SaaS product. Vite + React 18 + TS strict.
- `/opt/OS/saas/*/src/components/ui/` — shadcn/ui primitives (Radix + Tailwind).
- `/opt/OS/saas/*/src/components/` — feature components.
- `/opt/OS/saas/*/src/hooks/` — custom hooks (`use-toast`, `use-mobile`, etc.).
- `/opt/OS/saas/*/src/pages/` — route components.

**Stack partners (see references/integrations.md):**
- **Vite** — bundler, dev server, HMR via `@vitejs/plugin-react`.
- **TypeScript strict** — every component and hook typed; no `any`.
- **Tailwind + shadcn/ui** — styling and primitive library. Compose, don't copy.
- **@tanstack/react-query** — ALL server state. Never `useEffect` to fetch.
- **Zod + React Hook Form** — all forms use `zodResolver`. Single source of truth for shape + validation.
- **Wouter or React Router** — client routing (see repo for which).

**The rule:** client state → hooks (`useState`/`useReducer`). Server state → React Query. Form state → RHF + Zod. URL state → router. Derived state → compute during render. Never conflate these.

## Authentication

React is a library, not a service — **no API keys, no auth, no accounts**.
The only "auth-like" concerns for the Developer Agent are:

- **React DevTools** (browser extension) — inspect component tree,
  profile renders, view hook state. Install in Chrome/Firefox when
  debugging. No login required.
- **react.dev** — official docs and reference. Public.
- **npm registry** — `react` and `react-dom` are public packages.
  Pin exact versions in `package.json` to avoid silent minor drift.

What replaces auth for a library: **version pinning**.
Always pin `react` and `react-dom` to the **same exact version**.
A mismatch between `react@18.3.1` and `react-dom@18.2.0` causes
silent runtime errors like "Invalid hook call" that look like bugs
in your code.

    "react": "18.3.1",
    "react-dom": "18.3.1",

## Quick Reference

### Function component with typed props

```tsx
import { type ReactNode } from "react";

interface CardProps {
  title: string;
  children: ReactNode;
  onDismiss?: () => void;
}

export function Card({ title, children, onDismiss }: CardProps) {
  return (
    <div className="rounded-xl border p-4">
      <header className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">{title}</h3>
        {onDismiss && (
          <button onClick={onDismiss} aria-label="Dismiss">×</button>
        )}
      </header>
      {children}
    </div>
  );
}
```

### State + derived values (no useEffect)

```tsx
function LeadList({ leads }: { leads: Lead[] }) {
  const [query, setQuery] = useState("");
  // Derived — compute during render. NOT useEffect + setState.
  const filtered = leads.filter((l) =>
    l.name.toLowerCase().includes(query.toLowerCase())
  );
  return (
    <>
      <input value={query} onChange={(e) => setQuery(e.target.value)} />
      <ul>{filtered.map((l) => <li key={l.id}>{l.name}</li>)}</ul>
    </>
  );
}
```

### Server state with React Query

```tsx
import { useQuery } from "@tanstack/react-query";

function useLeads() {
  return useQuery({
    queryKey: ["leads"],
    queryFn: async () => {
      const res = await fetch("/api/leads");
      if (!res.ok) throw new Error("Failed to load leads");
      return (await res.json()) as Lead[];
    },
    staleTime: 30_000,
  });
}
```

### Form with React Hook Form + Zod

```tsx
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

const schema = z.object({
  email: z.string().email(),
  name: z.string().min(1),
});
type FormValues = z.infer<typeof schema>;

function SignupForm() {
  const { register, handleSubmit, formState: { errors } } =
    useForm<FormValues>({ resolver: zodResolver(schema) });
  return (
    <form onSubmit={handleSubmit((v) => console.log(v))}>
      <input {...register("email")} />
      {errors.email && <p>{errors.email.message}</p>}
      <input {...register("name")} />
      <button type="submit">Sign up</button>
    </form>
  );
}
```

### Effect for SUBSCRIPTIONS only (not for fetching)

```tsx
useEffect(() => {
  const sub = eventBus.subscribe("lead.created", handler);
  return () => sub.unsubscribe();   // cleanup on unmount OR dep change
}, [handler]);
```

## Conceptual Model

Think of a React app as a **pure function that produces a tree**.

1. **State changes trigger re-renders.** A re-render is React calling
   your component function again with the new state. It is NOT a DOM
   update. DOM updates happen only in the commit phase, after diffing.

2. **Rendering must be pure.** No side effects, no mutation, no I/O.
   Same props + same state → same JSX. If you need impurity, that's
   what event handlers and `useEffect` are for.

3. **Effects are for synchronizing with external systems.** NOT for
   deriving state from props. If you catch yourself writing
   `useEffect(() => setX(f(y)), [y])`, delete it and compute `x` during
   render instead.

4. **Strict Mode double-invokes on purpose.** In development, React
   calls your component twice and runs effects twice (mount → unmount → mount)
   to surface bugs that would only appear with concurrent features or
   Fast Refresh. If your code breaks under Strict Mode, it is buggy.

5. **Keys are identity, not order.** A `key` tells React "this element
   is the same logical thing as last render." Using array index as key
   causes bugs when the list reorders. Use stable IDs.

6. **Hooks are called in a fixed order.** Never inside conditionals,
   loops, or early returns. This is why the linter is non-negotiable.

7. **The three kinds of state:**
   - **Client state** — `useState`/`useReducer`. UI-only.
   - **Server state** — React Query. Caches, refetches, invalidation.
   - **Derived state** — neither. Compute during render from existing state.

## Gotchas

- **Strict Mode double-invocation.** In dev, every effect runs
  mount → cleanup → mount. If your effect doesn't clean up, you get
  duplicate subscriptions, duplicate network requests, duplicate timers.
  This is a feature — it catches real bugs. Fix the cleanup, don't
  disable Strict Mode.

- **`useEffect` to fetch data is almost always wrong.** It causes
  waterfalls, race conditions, no caching, no dedup, no retry, no
  invalidation. Use React Query. The ONLY legitimate `useEffect` uses
  are: synchronizing with non-React systems (DOM APIs, subscriptions,
  timers, third-party libraries).

- **Stale closure bug.** Handlers captured in `useEffect`/`useCallback`
  see the state from when the effect ran, not current state. Fix with
  either: include the value in deps, use `useRef` for latest value,
  or use the functional form `setX(prev => ...)`.

- **Array index as `key` breaks reorders.** React reuses DOM for the
  same key. If the list reorders and the key is the index, React
  attaches old state to new items. Use a stable `id`.

- **Derived state in `useState`.** Do NOT copy a prop into state with
  `useState(props.x)` — it won't update when the prop changes. Either
  compute during render, use `key` to reset the component, or use a
  reducer.

- **Object/array literals as deps or props cause infinite renders.**
  `{}` and `[]` are new references every render. Memoize with `useMemo`
  or lift them out of the component.

- **`react` and `react-dom` version mismatch → "Invalid hook call".**
  Pin both to the same exact version. Check `npm ls react react-dom`.

- **`useLayoutEffect` on the server warns.** If you SSR, use
  `useEffect` or isomorphic layout effect.

- **`key` on a component resets its state.** Sometimes that's what you
  want (resetting a form when the selected user changes). Use this
  deliberately — it's a documented escape hatch.

- **`startTransition` does not defer the input.** The state update is
  deferred; the input remains synchronous. Don't wrap an event handler
  entirely in `startTransition`.

## References

- `references/best_practices.md` — full 19-section creator-level protocol.
- `references/examples.md` — EOS-aligned realistic code patterns.
- `references/anti_patterns.md` — real failure modes and fixes.
- `references/integrations.md` — Vite / TS / Tailwind / shadcn / RQ / Zod / RHF stack composition.

## Source

- https://react.dev (authoritative, Meta-maintained)
- https://react.dev/reference/react (hooks API)
- https://react.dev/learn (conceptual)
- https://tkdodo.eu/blog (React Query patterns)
- https://overreacted.io (Dan Abramov — mental model posts)
