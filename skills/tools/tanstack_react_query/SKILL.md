---
name: tanstack_react_query
description: "Use when fetching, caching, mutating, or invalidating server state in EOS SaaS — covers useQuery/useMutation, query key design, cache invalidation, optimistic updates, loading/error states, and form submission flows. Also triggers when debugging stale data, refetch loops, request waterfalls, over-fetching, useEffect-to-fetch anti-patterns, or when planning Suspense/ErrorBoundary-driven page architecture."
allowed-tools: "Read, Write, Edit, Bash, WebFetch, WebSearch"
version: 1.0
trigger: both
effort: high
context: fork
last_researched: "2026-04-06"
api_version: "5.x"
sdk_version: "@tanstack/react-query@5"
speed_category: "medium"
source_url: "https://tanstack.com/query/latest"
sources:
  - "https://tanstack.com/query/latest/docs/framework/react/overview"
  - "https://tanstack.com/query/latest/docs/framework/react/guides/query-keys"
  - "https://tanstack.com/query/latest/docs/framework/react/guides/mutations"
  - "https://tanstack.com/query/latest/docs/framework/react/guides/invalidations-from-mutations"
  - "https://tanstack.com/query/latest/docs/framework/react/guides/optimistic-updates"
  - "https://tanstack.com/query/v5/docs/framework/react/guides/migrating-to-v5"
  - "https://tanstack.com/query/latest/docs/framework/react/guides/suspense"
  - "https://tanstack.com/query/latest/docs/react/comparison"
  - "https://tkdodo.eu/blog/practical-react-query"
  - "https://tkdodo.eu/blog/effective-react-query-keys"
  - "https://tkdodo.eu/blog/react-query-as-a-state-manager"
  - "https://tkdodo.eu/blog/status-checks-in-react-query"
  - "https://tkdodo.eu/blog/react-query-error-handling"
  - "https://tkdodo.eu/blog/react-query-and-type-script"
  - "https://tkdodo.eu/blog/placeholder-and-initial-data-in-react-query"
  - "https://tkdodo.eu/blog/the-query-options-api"
---

# Tool: TanStack Query (React adapter) — @tanstack/react-query v5

TanStack Query is the **server-state layer** for every page in `/opt/OS/saas`.
Anywhere a component reads data the backend owns — leads, organizations,
campaigns, billing, messages, analytics — it goes through React Query.
Anywhere a component writes data the backend owns, it goes through a
`useMutation` that invalidates the relevant query key on success.

This skill is what keeps the EOS SaaS codebase from sliding back into
`useEffect(() => fetch(...))` chaos: no manual loading flags, no
hand-rolled caches, no request waterfalls, no stale data on re-mount.

## What This Tool Does

TanStack Query is a **framework-agnostic async state manager**. The React
adapter (`@tanstack/react-query`) binds it to React via hooks. Its job is
to turn any async function (usually a `fetch` call, but any Promise works)
into cached, deduplicated, background-refetching, invalidation-aware
state — with zero boilerplate and no Redux.

Core primitives:
- **`QueryClient`** — the cache. One per app. Holds every query's data,
  status, error, and metadata, keyed by a deterministically-hashed
  `queryKey` array.
- **`QueryClientProvider`** — React context that makes the client
  available to hooks.
- **`useQuery({ queryKey, queryFn, ...opts })`** — reads (and dedupes,
  caches, and background-refetches) a Promise. Returns `{ data, error,
  status, isPending, isFetching, isError, isSuccess, refetch, ... }`.
- **`useMutation({ mutationFn, onMutate, onSuccess, onError, onSettled })`**
  — writes. Returns `{ mutate, mutateAsync, isPending, isError, error,
  data, variables, reset }`.
- **`useInfiniteQuery`** — cursor/page-based pagination with
  `fetchNextPage`, `hasNextPage`.
- **`useSuspenseQuery`** / **`useSuspenseInfiniteQuery`** — v5 hooks that
  suspend instead of returning `isPending`. `data` is guaranteed defined.
  Pairs with `<Suspense>` + `<ErrorBoundary>`.
- **`useQueries`** — parallel queries in one hook, dynamic count.
- **`useQueryClient()`** — imperative access to the cache for
  `invalidateQueries`, `setQueryData`, `prefetchQuery`, `cancelQueries`.
- **`queryOptions()`** — v5 type-safe helper that colocates `queryKey` +
  `queryFn` + options so the same definition works in `useQuery`,
  `prefetchQuery`, and `setQueryData` with full inference.

## EOS Integration

**Where React Query lives:**
- `/opt/OS/saas/*/src/lib/query-client.ts` — the shared `QueryClient`
  with EOS defaults.
- `/opt/OS/saas/*/src/main.tsx` — wraps `<App />` in
  `<QueryClientProvider>` + `<ReactQueryDevtools />` (dev only).
- `/opt/OS/saas/*/src/features/{feature}/queries.ts` — colocated query
  key factory + `queryOptions` + custom hooks per feature. Only hooks
  are exported.
- `/opt/OS/saas/*/src/features/{feature}/mutations.ts` — mutation hooks.

**Stack partners:**
- **React 18 (→ 19)** — the whole saas is RQ-driven. React 19's
  `useActionState` does not replace RQ; see integrations.md for the
  bridge pattern.
- **TypeScript strict** — every `queryFn` has an explicit return type.
  No `any`. Infer generics from the function.
- **Zod** — every `queryFn` validates the response with
  `Schema.parse(await res.json())`. RQ caches the parsed, typed value.
- **React Hook Form + shadcn** — forms submit via `useMutation`.
  `onSuccess` → `qc.setQueryData` + `form.reset(saved)`. `onError` →
  `form.setError(...)` with the 400 body (see react_hook_form skill).
- **Wouter / React Router** — RQ is the "loader". No route loaders
  needed when `prefetchQuery` + `useQuery` composes naturally.
- **Express + Drizzle backend** — returns JSON, sets proper 4xx/5xx
  statuses, serializes Zod errors in `{ errors: { field: [...] } }`
  shape the frontend's `onError` can read.

**The rule:** server state → RQ. Client state → `useState`/`useReducer`.
Form state → RHF. URL state → router. Derived state → compute during
render. Never store server data in `useState`. Never `useEffect` to fetch.

## Authentication

React Query is a library — **no API keys**. The auth-like concerns are:

- **`QueryClient` singleton** — create ONE per app. Never per-component.
  Per-component clients fragment the cache and defeat deduplication.
- **Version pinning** — `@tanstack/react-query@5.x`. Pin exact minor if
  you depend on specific v5 hooks. Check with
  `npm ls @tanstack/react-query`.
- **Devtools package** — `@tanstack/react-query-devtools` is a separate
  install. Only mount in dev: `{import.meta.env.DEV && <ReactQueryDevtools />}`.
- **Request auth** — lives inside your `queryFn` (attach JWT header,
  send cookies). RQ is agnostic to the transport.

## Quick Reference

### QueryClient setup with EOS defaults

```ts
// src/lib/query-client.ts
import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,              // 1 min — kills dev refetch thrash
      gcTime: 5 * 60_000,             // 5 min default
      retry: 1,                       // retry once on network blip
      refetchOnWindowFocus: "always", // catch stale dashboards on tab switch
      refetchOnReconnect: true,
      throwOnError: false,            // local handling by default
    },
    mutations: {
      retry: 0,                       // mutations should NOT auto-retry
      throwOnError: false,
    },
  },
});
```

```tsx
// src/main.tsx
import { QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { queryClient } from "./lib/query-client";

<QueryClientProvider client={queryClient}>
  <App />
  {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
</QueryClientProvider>
```

### Query key factory + `queryOptions` (v5)

```ts
// src/features/leads/queries.ts
import { queryOptions, useQuery } from "@tanstack/react-query";
import { LeadSchema, type Lead } from "@/schemas/lead";

export const leadKeys = {
  all: ["leads"] as const,
  lists: () => [...leadKeys.all, "list"] as const,
  list: (filters: { status?: string; q?: string }) =>
    [...leadKeys.lists(), filters] as const,
  details: () => [...leadKeys.all, "detail"] as const,
  detail: (id: string) => [...leadKeys.details(), id] as const,
};

export function leadDetailOptions(id: string) {
  return queryOptions({
    queryKey: leadKeys.detail(id),
    queryFn: async ({ signal }): Promise<Lead> => {
      const res = await fetch(`/api/leads/${id}`, { signal });
      if (!res.ok) throw new Error(`Failed: ${res.status}`);
      return LeadSchema.parse(await res.json());
    },
    staleTime: 30_000,
  });
}

export function useLead(id: string) {
  return useQuery(leadDetailOptions(id));
}
```

### Mutation with invalidation

```ts
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { leadKeys } from "./queries";

export function useUpdateLead(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (patch: Partial<Lead>) => {
      const res = await fetch(`/api/leads/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch),
      });
      if (!res.ok) throw await res.json().catch(() => new Error("Save failed"));
      return LeadSchema.parse(await res.json());
    },
    onSuccess: (saved) => {
      qc.setQueryData(leadKeys.detail(id), saved);
      // Return the promise so isPending stays true until refetch lands
      return qc.invalidateQueries({ queryKey: leadKeys.lists() });
    },
  });
}
```

### Optimistic update (cache approach)

```ts
useMutation({
  mutationFn: updateLead,
  onMutate: async (patch) => {
    await qc.cancelQueries({ queryKey: leadKeys.detail(id) });
    const previous = qc.getQueryData<Lead>(leadKeys.detail(id));
    qc.setQueryData<Lead>(leadKeys.detail(id), (old) =>
      old ? { ...old, ...patch } : old,
    );
    return { previous };
  },
  onError: (_err, _patch, ctx) => {
    if (ctx?.previous) qc.setQueryData(leadKeys.detail(id), ctx.previous);
  },
  onSettled: () => qc.invalidateQueries({ queryKey: leadKeys.detail(id) }),
});
```

### Suspense-first page

```tsx
import { useSuspenseQuery } from "@tanstack/react-query";
import { leadDetailOptions } from "./queries";

function LeadDetail({ id }: { id: string }) {
  // data is guaranteed defined — no isPending check
  const { data: lead } = useSuspenseQuery(leadDetailOptions(id));
  return <h1>{lead.name}</h1>;
}

// parent wraps in boundaries
<ErrorBoundary fallback={<ErrorCard />}>
  <Suspense fallback={<LeadSkeleton />}>
    <LeadDetail id={id} />
  </Suspense>
</ErrorBoundary>
```

## Conceptual Model

**Server state is fundamentally different from client state** — this is
the single insight that makes React Query make sense. Dominik Dorfmeister
(TkDodo, maintainer) frames it this way: when you `fetch` data and render
it, you are not displaying "the data" — you are displaying a **snapshot**
of how it looked when you asked. By the time your user sees it, the
server's version may already have changed.

Client state you own. Server state you borrow. Treating borrowed state
like owned state — copying it into `useState`, "initializing" from a
prop, storing it in Redux — is the source of 90% of React data bugs:
stale data after nav, lost updates, duplicate fetches, waterfalls.

React Query's job is to keep the borrowed copy fresh enough for the
user's needs, without you writing sync code. You give it:
1. A **key** (identity: what is this data?)
2. A **function** (recipe: how do I fetch it?)
3. A **freshness policy** (`staleTime`: how long is a snapshot good?)

It gives you back:
- Automatic deduplication (two components, same key → one request)
- Automatic background refetching when the user returns to the tab
- Automatic retry on failure
- Automatic garbage collection of inactive queries (`gcTime`, default 5m)
- Imperative invalidation hooks for writes

**Mental shift from "fetching library" to "state manager":** you are not
calling `fetch` with caching bolted on. You are declaring "this key maps
to this Promise," and the library owns the lifecycle. The `queryFn` is a
**pure description**, not an imperative call.

**The three kinds of state in an EOS SaaS page:**
1. **Server state** — RQ. Cached, keyed, synchronized.
2. **Client state** — `useState` / `useReducer`. UI-only: modal open,
   selected tab, hover state.
3. **URL state** — the router. Filter values, pagination page number,
   selected tab when shareable.

If you catch yourself writing `const [data, setData] = useState()` and
then `useEffect(() => fetch(...).then(setData))`, delete it. That's four
bugs waiting to happen, all of them solved by `useQuery`.

## Gotchas

- **`placeholderData` vs `initialData`.** `initialData` is **persisted
  to the cache as if it were real data** and respects `staleTime` —
  meaning if you pass stale `initialData` without `initialDataUpdatedAt`,
  RQ thinks it's fresh and won't refetch. `placeholderData` is
  **never cached**, always triggers a background refetch, and exposes
  an `isPlaceholderData` flag. Rule: use `placeholderData` for "fake
  UI until the real thing loads" (including `keepPreviousData` behavior
  in v5 via `placeholderData: (prev) => prev`); use `initialData` only
  when you are 100% certain the value is real server data (e.g.,
  hydrated from SSR or copied from another query with a known updatedAt).

- **`enabled: false` + manual `refetch` trap.** A disabled query that
  you `refetch()` manually does NOT become enabled for subsequent renders.
  It fetches once, then goes back to disabled. If you want "fetch on
  button click and then keep it live," flip `enabled` to `true` via
  state, don't call `refetch`.

- **Non-deterministic `queryKey` serialization.** RQ hashes the key
  deterministically, but this only works if the key's shape is stable.
  `['leads', { status: 'new', q: '' }]` and `['leads', { q: '', status: 'new' }]`
  hash to the SAME key (objects are sorted by key internally) — good —
  BUT `['leads', new Date()]` or `['leads', () => {}]` are
  non-serializable and will break. Use primitives and plain objects only.
  Never put a function, class instance, or `Date` directly in a key.

- **`invalidateQueries` doesn't refetch if no observer is mounted.**
  Invalidation marks a query stale, but it only refetches immediately
  for **active** (mounted/observed) queries. If you invalidate a key
  that no component is currently subscribed to, it will refetch next
  time a component mounts that query. Most of the time this is what
  you want, but if you're in a side panel mutating a list that
  just unmounted, you may see "stale" data flash on the next visit.
  Solution: `await qc.refetchQueries(...)` for critical flows, or
  keep the list mounted behind the panel.

- **`staleTime: 0` default causes refetch thrash in development.**
  The default `staleTime` is `0`, meaning every new mount is stale and
  triggers a refetch. In development with Strict Mode double-mounting,
  this doubles requests and looks like a bug. Set a project-wide
  `staleTime: 60_000` default in the `QueryClient` config and override
  per-query when you need freshness.

- **`useEffect` + `setQueryData` is an anti-pattern.** If you find
  yourself writing `useEffect(() => qc.setQueryData(key, derivedValue))`,
  delete it. Either (a) put the derivation in `queryFn` or `select`,
  or (b) if the value comes from another query, use `initialData: () =>
  qc.getQueryData(otherKey)?.subfield`. Writing to the cache from an
  effect creates ordering bugs and defeats background refetching.

- **Duplicating server state in local state.** `const [leads, setLeads] =
  useState(queryData)` is a bug. When RQ refetches in the background,
  your local copy is stale forever. If you need to edit before saving,
  use RHF (form state is client state) or keep a "draft" derived from
  the query data, not copied.

- **`isLoading` vs `isPending` (v5 rename).** In v5, the old `isLoading`
  was renamed to `isPending` (means "no data yet"). A new `isLoading`
  was reintroduced as `isPending && isFetching`. If you ported code from
  v4 and kept `isLoading`, the semantics silently changed. Use the
  codemod, then audit all status checks.

- **Per-component `new QueryClient()` instances.** Each component
  instantiating its own client defeats caching, dedup, and invalidation
  across the app. One client per app, created at module scope, passed
  via `QueryClientProvider`.

- **`useSuspenseQuery` cannot be conditionally enabled.** There is no
  `enabled` option. If you need conditional fetching inside a suspense
  page, either use regular `useQuery` for that dependent piece, or
  design the route so the dependency is part of the URL and always
  present. Queries inside a suspense component fetch serially — if you
  need parallel, use `useSuspenseQueries` or hoist them up to a parent.

- **Returning a non-Promise from `onSuccess` invalidation.** If you
  want `mutation.isPending` to stay `true` until invalidation completes,
  you must `return` the `invalidateQueries` promise from `onSuccess`.
  If you don't, the mutation resolves immediately and the UI flickers
  "success → stale → refetched."

## References

- `references/best_practices.md` — full 19-section creator-level protocol.
- `references/examples.md` — EOS-shaped recipes (QueryClient, factory,
  mutations, optimistic updates, Suspense, infinite, RHF bridge, prefetch).
- `references/anti_patterns.md` — real failure modes and the fixes.
- `references/integrations.md` — composition with React 18/19, Router,
  RHF, Zod, shadcn, TypeScript, Vite.
