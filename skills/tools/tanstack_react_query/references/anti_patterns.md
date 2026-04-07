# TanStack Query — Anti-Patterns

Real failure modes from EOS builds, TkDodo's blog, TanStack GitHub
issues, and production postmortems. Each entry: the broken pattern,
why it breaks, the fix.

---

## 1. Duplicating server state in `useState`

**Broken:**
```tsx
function LeadEditor({ id }: { id: string }) {
  const { data: lead } = useQuery(leadDetailOptions(id));
  const [name, setName] = useState(lead?.name ?? "");
  // ...
}
```

**Why it breaks:**
- `useState(lead?.name)` runs ONCE on mount with whatever `lead` was
  then (probably `undefined`). Subsequent query updates don't flow in.
- Background refetches write fresh data to the cache, but `name` in
  local state stays frozen at the initial value. The UI silently shows
  stale data.
- When the user edits `name`, you now have TWO sources of truth — the
  cache and the local copy — and no clear rule for which wins.

**Fix:** form state belongs to RHF, not `useState`. Initialize the form
from the query via `values` (reactive), not `defaultValues` (static):
```tsx
const form = useForm({
  resolver: zodResolver(LeadSchema),
  defaultValues: emptyLead,
  values: lead,                                    // reactive sync
  resetOptions: { keepDirtyValues: true },        // don't clobber edits
});
```

---

## 2. `useEffect` to sync query data into local state

**Broken:**
```tsx
const { data } = useQuery(leadListOptions({}));
const [filtered, setFiltered] = useState<Lead[]>([]);
useEffect(() => {
  setFiltered(data?.items.filter((l) => l.status === "new") ?? []);
}, [data]);
```

**Why it breaks:**
- Double render: query updates, effect runs, state updates, second render.
- Lost updates if the effect's dep array is wrong.
- Unnecessary state — the filtered list is a pure derivation.

**Fix:** compute during render, or use `select`:
```tsx
// Option 1: compute during render
const filtered = data?.items.filter((l) => l.status === "new") ?? [];

// Option 2: select — only re-renders when the projection changes
const { data: filtered } = useQuery({
  ...leadListOptions({}),
  select: (res) => res.items.filter((l) => l.status === "new"),
});
```

---

## 3. Per-component `new QueryClient()`

**Broken:**
```tsx
function App() {
  const queryClient = new QueryClient(); // new on every render!
  return (
    <QueryClientProvider client={queryClient}>
      <Routes />
    </QueryClientProvider>
  );
}
```

**Why it breaks:**
- Every render creates a new client with an empty cache, blowing away
  all cached queries.
- Dedup across components collapses.
- Invalidation from mutations hits the new client but the old observers
  are gone.

**Fix:** module scope, or `useState` lazy init:
```ts
// src/lib/query-client.ts
export const queryClient = new QueryClient({ /* defaults */ });
```
```tsx
// or for per-tree (e.g. Next.js App Router):
const [queryClient] = useState(() => new QueryClient({ /* ... */ }));
```

---

## 4. Non-deterministic / non-serializable query keys

**Broken:**
```ts
useQuery({
  queryKey: ["leads", new Date(), filtersObject, () => true],
  queryFn: fetchLeads,
});
```

**Why it breaks:**
- `new Date()` is a new value every render → cache never hits, always fetches.
- Functions and class instances don't serialize to stable hashes.
- Even plain objects work only if their contents are JSON-serializable primitives.

**Fix:** primitives and plain objects only. Object key order doesn't
matter (RQ sorts internally) but values must be stable:
```ts
useQuery({
  queryKey: ["leads", "list", { status, q, sort }],
  queryFn: fetchLeads,
});
```

For timestamps, use ISO strings. For class instances, pick a serializable
ID (e.g., `user.id`, not `user`).

---

## 5. Invalidating with the wrong granularity

**Broken (too broad):**
```ts
onSuccess: () => qc.invalidateQueries(), // no key = invalidate EVERYTHING
```

**Broken (too narrow):**
```ts
onSuccess: (lead) => qc.invalidateQueries({ queryKey: ["leads", "detail", lead.id] })
// list views stay stale
```

**Fix:** use the factory's hierarchy. Invalidate the smallest prefix
that covers everything affected by the mutation:
```ts
onSuccess: (lead) => {
  // Update the specific entry...
  qc.setQueryData(leadKeys.detail(lead.id), lead);
  // ...and invalidate the list prefix so all filter permutations refetch.
  return qc.invalidateQueries({ queryKey: leadKeys.lists() });
}
```

Prefix matching is the whole point of the factory pattern.

---

## 6. Storing mutation result in local state

**Broken:**
```tsx
const [createdLead, setCreatedLead] = useState<Lead | null>(null);
const mutation = useMutation({
  mutationFn: createLead,
  onSuccess: (lead) => setCreatedLead(lead),
});
```

**Why it breaks:**
- `mutation.data` already holds the result, typed.
- Extra state means another render and another source of truth.
- If the mutation is re-run, you're updating two things.

**Fix:**
```tsx
const mutation = useMutation({ mutationFn: createLead });
const createdLead = mutation.data; // typed, reactive
```

---

## 7. Skipping `select` → unnecessary re-renders

**Broken:**
```tsx
function LeadCount() {
  const { data } = useQuery(leadListOptions({}));
  return <span>{data?.total ?? 0}</span>;
  // Re-renders on every field of every lead, not just when total changes.
}
```

**Why it breaks:**
- Every time ANY field in the list updates, this component re-renders.
- On a 1000-row list with background refetches, this is thousands of
  wasted renders.

**Fix:**
```tsx
function LeadCount() {
  const { data: total } = useQuery({
    ...leadListOptions({}),
    select: (res) => res.total,
  });
  return <span>{total ?? 0}</span>;
}
```
Now it re-renders only when `total` actually changes. Structural sharing
+ `select` is RQ's most powerful perf lever.

---

## 8. Refetching on every mount without `staleTime`

**Broken:** default settings + many mount/unmount cycles.
```ts
// Default staleTime = 0
useQuery({ queryKey: ["me"], queryFn: fetchMe });
```

**Why it breaks:**
- Every route change that remounts this query → fresh fetch.
- Strict Mode doubles it.
- Looks like "my API is slow" when the real problem is the default.

**Fix:** set a sensible global default and override per query:
```ts
// lib/query-client.ts
defaultOptions: { queries: { staleTime: 60_000 } }

// override for truly volatile data:
useQuery({ queryKey: ["orderbook"], queryFn: fetchOrderbook, staleTime: 0 })
```

---

## 9. `useEffect` + `setQueryData` for derived state

**Broken:**
```tsx
const { data: lead } = useQuery(leadDetailOptions(id));
useEffect(() => {
  if (lead) {
    qc.setQueryData(["leads", "derived", id], derive(lead));
  }
}, [lead]);
```

**Why it breaks:**
- Creates a ghost query entry that's not driven by a real `queryFn`.
- Next background refetch of the source query runs the effect again → races.
- Invalidation doesn't work — there's nothing to refetch.

**Fix:** compute during render or use `select`:
```ts
const { data: derived } = useQuery({
  ...leadDetailOptions(id),
  select: (lead) => derive(lead),
});
```

---

## 10. Awaiting `mutation.mutate()`

**Broken:**
```ts
try {
  await mutation.mutate(values); // mutate returns void!
  toast.success("Saved");
} catch (err) {
  toast.error("Failed");
}
```

**Why it breaks:**
- `mutate` is fire-and-forget and returns `void`. `await void` is `undefined`.
- Neither `onSuccess` nor `onError` are in this code path — the handlers
  on the hook still fire, but the `try/catch` is dead code.

**Fix:** use callbacks OR `mutateAsync`:
```ts
// Callback style (preferred for component-local logic)
mutation.mutate(values, {
  onSuccess: () => toast.success("Saved"),
  onError: () => toast.error("Failed"),
});

// Async style (when you need to sequence)
try {
  await mutation.mutateAsync(values);
  toast.success("Saved");
} catch (err) {
  // Must handle rejection — unhandled otherwise
  toast.error("Failed");
}
```

---

## 11. `enabled: false` + `refetch()` as "fetch on demand"

**Broken:**
```ts
const query = useQuery({
  queryKey: ["report", params],
  queryFn: generateReport,
  enabled: false,
});

return <Button onClick={() => query.refetch()}>Run</Button>;
```

**Why it breaks:**
- The query runs once on click, but subsequent re-renders see
  `enabled: false` and don't keep it live.
- Window focus refetch, reconnect refetch, stale-time refetch — all
  dead because `enabled` is false.

**Fix:** gate with state that flips enabled on:
```ts
const [run, setRun] = useState(false);
const query = useQuery({
  queryKey: ["report", params],
  queryFn: generateReport,
  enabled: run,
});
return <Button onClick={() => setRun(true)}>Run</Button>;
```

Or use a mutation if "run once on click" is the real intent.

---

## 12. Using `isLoading` (v5) to mean "fetching in background"

**Broken (v5):**
```tsx
const q = useQuery(leadListOptions({}));
if (q.isLoading) return <Spinner />;  // only fires on INITIAL load in v5
return <List data={q.data!} />;
// — background refetches have no visible feedback
```

**Why it breaks:**
- In v5, `isLoading` means `isPending && isFetching` — true only on
  the initial hard load. Background refetches don't set it.
- You'll see a spinner once, then never during the (potentially slow)
  background refreshes.

**Fix:** use the right flag for the right thing:
- `isPending` — "no data yet, can't render anything"
- `isFetching` — "a request is in flight right now (including background)"
- `isLoading` — "isPending && isFetching" (first-time load only)

```tsx
if (q.isPending) return <Skeleton />;
return (
  <>
    {q.isFetching && <SmallSpinner className="absolute top-2 right-2" />}
    <List data={q.data} />
  </>
);
```

---

## 13. Global `QueryClient.clear()` on logout and losing app state

**Broken:** calling `qc.clear()` on logout nukes EVERY query — including
the `["currentUser"]` query whose error is what triggered the logout,
causing render loops.

**Fix:** scope the clear:
```ts
function logout() {
  // Clear user-specific data but leave app-level (tenant config, etc.)
  qc.removeQueries({ queryKey: ["me"] });
  qc.removeQueries({ queryKey: ["leads"] });
  // Or with a predicate:
  qc.removeQueries({
    predicate: (q) => (q.meta as any)?.scope === "user",
  });
}
```

Alternatively, `qc.resetQueries()` which refetches in place rather than removing.

---

## 14. Throwing non-Error values from `queryFn`

**Broken:**
```ts
queryFn: async () => {
  const res = await fetch(url);
  if (!res.ok) throw { status: res.status };  // plain object!
  return res.json();
}
```

**Why it breaks:**
- `error instanceof Error` is false.
- TS types the error as `unknown` / `Error` depending on config.
- DevTools and error boundaries handle it poorly.

**Fix:** always throw a real `Error` subclass:
```ts
class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

if (!res.ok) throw new ApiError(res.status, `Fetch failed: ${res.status}`);
```
