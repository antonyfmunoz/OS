# TanStack Query — Integrations (Composition with the EOS Stack)

React Query is the server-state layer. Everything else in `/opt/OS/saas`
composes around it. This doc is the single map of how they fit together.

---

## React 18 — Suspense + `useSuspenseQuery`

React 18 enabled Suspense for data fetching. RQ v5 ships
`useSuspenseQuery` / `useSuspenseInfiniteQuery` / `useSuspenseQueries`
to plug directly in.

```tsx
<ErrorBoundary fallback={<ErrorCard />}>
  <Suspense fallback={<PageSkeleton />}>
    <LeadDetail id={id} />
  </Suspense>
</ErrorBoundary>

function LeadDetail({ id }: { id: string }) {
  const { data } = useSuspenseQuery(leadDetailOptions(id));
  return <h1>{data.name}</h1>; // data is guaranteed defined
}
```

**What you give up:**
- No `enabled` — suspense queries can't be conditional.
- No `placeholderData` — Suspense owns the loading UX.
- No initial undefined — `data` is always typed.

**What you get:**
- No `if (isPending)` branches in page components.
- Centralized loading + error fallbacks at the boundary.
- Clean composition: sibling suspense queries fetch in **parallel**
  (thanks to React 18's concurrent render), nested queries fetch in **series**.

**The rule:** hoist multiple queries to the same component so they
parallelize. A child's query can't start until the parent's data arrives.

---

## React 19 — Actions vs RQ Mutations (and the bridge)

React 19 shipped `useActionState`, `useOptimistic`, `useFormStatus`,
and async transitions. None of these replace RQ — they compose with it.

### When to use each

**RQ `useMutation`** — default for EOS SaaS:
- Client-first flow (SPA, no progressive enhancement required)
- You want optimistic UI + rollback across the whole cache
- You want server errors mapped back into form field errors
- You want mutations to invalidate related queries automatically
- Composes with RHF + Zod + shadcn out of the box

**React 19 Actions + `useActionState`**:
- Progressive enhancement matters (the form must work without JS)
- Next.js App Router with Server Functions
- Simple form → server round trip → display result
- You want free `isPending`, automatic form reset on success, no extra library

### `useOptimistic` + RQ optimistic updates (compose, don't replace)

```tsx
import { useOptimistic } from "react";

function LeadStatusButton({ lead }: { lead: Lead }) {
  const update = useUpdateLead(lead.id);  // RQ mutation with optimistic update

  // `useOptimistic` gives INSTANT UI transitions without waiting for the cache.
  const [optimisticStatus, setOptimisticStatus] = useOptimistic(
    lead.status,
    (_prev, next: Lead["status"]) => next,
  );

  return (
    <form
      action={(fd) => {
        const next = fd.get("status") as Lead["status"];
        setOptimisticStatus(next);         // 1. Instant local feedback
        update.mutate({ status: next });   // 2. RQ optimistic update + rollback
      }}
    >
      <select name="status" defaultValue={optimisticStatus}>
        <option>new</option>
        <option>contacted</option>
        <option>qualified</option>
      </select>
      <button>Update</button>
    </form>
  );
}
```

- `useOptimistic` handles the immediate button state in the current transition.
- RQ's `onMutate` + `setQueryData` updates the cache everywhere else on
  the page (list view, sidebar, etc.) with rollback on error.

### The bridge: RHF + Actions + RQ

See the react_hook_form skill for the canonical pattern. Short version:
- RHF owns client validation and field state.
- React 19 Action owns progressive enhancement and server round trip.
- RQ owns cache and background refresh after success.
- `useActionState` bridges server response → RHF `setError`.

---

## React Router / Wouter — loaders vs RQ

There are two philosophies and they compose cleanly.

### Philosophy 1: Loaders as prefetch triggers (recommended)

```ts
// React Router v6.4+ loader
export async function leadLoader({ params }: LoaderFunctionArgs) {
  await queryClient.ensureQueryData(leadDetailOptions(params.id!));
  return null; // data lives in the RQ cache
}
```
```tsx
function LeadPage() {
  const { id } = useParams();
  const { data } = useSuspenseQuery(leadDetailOptions(id!));
  return <LeadView lead={data} />;
}
```
- The route loader warms the cache.
- The component reads via `useSuspenseQuery` — guaranteed hit.
- Background refetch keeps it fresh.
- No spinners on nav, no double fetch.

### Philosophy 2: RQ as the only loader

With Wouter (no built-in loaders), just use `useQuery` in the route
component and prefetch on hover:

```tsx
function LeadRow({ lead }: { lead: Lead }) {
  const qc = useQueryClient();
  return (
    <Link
      href={`/leads/${lead.id}`}
      onMouseEnter={() => qc.prefetchQuery(leadDetailOptions(lead.id))}
    >
      {lead.name}
    </Link>
  );
}
```

Prefetch on hover + `useSuspenseQuery` in the detail page gives the
same "instant nav" feel without router-loader glue.

---

## React Hook Form — the canonical pairing

See the `react_hook_form` skill's `integrations.md` for the full map.
Minimum version here:

```tsx
const leadQuery = useLead(id);
const update = useUpdateLead(id);

const form = useForm<LeadFormValues>({
  resolver: zodResolver(LeadFormSchema),
  defaultValues: emptyLead,
  values: leadQuery.data,                          // RQ → RHF (reactive)
  resetOptions: { keepDirtyValues: true },
  mode: "onBlur",
});

function onSubmit(values: LeadFormValues) {
  form.clearErrors("root.server");
  update.mutate(values, {
    onSuccess: (saved) => form.reset(saved),        // reset baseline
    onError: (err) => {
      if (err instanceof ApiError && err.fieldErrors) {
        for (const [k, msgs] of Object.entries(err.fieldErrors)) {
          form.setError(k as any, { type: "server", message: msgs[0] });
        }
      } else {
        form.setError("root.server", {
          message: err instanceof Error ? err.message : "Failed",
        });
      }
    },
  });
}
```

**Key rules:**
1. Never copy query data into `useState` — use `values` (reactive) or
   `defaultValues` (static).
2. Mutation `onSuccess` primes the cache (via the mutation hook) AND
   resets the form baseline.
3. Mutation `onError` maps 400 field errors into `form.setError`.
4. `form.clearErrors("root.server")` before each submit to avoid
   ghost errors.

---

## Zod — validate at the fetch boundary

One schema per resource. It's used in THREE places:
1. Frontend form validation via `zodResolver`.
2. Frontend response validation via `Schema.parse(await res.json())`.
3. Backend request validation via the same schema (shared package if
   monorepo; copy if split repos).

```ts
// src/schemas/lead.ts
export const LeadSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1),
  email: z.string().email(),
  status: z.enum(["new", "contacted", "qualified", "lost", "won"]),
});
export type Lead = z.infer<typeof LeadSchema>;

// Use in queryFn:
queryFn: async ({ signal }) => {
  const res = await fetch(`/api/leads/${id}`, { signal });
  if (!res.ok) throw new ApiError(res.status, res.statusText);
  return LeadSchema.parse(await res.json()); // ← validate + type
}
```

**Why at the boundary:** RQ caches whatever you return. If you cache
unvalidated data, every component consuming it has `any`-like risk.
Parse once at the fetch boundary and you know the cache is always
typed, always correct.

**Performance note:** Zod parsing is fast (microseconds for typical
shapes). Do not skip it to "save perf" — the cost of bad data is
much higher.

---

## shadcn/ui — loading states and toasts

shadcn provides `<Skeleton>` for loading states and integrates with
`sonner` for toasts.

### Loading skeletons

```tsx
function LeadDetail({ id }: { id: string }) {
  const q = useQuery(leadDetailOptions(id));

  if (q.isPending) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-48" />
        <Skeleton className="h-6 w-24" />
      </div>
    );
  }
  if (q.isError) return <ErrorCard error={q.error} />;

  return <LeadView lead={q.data} />;
}
```

Or use Suspense + `<Skeleton>` in the fallback (cleaner for pages
with one primary query).

### Toast-on-error via `QueryCache`

```ts
import { toast } from "sonner";

new QueryClient({
  queryCache: new QueryCache({
    onError: (error, query) => {
      if (query.state.data !== undefined) {
        // Only background refetch failures — initial ones have their own UI
        toast.error(
          (query.meta?.errorMessage as string) ?? `Refresh failed`,
        );
      }
    },
  }),
});
```

Pass a per-query message via `meta`:
```ts
queryOptions({
  queryKey: leadKeys.detail(id),
  queryFn: fetchLead,
  meta: { errorMessage: "Couldn't refresh lead details" },
});
```

### Toast-on-success for mutations

```ts
mutation.mutate(values, {
  onSuccess: () => toast.success("Lead saved"),
  onError: (err) => toast.error(err.message ?? "Save failed"),
});
```

---

## TypeScript (strict) — type inference over generics

### Infer from `queryFn`, not explicit generics

```ts
// Bad — fighting the inference
const q = useQuery<Lead, ApiError>({
  queryKey: ["lead", id],
  queryFn: () => fetchLead(id),
});

// Good — annotate the function, let RQ infer
async function fetchLead(id: string, signal?: AbortSignal): Promise<Lead> {
  const res = await fetch(`/api/leads/${id}`, { signal });
  if (!res.ok) throw new ApiError(res.status, res.statusText);
  return LeadSchema.parse(await res.json());
}

const q = useQuery({
  queryKey: ["lead", id],
  queryFn: ({ signal }) => fetchLead(id, signal),
});
// q.data is Lead | undefined, q.error is Error | null
```

### When you MUST specify generics: `select`

Partial type inference isn't supported, so `select` forces all four:
```ts
const q = useQuery<LeadListResponse, Error, string[], ReturnType<typeof leadKeys.lists>>({
  queryKey: leadKeys.lists(),
  queryFn: fetchLeads,
  select: (res) => res.items.map((l) => l.name),
});
```

The cleaner alternative is `queryOptions` — types flow end-to-end:
```ts
const opts = queryOptions({
  queryKey: leadKeys.list({}),
  queryFn: fetchLeads,
});

const q = useQuery({
  ...opts,
  select: (res) => res.items.map((l) => l.name), // inferred
});
```

### Error typing

By default, `error` is typed as `Error` (v5). To narrow to your own
class, check with `instanceof`:
```ts
if (q.error instanceof ApiError && q.error.status === 403) {
  // typed as ApiError here
}
```

Global custom error types via module augmentation (advanced):
```ts
// src/types/react-query.d.ts
import "@tanstack/react-query";
declare module "@tanstack/react-query" {
  interface Register {
    defaultError: ApiError;
  }
}
```
Now every `q.error` is typed as `ApiError` throughout the app.

### Do not destructure if you need narrowing

```ts
// Bad — loses discriminated union narrowing
const { data, isSuccess } = useQuery(opts);
if (isSuccess) {
  // data is STILL TData | undefined
}

// Good
const q = useQuery(opts);
if (q.isSuccess) {
  q.data; // narrowed to TData
}
```

---

## Vite — zero-config, devtools via conditional import

### Basic install
```bash
npm i @tanstack/react-query @tanstack/react-query-devtools
```

### No Vite config needed
RQ is a runtime library — no build-time hooks, no plugins.

### Devtools only in dev
```tsx
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";

<QueryClientProvider client={queryClient}>
  <App />
  {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
</QueryClientProvider>
```

Vite tree-shakes the import in production builds when the `DEV` check
is statically false.

### HMR behavior
Vite's Fast Refresh preserves the `QueryClient` singleton across HMR
reloads as long as it's created at module scope. If you recreate it
inside a component body, HMR will blow away the cache on every edit.

### Env vars for API base URL
```ts
// src/lib/api.ts
const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";
export const apiUrl = (path: string) => `${API_BASE}${path}`;
```

---

## Composition summary (EOS stack map)

```
Zod schema                          (src/schemas/)
  ↓ z.infer<typeof S>
apiFetch(url, Schema)               (src/lib/api.ts)
  ↓ validated typed value
queryFn: async () => { ... }        (src/features/*/queries.ts)
  ↓ Promise<T>
queryOptions({ key, fn })           (@tanstack/react-query)
  ↓ shared options object
useQuery / useSuspenseQuery / prefetchQuery
  ↓ T | undefined / T / cache
<Suspense> + <ErrorBoundary>        (React 18/19)
  ↓
Component renders <LeadView />      (shadcn/ui)
  ↓ user edits
useForm({ values: query.data })     (react-hook-form)
  ↓ form.handleSubmit(onSubmit)
useMutation.mutate(values)          (@tanstack/react-query)
  ↓ POST /api/...
Express + Drizzle validates with SAME Zod schema
  ↓ 200 saved or 400 { errors }
mutation.onSuccess → setQueryData + invalidateQueries + form.reset(saved)
mutation.onError   → form.setError per field from ApiError.fieldErrors
  ↓
<FormMessage /> renders Zod or server messages
QueryCache.onError → toast.error for background refresh failures
```

One schema. One cache. One source of truth. Every boundary validated.
Every error surfaced. Every mutation propagates through invalidation.
