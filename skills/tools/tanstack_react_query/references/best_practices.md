# TanStack Query (React) — Creator-Level Best Practices

Source: https://tanstack.com/query/latest
API Version: 5.x
SDK Version: @tanstack/react-query@5
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication

React Query is a client library — **no auth system of its own**. The
auth-like concerns that matter:

- **QueryClient identity.** One `new QueryClient()` per app. Instantiate
  at module scope or as a ref-pinned singleton in a root component.
  Multiple clients fragment the cache and break dedup across components.
- **Provider scope.** Wrap the entire app tree in `<QueryClientProvider
  client={queryClient}>`. Nested providers are possible (e.g. test
  isolation) but for production use one.
- **Request auth.** Lives inside the `queryFn`. Attach `Authorization:
  Bearer <jwt>` or send cookies via `credentials: "include"`. RQ is
  transport-agnostic and never sees your token.
- **Secrets.** No secrets in the browser bundle. Any API key required
  must live on the backend; the browser calls your own Express routes
  which call the upstream with secrets from `.env`.
- **Devtools auth.** `@tanstack/react-query-devtools` is a separate
  package. Gate with `import.meta.env.DEV` so it never ships to prod.

---

## Core Operations with Exact Signatures

### `useQuery`

```ts
function useQuery<TQueryFnData, TError, TData, TQueryKey extends QueryKey>(
  options: {
    queryKey: TQueryKey;                         // required
    queryFn: (ctx: QueryFunctionContext) => Promise<TQueryFnData>;
    enabled?: boolean;                            // default true
    staleTime?: number;                           // ms; default 0
    gcTime?: number;                              // ms; default 300_000
    refetchOnWindowFocus?: boolean | "always";
    refetchOnMount?: boolean | "always";
    refetchOnReconnect?: boolean | "always";
    refetchInterval?: number | false;
    retry?: boolean | number | ((failureCount, error) => boolean);
    retryDelay?: number | ((attempt: number) => number);
    select?: (data: TQueryFnData) => TData;       // transform for render
    placeholderData?: TData | ((prev) => TData);
    initialData?: TData | (() => TData);
    initialDataUpdatedAt?: number | (() => number);
    throwOnError?: boolean | ((error) => boolean);
    meta?: Record<string, unknown>;
    networkMode?: "online" | "always" | "offlineFirst";
  }
): UseQueryResult<TData, TError>
```

Return shape (v5):
```ts
{
  data: TData | undefined;
  error: TError | null;
  status: "pending" | "error" | "success";
  fetchStatus: "fetching" | "paused" | "idle";
  isPending: boolean;     // no data yet
  isLoading: boolean;     // isPending && isFetching (initial load only)
  isFetching: boolean;    // a request is in flight right now
  isSuccess: boolean;
  isError: boolean;
  isStale: boolean;
  isPlaceholderData: boolean;
  refetch: () => Promise<QueryObserverResult>;
  dataUpdatedAt: number;
  errorUpdatedAt: number;
  failureCount: number;
  failureReason: TError | null;
}
```

### `useMutation`

```ts
function useMutation<TData, TError, TVariables, TContext>({
  mutationFn: (variables: TVariables) => Promise<TData>,
  mutationKey?: MutationKey,
  onMutate?: (variables) => Promise<TContext> | TContext,
  onSuccess?: (data, variables, context) => Promise<unknown> | unknown,
  onError?: (error, variables, context) => Promise<unknown> | unknown,
  onSettled?: (data, error, variables, context) => Promise<unknown> | unknown,
  retry?: boolean | number;
  throwOnError?: boolean;
  networkMode?: "online" | "always" | "offlineFirst";
  scope?: { id: string };  // serialize mutations with same id
})
```

Return shape:
```ts
{
  mutate: (variables, { onSuccess, onError, onSettled }?) => void;
  mutateAsync: (variables, callbacks?) => Promise<TData>;
  data: TData | undefined;
  error: TError | null;
  variables: TVariables | undefined;
  isIdle: boolean;
  isPending: boolean;
  isSuccess: boolean;
  isError: boolean;
  status: "idle" | "pending" | "error" | "success";
  reset: () => void;
  submittedAt: number;
}
```

Key semantics:
- `mutate` is fire-and-forget; errors must be handled via `onError` or
  the component's `isError`. Never wrap `mutate` in try/catch — it won't
  throw.
- `mutateAsync` returns a Promise that rejects on error. Use when you
  need to await in the caller (e.g., sequential mutations), but you
  MUST handle the rejection.
- Callbacks on `useMutation` run first, THEN callbacks on `mutate()`.
  This is opposite of what most people expect.

### `useInfiniteQuery`

```ts
useInfiniteQuery({
  queryKey: ['leads', 'infinite', filters],
  queryFn: ({ pageParam, signal }) =>
    fetchLeads({ cursor: pageParam, ...filters, signal }),
  initialPageParam: null as string | null,
  getNextPageParam: (lastPage, pages) => lastPage.nextCursor ?? undefined,
  getPreviousPageParam: (firstPage) => firstPage.prevCursor ?? undefined,
  maxPages: 10, // cap memory
})
// returns: { data: { pages, pageParams }, fetchNextPage, hasNextPage, isFetchingNextPage }
```

### `useSuspenseQuery`

Same options as `useQuery` EXCEPT:
- No `enabled`
- No `placeholderData`
- `data` is guaranteed non-null
- Errors throw to the nearest `<ErrorBoundary>`
- Pending state throws to the nearest `<Suspense>`

```ts
const { data } = useSuspenseQuery(leadDetailOptions(id));
// data: Lead — never undefined
```

### `QueryClient` methods

```ts
qc.invalidateQueries({ queryKey, exact?, predicate?, refetchType? })
qc.refetchQueries({ queryKey, type?: 'active' | 'inactive' | 'all' })
qc.setQueryData<T>(queryKey, updater: T | ((old: T | undefined) => T))
qc.getQueryData<T>(queryKey): T | undefined
qc.prefetchQuery(options) // same shape as useQuery options
qc.cancelQueries({ queryKey })
qc.removeQueries({ queryKey })
qc.resetQueries({ queryKey })
qc.ensureQueryData(options) // returns cached or fetches
```

### `queryOptions` (v5 helper)

```ts
import { queryOptions } from "@tanstack/react-query";

const leadDetail = (id: string) => queryOptions({
  queryKey: ["leads", "detail", id] as const,
  queryFn: ({ signal }) => fetchLead(id, signal),
  staleTime: 30_000,
});

// Works everywhere:
useQuery(leadDetail(id));
qc.prefetchQuery(leadDetail(id));
qc.setQueryData(leadDetail(id).queryKey, updated);
qc.getQueryData(leadDetail(id).queryKey); // typed!
```

---

## Pagination Patterns

Two distinct patterns — pick based on UX.

### Pattern 1: "Page by page with previous-page flicker-free"

Use `placeholderData: (prev) => prev` (replaces v4's `keepPreviousData`).
The previous page stays on screen while the next page fetches. Signals
this with `isPlaceholderData`.

```ts
const [page, setPage] = useState(0);

const leads = useQuery({
  queryKey: ['leads', 'list', { page }],
  queryFn: () => fetchLeads({ page }),
  placeholderData: (prev) => prev,   // keep showing while fetching next
  staleTime: 30_000,
});

// leads.isPlaceholderData === true while the new page is loading
```

Pair with a "Next" button that's disabled when `isPlaceholderData`.

### Pattern 2: "Infinite scroll / load more"

Use `useInfiniteQuery`. Data is `{ pages: T[][], pageParams: unknown[] }`.
Flatten with `.flatMap(p => p.items)`. Cap with `maxPages` to bound memory.

```ts
const q = useInfiniteQuery({
  queryKey: ['leads', 'infinite'],
  queryFn: ({ pageParam }) => fetchLeads({ cursor: pageParam }),
  initialPageParam: null,
  getNextPageParam: (last) => last.nextCursor,
  maxPages: 20,
});

const flat = q.data?.pages.flatMap(p => p.items) ?? [];
```

**Gotcha:** infinite queries refetch ALL pages on invalidation by default
(to keep the list consistent). For very large lists this is expensive.
Use `maxPages` or switch to manual invalidation with `refetchPage`.

---

## Rate Limits

React Query has no rate limits of its own — it's a client library. What
RQ controls is **when** your `queryFn` fires:

- **Dedup window.** Identical `queryKey` calls within the same render
  cycle resolve to one in-flight request.
- **`staleTime`.** While data is fresh, `useQuery` returns cached data
  with no network call. Default 0 = always considered stale on mount.
- **Refetch triggers.** `refetchOnWindowFocus`, `refetchOnMount`,
  `refetchOnReconnect`, `refetchInterval`. Each can be overridden per
  query.
- **Retry.** Default: 3 retries with exponential backoff
  (`retryDelay: attempt => Math.min(1000 * 2 ** attempt, 30000)`).
  Mutations default to 0 retries. Override with `retry: 1` or a function
  that inspects the error to skip 4xx.

**Rate limit strategy for upstream APIs:**
```ts
retry: (failureCount, error) => {
  if (error.status === 429) return failureCount < 3;
  if (error.status >= 500) return failureCount < 2;
  return false; // don't retry 4xx
},
retryDelay: (attempt, error) => {
  // Honor Retry-After on 429
  const retryAfter = error.retryAfter;
  if (retryAfter) return retryAfter * 1000;
  return Math.min(1000 * 2 ** attempt, 30_000);
},
```

---

## Error Codes and Recovery

RQ itself throws `Error` for non-ok fetches only if YOU throw in `queryFn`.
The pattern is: check `res.ok`, throw a typed error with the status.

```ts
class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public fieldErrors?: Record<string, string[]>,
    public retryAfter?: number,
  ) { super(message); }
}

async function fetchJson<T>(url: string, schema: ZodSchema<T>, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(
      body.message ?? res.statusText,
      res.status,
      body.errors,
      res.headers.get('retry-after') ? Number(res.headers.get('retry-after')) : undefined,
    );
  }
  return schema.parse(await res.json());
}
```

### Three levels of error handling (TkDodo)

1. **Local** — `const { error, isError } = useQuery(...)`. Good for
   per-component fallback UI.
2. **Error boundaries** — pass `throwOnError: true` or a predicate
   (`throwOnError: (err) => err.status >= 500`). RQ rethrows during
   render, the nearest `<ErrorBoundary>` catches it. Good for hard
   failures on a page.
3. **Global** — `new QueryCache({ onError: (err, query) => { ... } })`.
   Fires once per failed query. Perfect for toast notifications on
   background refetch failures. Check `query.state.data !== undefined`
   to only toast for background (not initial) failures.

```ts
import { QueryCache, QueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

export const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: (error, query) => {
      if (query.state.data !== undefined) {
        toast.error(`Background refresh failed: ${error.message}`);
      }
    },
  }),
  defaultOptions: { queries: { staleTime: 60_000 } },
});
```

Mutation errors: use a `MutationCache` the same way.

### Mutation errors — server 400 → form field errors

See the RHF integration section. The pattern is:
1. Backend returns `400 { errors: { email: ['already taken'] } }`.
2. `queryFn`/`mutationFn` throws `ApiError` with `fieldErrors`.
3. `onError` maps `fieldErrors` into `form.setError(field, { type: 'server', message })`.
4. `<FormMessage />` renders them.

---

## SDK Idioms

- **Exact package:** `@tanstack/react-query` for React. Separate devtools:
  `@tanstack/react-query-devtools`. The core `@tanstack/query-core` is
  transitively installed and should not be imported directly.
- **Always use `queryOptions` over raw option objects.** Type-safe,
  colocated, reusable across `useQuery`, `prefetchQuery`, `setQueryData`.
- **Always wrap `useQuery` in a custom hook per feature.** `useLead(id)`,
  `useLeadList(filters)`, `useCurrentUser()`. Components import the hook,
  never the raw `queryKey`.
- **Custom hooks go in `src/features/{feature}/queries.ts`.** Colocate
  key factory + `queryFn` + custom hook in the same file. Only export hooks.
- **Never destructure the result if you need type narrowing.** Keep the
  object (`const leads = useQuery(...)`) so TS can narrow `leads.data`
  to non-undefined after `if (leads.isSuccess)`.
- **Type inference over explicit generics.** Annotate the `queryFn`
  return type, let TS infer `TData`. Only specify generics when using
  `select` (partial inference not supported).
- **AbortSignal.** Always thread `ctx.signal` into `fetch`:
  `queryFn: ({ signal }) => fetch(url, { signal })`. RQ aborts on unmount
  and on query key change — this cancels the underlying request.
- **`skipToken` for dependent queries (v5.25+).** Instead of
  `enabled: !!userId` + `queryFn` that could fail, pass
  `queryFn: userId ? () => fetchUser(userId) : skipToken`. Safer typing.
- **`select` for render-only transforms.** `select: (data) =>
  data.items.map(toViewModel)`. Runs on every render but is memoized
  by reference equality of `data`. Keep it pure.
- **`structuralSharing: true`** (default). RQ does deep equality on
  returned data and reuses references where possible — saves re-renders
  downstream. Don't mutate query results.

---

## Anti-Patterns

1. **`useEffect` + `fetch` + `useState`.** The whole reason RQ exists.
   Loss of caching, dedup, retry, invalidation, background refetch.
   Always `useQuery`.
2. **Copying query data into local state.**
   `const [leads, setLeads] = useState(query.data)` — stale forever on
   background refetch. Use `query.data` directly or `select`.
3. **`new QueryClient()` inside a component body without `useState` /
   `useRef`.** Re-created on every render, cache lost. Always module
   scope, or `useState(() => new QueryClient())` if you need per-tree.
4. **Broad invalidation.** `qc.invalidateQueries()` with no key
   invalidates EVERYTHING. On a dashboard with 20 queries you just
   fired 20 requests. Scope to `{ queryKey: leadKeys.all }`.
5. **Non-serializable query keys.** `['lead', new Date()]`, `['lead', fn]`,
   `['lead', classInstance]`. Keys are hashed by JSON-equivalence; these
   are unstable or unhashable.
6. **`queryKey` missing a dependency.** If `queryFn` reads `userId` from
   closure but `queryKey` is `['user']` not `['user', userId]`, you get
   stale data when `userId` changes. The key is the dep array.
7. **Passing `mutate` to callers and awaiting it.** `mutate` returns
   `void`. Use `mutateAsync` if you need to await — and handle the
   rejection.
8. **`onError` in `mutate()` options expecting to prevent the hook-level
   `onError`.** Both fire. Hook-level first, then call-level.
9. **Ignoring `select`.** Without `select`, every component subscribed
   to a query re-renders on every field change. `select` lets each
   component subscribe to the slice it cares about.
10. **`refetchInterval` as polling without considering `refetchIntervalInBackground`.**
    Default is background polling is OFF. If you want true polling even
    when the tab is hidden, set `refetchIntervalInBackground: true`.

---

## Data Model

RQ's internal data model, per query:
```
Query {
  queryKey: readonly unknown[]
  queryHash: string         // deterministic JSON hash
  queryFn: fn
  state: {
    data: T | undefined
    error: Error | null
    dataUpdatedAt: number
    errorUpdatedAt: number
    fetchStatus: 'fetching' | 'paused' | 'idle'
    status: 'pending' | 'error' | 'success'
    fetchFailureCount: number
    isInvalidated: boolean
  }
  observers: QueryObserver[]   // one per useQuery mount
  gcTime: number               // when observers===0, schedule delete
}
```

Key entities:
- **Query** — one per unique `queryKey` hash. Shared by all observers.
- **Observer** — one per `useQuery` call site. Tracks its own `select`,
  `notifyOnChangeProps`, etc.
- **Mutation** — one per `useMutation` call, per `.mutate()` invocation.
  Mutations don't persist in the cache by default (use `mutationCache`
  persistence for offline).
- **QueryCache** — owns all queries. Fires `onQueryAdded`, `onQueryRemoved`,
  `onQueryUpdated`, plus the global `onError` / `onSuccess`.
- **MutationCache** — same for mutations.

Relationships:
- Observers ↔ Query: N:1.
- When the last observer unsubscribes (unmount), the query enters "inactive"
  state. After `gcTime`, it's removed from cache.
- Invalidation walks all queries and marks matching ones stale; it
  triggers refetch only on queries with ≥1 active observer (unless
  `refetchType: 'all' | 'inactive'`).

---

## Webhooks and Events

RQ is client-side — it has no webhook system of its own. But **the
invalidation pattern IS the "webhook" pattern** for client state:

- **Mutation as event source.** Your `useMutation` is the "webhook sender."
  Its `onSuccess` is the "handler."
- **`invalidateQueries` is the fan-out.** One mutation can invalidate
  many query keys — each observer refetches independently.
- **Server-sent events / WebSocket integration:** open the socket in a
  `useEffect`, and on each event call `qc.setQueryData(key, updater)`
  or `qc.invalidateQueries({ queryKey })`. This turns RQ into a live
  data layer.

```ts
useEffect(() => {
  const ws = new WebSocket("/ws/leads");
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.type === "lead.updated") {
      qc.setQueryData(leadKeys.detail(msg.id), msg.lead);
      qc.invalidateQueries({ queryKey: leadKeys.lists() });
    }
  };
  return () => ws.close();
}, [qc]);
```

**Gotcha:** `setQueryData` accepts either a value or an updater function.
Always prefer the updater form when deriving from previous data — RQ
guarantees it's called with the current cache state.

---

## Limits

- **`queryKey` size.** No hard limit, but keys get hashed on every
  cache op. Keep to a few stable primitives + one plain object of filters.
- **Cache entries.** Unlimited in memory. Bounded only by `gcTime`.
  Extremely long-lived SPAs can accumulate — consider `staleTime: Infinity`
  for truly static data (country list, enums) and explicit `removeQueries`
  for big payloads.
- **Observers per query.** Unlimited. Each observer can have its own
  `select`, `notifyOnChangeProps`, etc.
- **Infinite query pages.** `maxPages` caps memory. Without it, infinite
  scroll leaks.
- **Mutation scope serialization.** Mutations with the same `scope.id`
  run serially. Without a scope, they parallelize.
- **Persisted cache (with `@tanstack/query-sync-storage-persister`):**
  Subject to `localStorage`/`IndexedDB` quotas (~5MB / ~50MB). Use the
  `dehydrate` filter to drop large queries before persist.

---

## Cost Model

React Query is **free and open-source** (MIT). No service, no pricing.
The "cost" is:

- **Bundle size.** `@tanstack/react-query` is ~13.4 KB gzipped in v5.
  SWR is ~4.2 KB. RTK Query is bundled with Redux Toolkit. For bundle-
  sensitive apps (landing pages), RQ may be overkill — but for any
  real app, 13KB buys you the entire server-state layer.
- **Memory.** Every cached query holds `data + metadata`. For large
  lists (thousands of rows), this can reach megabytes. Use `select`
  to project down, or don't cache the whole list — use cursor pagination.
- **Network.** The opposite of cost — RQ *saves* network calls via
  dedup and caching. Default `staleTime: 0` is network-heavy; a sane
  default of 30-60s materially reduces backend load.
- **DX cost.** Learning curve for the mental shift "server state is
  different." Real, but one-time.

**Monitoring in production:** tap `QueryCache.subscribe` to log
`queryAdded/updated` events to your analytics. Observe cache size,
stale rate, error rate. PostHog + React Query is a great combo for
dashboards on data-fetching health.

---

## Version Pinning

- **Current:** `@tanstack/react-query@5.x`. Previously `react-query@4.x`
  (the package was renamed in v4 → v5). Always use the scoped package.
- **React peer dep:** React 18+. React 19 supported fully in v5.40+.
- **SemVer:** TanStack follows strict semver. v4 → v5 was a major with
  named breaking changes (see below). Within v5, minor releases are
  additive.
- **Pinning in package.json:**
  ```json
  "@tanstack/react-query": "5.59.0",
  "@tanstack/react-query-devtools": "5.59.0"
  ```
  Pin both to the same exact minor. Devtools can lag slightly but
  should be bumped together.

### v4 → v5 breaking changes (full list)

1. **`loading` → `pending` status.** `isLoading` semantics changed.
   Old `isLoading` was "no data yet" → now `isPending`. New `isLoading`
   means `isPending && isFetching` (initial load only). `isInitialLoading`
   is deprecated.
2. **Single signature for hooks.** All hooks take one options object.
   Positional args (`useQuery(key, fn, opts)`) removed.
3. **`cacheTime` → `gcTime`.** Clearer name for garbage collection time.
4. **`useErrorBoundary` → `throwOnError`.** Same behavior, better name.
5. **`keepPreviousData` removed.** Use `placeholderData: (prev) => prev`.
6. **`onSuccess` / `onError` / `onSettled` on `useQuery` REMOVED.**
   Use the global `QueryCache` callbacks, or handle in render/effect.
   This was controversial but correct — query callbacks only fired for
   the observer that triggered the fetch, causing subtle bugs.
7. **`useInfiniteQuery` requires `initialPageParam`.** No longer optional.
8. **`refetchInterval` callback signature changed** — now receives
   `query` instead of `data`.
9. **`status: 'idle'` removed.** Disabled queries are `pending`.
10. **Custom logger removed.** Use `QueryCache({ onError })` instead.

**Migration aid:** `npx @tanstack/query-codemod`. Run prettier after.

### Upcoming (2026)

- TanStack Start integration deepening (SSR, streaming).
- Better React Server Component interop.
- No v6 on the roadmap near-term — v5 is the long-lived line.

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

**Why Tanner Linsley built it (2019).** Existing data-fetching solutions
in React fell into two buckets: Redux + sagas/thunks (too much boilerplate
for a problem that was 90% cache management) and ad-hoc `useEffect` +
`fetch` (no caching, no dedup, no retry). Apollo Client solved it for
GraphQL. Nobody solved it for REST. React Query was Tanner's answer:
**a cache that understands async, indexed by a key, agnostic to the
transport.**

**The core insight:** server state is fundamentally different from
client state. You don't own it. You can't guarantee freshness. You're
always showing a snapshot. Once you accept that, the design falls out:
- Keys identify snapshots (a cache is a map of keys to snapshots).
- Snapshots have staleness (stale-while-revalidate).
- Mutations invalidate keys (not values — you don't have to know the
  new value to mark the snapshot dirty).
- Background refetches keep snapshots fresh.

**TanStack philosophy (headless, framework-agnostic, type-safe).**
The whole TanStack ecosystem (Query, Router, Table, Form, Virtual) shares
principles: headless (no UI), framework-agnostic (core is pure JS,
adapters for React/Vue/Svelte/Solid/Angular), TypeScript-first (inference
over explicit annotations), zero-UI-opinions. You bring the components;
TanStack brings the state machine. This is why Query composes with
shadcn/ui, MUI, plain HTML — it cares only about data, never DOM.

**Conscious tradeoffs:**
- **Not normalized.** Unlike Apollo, RQ does NOT normalize entities
  across queries. Two queries returning the same user will have two
  copies. The tradeoff: simpler mental model, simpler API, no GraphQL
  schema required — but you must manually invalidate related queries.
  For 90% of apps this is the right call; for huge graph-like domains,
  Apollo is better.
- **Cache is in-memory by default.** Persistence is opt-in. Keeps the
  core small; avoids the "every page load re-fetches everything" trap
  of over-persisted caches.
- **No built-in schema validation.** You bring Zod or io-ts. RQ caches
  whatever you return from `queryFn`. Validation is your responsibility
  — and should happen at the fetch boundary, not in components.
- **Mutations don't auto-invalidate.** You must call `invalidateQueries`
  in `onSuccess`. RTK Query does auto-invalidation via tags; RQ chose
  explicitness. The tradeoff: more code, but you never invalidate
  accidentally.

**What it's explicitly NOT:**
- Not a state manager for client state (use `useState`, Zustand, Jotai).
- Not a GraphQL client (works with GraphQL but you lose normalization).
- Not a WebSocket library (you drive updates manually via `setQueryData`).
- Not a form library (use React Hook Form).

---

## Problem-Solution Map and Hidden Capabilities

**Problems RQ actually solves beyond "fetching":**

- **Request deduplication.** 10 components call `useLead('abc')` on the
  same page — one HTTP request. This alone is worth the library.
- **Stale-while-revalidate.** Show cached data instantly, refetch in
  background. Users never see loading states on repeat visits.
- **Race condition prevention.** Rapid filter changes cancel in-flight
  requests via `AbortController` + `queryKey` change. No "last response
  wins" bugs.
- **Offline queue (via persister).** Mutations queue while offline,
  retry when online.
- **Prefetch on hover.** `qc.prefetchQuery(...)` on `onMouseEnter` →
  detail page loads instantly on click.
- **Cache warming from routing.** Route loaders can `ensureQueryData`
  so the page never shows a spinner.
- **Optimistic UI with automatic rollback.** `onMutate` snapshots,
  `onError` restores. Trivially correct.

**Hidden / underused capabilities:**

- **`select` for per-observer transforms.** Different components can
  subscribe to different slices of the same query with `select`, and
  only re-render when THEIR slice changes. Massive perf win.
- **`structuralSharing`.** Deep equality + reference reuse means
  components that consume unchanged subtrees don't re-render even on
  refetch. Defaults on.
- **`notifyOnChangeProps`.** Fine-grained: "only re-render me when
  `data` changes, not `isFetching`." Hand-tuned perf.
- **`placeholderData` as a function of previous data.** The v5 way to
  get `keepPreviousData` behavior, but you can also project — e.g.,
  show the old data but flagged as "stale."
- **Mutation scopes.** `scope: { id: 'lead-save' }` serializes mutations
  with the same scope ID. Perfect for preventing double-submits.
- **`useMutationState`.** Read the state of any mutation from anywhere
  in the tree. Powers "global saving indicator" patterns.
- **`meta` on queries/mutations.** Attach arbitrary metadata, read it
  in global error handler: `meta: { errorMessage: 'Failed to save lead' }`
  → `toast.error(query.meta.errorMessage)`.
- **`QueryErrorResetBoundary`.** Resets query errors from within an
  `ErrorBoundary` so "Try Again" buttons work.
- **Dehydrate / Hydrate for SSR.** Server pre-fetches, serializes the
  cache, client hydrates. Zero hydration mismatches.
- **`matchQuery` predicates.** `invalidateQueries({ predicate: (q) =>
  q.queryKey[0] === 'leads' && q.state.dataUpdatedAt < Date.now() - 60_000 })`
  — invalidate by arbitrary logic.

---

## Operational Behavior and Edge Cases

- **Strict Mode double-invoke.** In React 18 Strict Mode dev, `useQuery`
  mounts → unmounts → mounts, doubling initial fetches. RQ deduplicates
  so only one actual request goes out, but `queryFn` may be called
  twice. Design `queryFn` to be idempotent.
- **Stale data during background refetch.** `isFetching` is true,
  `data` is old. The correct render order is: check `data` first,
  then `error`, then pending. Showing an error screen when stale
  data is available is bad UX — RQ encourages "stale data over error."
- **`enabled: false` starts as `isPending: true`, not `isIdle`.** The
  old `idle` status was removed in v5. A disabled query is pending
  until it runs once.
- **AbortController on key change.** When `queryKey` changes, the old
  query's in-flight request is cancelled via `signal.abort()`. Your
  `fetch` must thread `signal` or the request continues (wasting bandwidth
  and potentially resolving into the new cache entry).
- **`gcTime` clock starts when observer count hits 0.** Re-mounting a
  query within `gcTime` reuses the cached data. After `gcTime`, the
  query is removed and the next mount is a cold fetch.
- **`setQueryData` with a function.** The updater is called with the
  current cache value (possibly `undefined`). You MUST handle the
  undefined case: `(old) => old ? { ...old, ...patch } : old`.
- **Mutations don't cancel on unmount.** Unlike queries, `mutateAsync`
  keeps running if the component unmounts. The `onSuccess` still fires;
  DOM updates via that callback will warn. Use `qc.setQueryData` which
  is safe even without mounted observers.
- **Error identity.** RQ holds onto the last error until a successful
  refetch OR `reset()` is called. If you `refetch` and it fails again,
  the error object is a new reference — useEffect deps on error will
  re-fire.
- **Network mode.** Default `online` pauses queries when offline (shows
  `fetchStatus: 'paused'`). `always` tries regardless. `offlineFirst`
  tries once, then pauses. Matters for PWAs and poor-connection users.

---

## Ecosystem Position and Composition

**Where RQ sits:** the async state layer between your React components
and any async source (REST, GraphQL, WebSocket, IndexedDB, Web Workers).
It is the **single source of truth for server state**.

**Natural complements:**
- **React Hook Form + Zod** — forms submit via mutations, errors flow
  back via `setError`.
- **shadcn/ui + sonner** — loading skeletons via `isPending`, toasts
  via global `QueryCache` callbacks.
- **TanStack Router** — built-in RQ integration via route loaders and
  `ensureQueryData`.
- **Zod** — validate at the fetch boundary, cache typed values.
- **MSW (Mock Service Worker)** — test queries with realistic HTTP mocks.
- **@tanstack/react-query-devtools** — inspector, mandatory in dev.
- **@tanstack/query-sync-storage-persister** / `query-async-storage-persister`
  — persist the cache to localStorage / AsyncStorage.

**Forced / anti-integrations:**
- **Redux for server state.** Doing both is common, both wrong. Use
  Redux (or Zustand) for client state only, RQ for server state. Never
  dispatch query data into Redux.
- **Apollo + RQ.** Pick one per app. They're solving the same problem.
- **SWR + RQ.** Same — pick one. SWR is simpler; RQ is more complete.
- **Global `fetch` interceptors that mutate responses.** If you rewrite
  responses in an interceptor, RQ caches the rewritten version — hard
  to debug. Prefer putting transforms in `queryFn` or `select`.

**Data handoff patterns:**
- RQ → Form: `useForm({ values: query.data, resetOptions: { keepDirtyValues: true } })`
- Form → RQ: `mutation.mutate(form.getValues())` → `onSuccess` sets cache.
- RQ → URL: `useSyncQueryToUrl(query.data.sort)` — one way only.
- URL → RQ: filter values from `useSearchParams` → into `queryKey`.
- RQ → RQ (derived): `initialData: () => qc.getQueryData(otherKey)?.subfield`.
  Cheap way to pre-populate a detail query from a list query.

---

## Trajectory and Evolution

**Recent (v5.x, 2024-2026):**
- `queryOptions` helper (type-safe colocation) — widely adopted.
- `useSuspenseQuery` + `useSuspenseInfiniteQuery` — first-class Suspense.
- `skipToken` sentinel for dependent queries.
- Improved TypeScript inference across the board.
- React 19 compatibility: works with Actions, `use()`, Server Components.
- Streaming SSR support with `HydrationBoundary`.

**Current direction:**
- Deeper TanStack Start integration (SSR + streaming + RSC).
- More "query options" style helpers (loaders, mutations).
- Better offline-first primitives (persistence + sync).
- TypeScript-first DX investment continues.

**Not on the roadmap:**
- Normalized caching (Apollo's territory — explicit design tradeoff).
- Built-in schema validation (you bring Zod).
- v6 — v5 is the long-lived line. No major rewrites planned.

**Deprecated / avoid:**
- Old `react-query` package (pre-v4). Upgrade to `@tanstack/react-query@5`.
- `useQuery` positional arguments (`useQuery('key', fn)`). Options object only.
- `onSuccess`/`onError`/`onSettled` on `useQuery` (removed in v5). Use
  `QueryCache({ onError })`.
- `isInitialLoading` — use `isLoading` in v5.
- `keepPreviousData` — use `placeholderData: (prev) => prev`.
- `cacheTime` — now `gcTime`.

**Community-adopted patterns the team endorses:**
- TkDodo's query key factory (now official via `queryOptions`).
- `QueryCache` global error handler → toast pattern.
- Suspense-first page architecture with `useSuspenseQuery` + error
  boundaries.
- Colocated feature folders with `queries.ts` per feature.

---

## Conceptual Model and Solution Recipes

**Mental model:** a `QueryClient` is a map `Map<QueryHash, Query>`.
A `Query` is a state machine (`pending → fetching → success | error`)
wrapping a cached Promise result. Observers subscribe; mutations
invalidate. Everything else is sugar on this core.

**Primitives:**
- Key (identity)
- Function (recipe)
- Cache (map of key → snapshot)
- Observer (subscription)
- Mutation (event that invalidates keys)

**Verbs:**
- `useQuery` — subscribe
- `useMutation` — emit event
- `invalidateQueries` — mark stale
- `setQueryData` — write through
- `prefetchQuery` — warm cache
- `ensureQueryData` — "cached or fetched, either way return data"

### Recipe 1: Complete CRUD for a resource

```ts
// features/leads/queries.ts
export const leadKeys = { /* factory */ };
export const leadDetail = (id) => queryOptions({ /* ... */ });
export const leadList = (filters) => queryOptions({ /* ... */ });

export const useLead = (id) => useQuery(leadDetail(id));
export const useLeads = (filters) => useQuery(leadList(filters));

export const useCreateLead = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createLead,
    onSuccess: (lead) => {
      qc.setQueryData(leadKeys.detail(lead.id), lead);
      return qc.invalidateQueries({ queryKey: leadKeys.lists() });
    },
  });
};

export const useUpdateLead = (id) => { /* optimistic update */ };
export const useDeleteLead = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: deleteLead,
    onSuccess: (_, id) => {
      qc.removeQueries({ queryKey: leadKeys.detail(id) });
      return qc.invalidateQueries({ queryKey: leadKeys.lists() });
    },
  });
};
```

### Recipe 2: Suspense page with prefetch on route enter

```ts
// Route loader (Wouter/React Router adapter)
async function leadLoader({ params }) {
  await queryClient.ensureQueryData(leadDetail(params.id));
  return null; // data is in cache; page reads via useSuspenseQuery
}

function LeadPage({ id }) {
  const { data: lead } = useSuspenseQuery(leadDetail(id));
  return <LeadView lead={lead} />;
}
```

### Recipe 3: Live updates via WebSocket

```ts
useEffect(() => {
  const ws = new WebSocket(WS_URL);
  ws.onmessage = (ev) => {
    const { type, payload } = JSON.parse(ev.data);
    if (type === "lead.updated") {
      qc.setQueryData(leadKeys.detail(payload.id), payload);
    }
    if (type === "lead.deleted") {
      qc.removeQueries({ queryKey: leadKeys.detail(payload.id) });
      qc.invalidateQueries({ queryKey: leadKeys.lists() });
    }
  };
  return () => ws.close();
}, [qc]);
```

### Recipe 4: Infinite scroll list

```ts
const q = useInfiniteQuery({
  queryKey: leadKeys.list(filters),
  queryFn: ({ pageParam }) => fetchLeads({ ...filters, cursor: pageParam }),
  initialPageParam: null,
  getNextPageParam: (last) => last.nextCursor,
});
const leads = q.data?.pages.flatMap((p) => p.items) ?? [];
```

### Recipe 5: Form → mutation → invalidation → reset

```ts
const form = useForm({ resolver: zodResolver(LeadSchema), values: lead });
const mutation = useUpdateLead(id);

function onSubmit(values) {
  mutation.mutate(values, {
    onSuccess: (saved) => form.reset(saved),
    onError: (err) => {
      if (err.fieldErrors) {
        Object.entries(err.fieldErrors).forEach(([k, v]) =>
          form.setError(k, { type: 'server', message: v[0] }));
      }
    },
  });
}
```

---

## Industry Expert and Cutting-Edge Usage

**TkDodo (Dominik Dorfmeister) — maintainer, canonical voice.**
His blog is the de facto second documentation. The patterns he's
codified: query key factories, custom hooks per feature, status checks
with data-first, global error handling via `QueryCache.onError`,
`select` for render transforms, `placeholderData` over `initialData`
for most cases, and **"server state is not client state"** as the
governing principle. If there's any conflict between a random tutorial
and a TkDodo post, trust TkDodo.

**Frontier patterns (2025-2026):**

1. **`queryOptions`-everywhere.** Every query is defined via
   `queryOptions` and imported across `useQuery`, `prefetchQuery`,
   `setQueryData`. This is the type-safe equivalent of the old query
   key factory. Top codebases have eliminated raw `queryKey`/`queryFn`
   pairs entirely.

2. **Suspense-first pages.** `useSuspenseQuery` at the leaf, `<Suspense>`
   at a sensible parent, `<ErrorBoundary>` above that. Pages have no
   `isPending` branches. Loading states are skeletons rendered by the
   Suspense fallback, not conditionals in the component.

3. **Route-loader prefetch pattern.** TanStack Router and React Router
   v6.4+ loaders call `qc.ensureQueryData` to guarantee data before
   render. Users never see spinners on client-side nav.

4. **Global error handler via `QueryCache`.** All error toasts come
   from one place. Components only handle domain-specific errors.
   `meta: { errorMessage: '...' }` lets each query customize its toast.

5. **Mutation scopes for double-submit prevention.** `scope: { id:
   'save-lead' }` so even if a user mashes the button, mutations run
   serially.

6. **Offline-first with persister.** Mutations queue in IndexedDB via
   `@tanstack/query-async-storage-persister`. Sync when online. Perfect
   for mobile PWAs.

7. **WebSocket + `setQueryData` as a "live cache."** Server pushes
   updates; client updates cache; all observers re-render. Replaces
   "pull polling" entirely.

8. **React 19 `useOptimistic` + RQ optimistic updates.** Not
   redundant — they compose. `useOptimistic` for instant single-transition
   UI; RQ optimistic updates for cache-wide snapshot/rollback. Use
   `useOptimistic` for the local button state, RQ cache updates for
   everything else on the page.

9. **`useMutationState` for global "saving..." indicators.** Header bar
   shows "Saving..." when ANY mutation is pending, anywhere. One hook,
   zero prop drilling.

10. **Query-sliced subscriptions via `select`.** Heavy-data queries
    (bulk lead list) stay in one cache entry; individual components
    `select` the one lead they care about. Only re-render when their
    slice changes. Bigger lists, fewer re-renders.

**What top companies do:**
- **Vercel** — SWR (they own it). Everyone else at their scale tends
  to use RQ for the complex apps.
- **Linear** — known to use a custom sync engine, but their React
  layer patterns mirror RQ's mental model.
- **GitHub (Primer)** — shadcn-esque + RQ for their recent dashboards.
- **OSS SaaS templates** (create-t3-app, cal.com, dub.co) — RQ across
  the board, usually with tRPC's RQ adapter for end-to-end typing.

**tRPC + RQ** is the highest-leverage combo for TypeScript monorepos:
tRPC generates typed query hooks backed by RQ, so you get inferred
types from the backend handler all the way to `useQuery`. For EOS
SaaS if/when backend goes TS-unified, consider this.

---

## EOS Usage Patterns

- One `queryClient` per SaaS app at `src/lib/query-client.ts`.
- `staleTime: 60_000`, `retry: 1`, `refetchOnWindowFocus: "always"`.
- Feature folders: `src/features/{feature}/queries.ts` + `mutations.ts`.
- Every `queryFn` validates with a Zod schema from `src/schemas/`.
- Forms use RHF; submission is a mutation; `onSuccess` calls
  `qc.setQueryData` + `form.reset(saved)` + `qc.invalidateQueries`.
- Global error toasts via `QueryCache.onError` + sonner.
- Suspense-first pages with `useSuspenseQuery` where the data is
  required to render at all (lead detail, dashboard).
- Devtools mounted only under `import.meta.env.DEV`.

## Gotchas

(Mirrored from SKILL.md + project-specific failures as they emerge.)

- `placeholderData` vs `initialData` — see SKILL.md.
- `enabled: false` + manual `refetch` does not re-enable.
- Non-serializable keys (Date, fn, class instance) break hashing.
- `invalidateQueries` only refetches active observers.
- Default `staleTime: 0` thrashes in dev with Strict Mode.
- Never `useEffect` → `setQueryData` for derived state.
- Never `useState(queryData)` — reference goes stale.
- v5 rename: `isLoading` → `isPending` + new `isLoading` semantics.
- One `QueryClient` per app. Never per component.
- `useSuspenseQuery` has no `enabled`.
- Return the `invalidateQueries` promise from `onSuccess` so the
  mutation stays pending until the refetch lands.
