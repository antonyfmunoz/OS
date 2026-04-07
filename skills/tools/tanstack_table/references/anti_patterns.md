# TanStack Table v8 — Anti-Patterns

Real failures, real fixes. Each one is a bug that has shipped.

---

## 1. Inlining `data` or `columns` causes infinite re-renders / state resets

```tsx
// WRONG
function LeadsTable() {
  const { data } = useQuery({ queryKey: ["leads"], queryFn: fetchLeads });
  const table = useReactTable({
    data: data ?? [],                       // new [] every render
    columns: [                              // new array every render
      { accessorKey: "name", header: "Name" },
      { accessorKey: "email", header: "Email" },
    ],
    getCoreRowModel: getCoreRowModel(),
  });
}
```

`data ?? []` creates a fresh empty array on every render. The table
treats it as "data changed", recomputes row models, and resets internal
caches. Worse, the inline `columns` array changes identity every render,
which resets `sorting`, `pagination`, `columnFilters`, etc.

```tsx
// RIGHT
const EMPTY: Lead[] = [];
const columns: ColumnDef<Lead>[] = [        // module scope
  { accessorKey: "name", header: "Name" },
  { accessorKey: "email", header: "Email" },
];

function LeadsTable() {
  const { data = EMPTY } = useQuery({ queryKey: ["leads"], queryFn: fetchLeads });
  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });
}
```

If columns must depend on props/state, wrap in `useMemo` with **all**
dependencies declared.

---

## 2. `accessorKey: "user.name"` doesn't traverse nested objects

```tsx
// WRONG
{ accessorKey: "user.name", header: "User" }
// looks up row["user.name"], not row.user.name → undefined
```

```tsx
// RIGHT
{
  id: "userName",
  accessorFn: (row) => row.user.name,
  header: "User",
}
```

Or with the column helper:

```ts
columnHelper.accessor((row) => row.user.name, {
  id: "userName",
  header: "User",
})
```

---

## 3. Skipping `getRowId` corrupts row selection on sort

```tsx
// WRONG — selection keys are array indices
useReactTable({
  data,
  columns,
  state: { rowSelection },
  onRowSelectionChange: setRowSelection,
  getCoreRowModel: getCoreRowModel(),
  getSortedRowModel: getSortedRowModel(),
});
```

Select row #3, then sort by name → "row 3" is now a different lead.

```tsx
// RIGHT
useReactTable({
  data,
  columns,
  getRowId: (row) => row.id,             // your DB primary key
  state: { rowSelection },
  onRowSelectionChange: setRowSelection,
  getCoreRowModel: getCoreRowModel(),
  getSortedRowModel: getSortedRowModel(),
});
```

---

## 4. Forgetting the row model silently disables the feature

```tsx
// WRONG — sorting state updates, rows never reorder
useReactTable({
  data,
  columns,
  state: { sorting },
  onSortingChange: setSorting,
  getCoreRowModel: getCoreRowModel(),
  // missing: getSortedRowModel
});
```

```tsx
// RIGHT
useReactTable({
  data,
  columns,
  state: { sorting },
  onSortingChange: setSorting,
  getCoreRowModel: getCoreRowModel(),
  getSortedRowModel: getSortedRowModel(),
});
```

Same trap for `getFilteredRowModel`, `getPaginationRowModel`,
`getExpandedRowModel`, etc. **Rule:** every state field needs its
matching row model unless `manualX` is true.

---

## 5. `flexRender` called with the wrong first arg

```tsx
// WRONG — renders the raw value, ignores your custom cell renderer
<TableCell>{flexRender(cell.getValue(), cell.getContext())}</TableCell>
```

```tsx
// RIGHT
<TableCell>{flexRender(cell.column.columnDef.cell, cell.getContext())}</TableCell>
```

Same for headers — `flexRender(header.column.columnDef.header, header.getContext())`.

---

## 6. `keepPreviousData` removed in React Query v5

```tsx
// WRONG (v4 syntax) — TS error or silently undefined
useQuery({
  queryKey: ["leads", pagination],
  queryFn: () => fetchLeads(pagination),
  keepPreviousData: true,
});
```

```tsx
// RIGHT (v5)
import { keepPreviousData } from "@tanstack/react-query";

useQuery({
  queryKey: ["leads", pagination],
  queryFn: () => fetchLeads(pagination),
  placeholderData: keepPreviousData,
});
```

Without it, every page change blanks the table for a frame.

---

## 7. Forgetting to reset `pageIndex` when filters change

```tsx
// WRONG — user is on page 5, applies filter, sees empty page
onColumnFiltersChange: setColumnFilters,
```

```tsx
// RIGHT
onColumnFiltersChange: (updater) => {
  setColumnFilters(updater);
  setPagination((p) => ({ ...p, pageIndex: 0 }));
},
```

---

## 8. `manualPagination: true` without `pageCount`

```tsx
// WRONG — pagination UI thinks there's only 1 page
useReactTable({
  data: data?.rows ?? [],
  columns,
  state: { pagination },
  onPaginationChange: setPagination,
  manualPagination: true,
  getCoreRowModel: getCoreRowModel(),
});
```

```tsx
// RIGHT
useReactTable({
  data: data?.rows ?? [],
  columns,
  pageCount: data?.pageCount ?? -1,
  state: { pagination },
  onPaginationChange: setPagination,
  manualPagination: true,
  getCoreRowModel: getCoreRowModel(),
});
```

Use `-1` when total is unknown — the UI uses
`getCanNextPage()` instead.

---

## 9. Per-component `new QueryClient()` next to a per-component table

Tables themselves don't share state — but the **data** behind them does.
If each `LeadsTable` instance creates its own `QueryClient`, two
instances on the same page fetch twice. Same trap on the table side:

```tsx
// WRONG — creates a new client and a new column array per render
function MyTable() {
  const queryClient = new QueryClient();
  const columns = [...];
}
```

QueryClient → module scope. Columns → module scope or `useMemo`.

---

## 10. Storing table state in Redux / Zustand "for global access"

```tsx
// WRONG — duplicates the truth
const sorting = useAppStore((s) => s.tables.leads.sorting);
const setSorting = useAppStore((s) => s.tables.leads.setSorting);
useReactTable({ state: { sorting }, onSortingChange: setSorting, ... });
```

The table already owns this. If you need the state for URL sync, use
`nuqs` or `useSearchParams` — that's a projection, not a duplicate.
Don't lift table state into a global store unless multiple, distant
components truly need to read it.

---

## 11. Mutating `data` in place

```tsx
// WRONG
data.push(newRow);                           // mutating array
data[0].status = "won";                      // mutating row
```

The table uses reference equality to detect changes. In-place mutation
is invisible to React; the table won't re-render. Always replace
immutably (or let React Query do it via `setQueryData`).

---

## 12. `useEffect` to "sync" table state somewhere else

```tsx
// WRONG
useEffect(() => {
  router.push(`?page=${pagination.pageIndex}`);
}, [pagination]);
```

Effects-for-sync are an anti-pattern. Do it in the change handler:

```tsx
onPaginationChange: (updater) => {
  setPagination(updater);
  // router update happens via state → URL projection in render, or:
  const next = typeof updater === "function" ? updater(pagination) : updater;
  router.push(`?page=${next.pageIndex}`);
},
```

Better: use `nuqs` so the URL **is** the state.

---

## 13. Calling row models as values instead of factories

```tsx
// WRONG — TypeError, getCoreRowModel is a factory
useReactTable({
  data,
  columns,
  getCoreRowModel,                  // missing parens
});
```

```tsx
// RIGHT
useReactTable({
  data,
  columns,
  getCoreRowModel: getCoreRowModel(),    // call it
});
```

The repeated parens are intentional — the outer is the factory, the
returned function is the actual row-model implementation closed over
your table options.

---

## 14. Putting non-serializable values in `meta`

```tsx
// WRONG — function in meta breaks structuredClone, devtools, URL sync
{ accessorKey: "x", meta: { onClick: handleClick } }
```

Keep `meta` to plain JSON-serializable data. For handlers, pass them
via React context or props through the render layer.

---

## 15. Virtualizing without `getScrollElement` set correctly

```tsx
// WRONG — virtualizer measures viewport instead of table container
const virtualizer = useVirtualizer({
  count: rows.length,
  getScrollElement: () => document.body,  // body never scrolls in our app
  estimateSize: () => 44,
});
```

```tsx
// RIGHT
const parentRef = useRef<HTMLDivElement>(null);
const virtualizer = useVirtualizer({
  count: rows.length,
  getScrollElement: () => parentRef.current,
  estimateSize: () => 44,
});
return <div ref={parentRef} className="h-[640px] overflow-auto">...</div>;
```
