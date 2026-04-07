---
name: tanstack_table
description: "Use when building data tables in EOS SaaS with @tanstack/react-table v8 — defining ColumnDef<TData, TValue>, wiring getCoreRowModel/getSortedRowModel/getFilteredRowModel/getPaginationRowModel, composing with shadcn DataTable (flexRender), integrating server-driven pagination/sorting/filtering with TanStack Query (manualPagination + placeholderData), row selection, column visibility, faceted filters, expanding rows, and row virtualization via @tanstack/react-virtual. Also triggers when debugging unstable column/data references causing infinite re-renders, missing row models, wrong accessorKey vs accessorFn choices, or state sync bugs between controlled table state and URL/query params."
allowed-tools: "Read, Write, Edit, Bash, WebFetch, WebSearch"
version: 1.0
trigger: both
effort: high
context: fork
last_researched: "2026-04-06"
last_updated: "2026-04-06"
api_version: "8.x"
sdk_version: "@tanstack/react-table@8"
speed_category: "medium"
source_url: "https://tanstack.com/table/latest"
sources:
  - "https://tanstack.com/table/latest/docs/introduction"
  - "https://tanstack.com/table/latest/docs/guide/column-defs"
  - "https://tanstack.com/table/latest/docs/guide/row-models"
  - "https://tanstack.com/table/latest/docs/framework/react/guide/table-state"
  - "https://tanstack.com/table/latest/docs/guide/pagination"
  - "https://tanstack.com/table/latest/docs/guide/sorting"
  - "https://tanstack.com/table/latest/docs/guide/column-filtering"
  - "https://tanstack.com/table/latest/docs/guide/global-filtering"
  - "https://tanstack.com/table/latest/docs/guide/row-selection"
  - "https://tanstack.com/table/latest/docs/guide/column-visibility"
  - "https://tanstack.com/table/latest/docs/guide/expanding"
  - "https://tanstack.com/table/latest/docs/guide/virtualization"
  - "https://ui.shadcn.com/docs/components/data-table"
  - "https://tanstack.com/virtual/latest"
---

# Tool: TanStack Table (React adapter) — @tanstack/react-table v8

TanStack Table is the **headless table engine** for every data grid in
`/opt/OS/saas`. Leads list, organizations directory, campaign dashboard,
message inbox, billing history, analytics breakdowns — any time we
render rows of backend data with sorting, filtering, pagination, or
selection, it goes through `useReactTable`.

This skill keeps the EOS SaaS from reinventing sort/filter/pagination
state machines per page. TanStack Table owns the state; shadcn's
DataTable pattern owns the markup; TanStack Query owns the fetch.
Three primitives, zero duplication.

## What This Tool Does

TanStack Table is a **framework-agnostic, headless, type-safe table
state engine**. "Headless" means it ships zero markup and zero CSS —
it hands you a `table` instance with rows, columns, and header groups,
and you render them with your own components (in our case, shadcn
`<Table>` + `flexRender`).

Core primitives:
- **`ColumnDef<TData, TValue>`** — the schema. Declares how one column
  extracts its value (`accessorKey` or `accessorFn`), how it renders
  (`header`, `cell`, `footer`), and per-column behavior (sort/filter
  functions, `enableSorting`, `meta` for custom payloads).
- **`useReactTable(options)`** — the React adapter. Takes `data`,
  `columns`, row models, and state, returns a `table` instance.
- **Row models** — tree-shakable opt-in pipelines:
  `getCoreRowModel` (always required), `getSortedRowModel`,
  `getFilteredRowModel`, `getPaginationRowModel`,
  `getGroupedRowModel`, `getExpandedRowModel`,
  `getFacetedRowModel`, `getFacetedUniqueValues`,
  `getFacetedMinMaxValues`.
- **`flexRender(Component, context)`** — renders a column's `header`
  or `cell` whether it's a string, JSX, or function component. Always
  use this in the render layer; never call `cell()` directly.
- **Table state** — `sorting`, `columnFilters`, `globalFilter`,
  `pagination`, `rowSelection`, `columnVisibility`, `columnOrder`,
  `columnSizing`, `expanded`, `grouping`. Each can be uncontrolled
  (initial only) or controlled via `state` + `onXChange`.

## EOS Integration

**Where TanStack Table lives:**
- `/opt/OS/saas/*/src/components/data-table/data-table.tsx` — the
  generic shadcn-style `DataTable<TData, TValue>` component. One per
  saas. Takes `columns`, `data`, and optional server-state props.
- `/opt/OS/saas/*/src/components/data-table/data-table-*.tsx` —
  column header (sort indicators), pagination bar, view options
  (column visibility), faceted filter popover. All shadcn patterns.
- `/opt/OS/saas/*/src/features/{feature}/columns.tsx` — the
  `ColumnDef[]` for a feature, colocated with its Zod schema.
- `/opt/OS/saas/*/src/features/{feature}/{feature}-table.tsx` — the
  feature-specific table that wires columns + `useQuery` + `DataTable`.

**Stack partners:**
- **TanStack React Query** — the data source. Server-driven tables
  pass `pagination`/`sorting`/`columnFilters` into the `queryKey` and
  use `placeholderData: (prev) => prev` to keep the old page visible
  while the new one loads (v5 replacement for `keepPreviousData`).
- **shadcn/ui** — `<Table>`, `<TableHeader>`, `<TableBody>`,
  `<TableRow>`, `<TableCell>`, `<Input>`, `<DropdownMenu>`,
  `<Button>`. Composition not inheritance.
- **TanStack React Virtual** (`@tanstack/react-virtual`) — row
  virtualization for any table over ~500 rows. Required for the
  leads list at 10k+ rows.
- **Zod** — every row type is a Zod-inferred type. `ColumnDef<Lead>`
  is fully typed because `Lead` comes from `LeadSchema.infer`.
- **React Hook Form** — inline row editing when needed. Each row's
  form is a separate `useForm` scoped to that row, not a global form.

**The rule:** columns are memoized at module scope or via `useMemo`
with stable deps. `data` is the unwrapped React Query `data ?? []`.
Never inline `columns={[...]}` or `data={[...]}` in JSX — every
render creates a new reference and the table resets state.

## Authentication

TanStack Table is a pure client-side library — **no API keys, no auth,
no network**. The "auth-like" concerns are:

- **Version pinning** — `@tanstack/react-table@8.x`. Pin to exact minor
  if you rely on v8.17+ (`placeholderData` pattern, `getFacetedUniqueValues`
  improvements). Verify with `npm ls @tanstack/react-table`.
- **Adapter split** — `@tanstack/react-table` re-exports from
  `@tanstack/table-core`. Import from the react package only; don't
  mix imports or you'll duplicate types.
- **Peer React** — v8 supports React 16.8+, 17, 18, 19. Our saas is
  React 18 strict mode; works with StrictMode double-render because
  the table instance is stable per `useReactTable` call.
- **Data auth** — lives inside the `queryFn` of the TanStack Query
  hook feeding `data`, not in the table. The table sees only rows.

## Quick Reference

### Minimal client-side table

```tsx
// src/features/leads/columns.tsx
import type { ColumnDef } from "@tanstack/react-table";
import type { Lead } from "@/schemas/lead";
import { Button } from "@/components/ui/button";
import { ArrowUpDown } from "lucide-react";

export const leadColumns: ColumnDef<Lead>[] = [
  {
    accessorKey: "name",
    header: ({ column }) => (
      <Button
        variant="ghost"
        onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
      >
        Name <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    ),
    cell: ({ row }) => <span className="font-medium">{row.getValue("name")}</span>,
  },
  {
    accessorKey: "status",
    header: "Status",
    filterFn: "equals",
  },
  {
    id: "fullName",
    accessorFn: (row) => `${row.firstName} ${row.lastName}`,
    header: "Full name",
  },
  {
    accessorKey: "createdAt",
    header: "Created",
    cell: ({ getValue }) =>
      new Intl.DateTimeFormat("en-US").format(new Date(getValue<string>())),
    sortingFn: "datetime",
  },
];
```

```tsx
// src/features/leads/leads-table.tsx
import { useMemo, useState } from "react";
import {
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  useReactTable,
  type SortingState,
  type ColumnFiltersState,
} from "@tanstack/react-table";
import { useLeads } from "./queries";
import { leadColumns } from "./columns";
import { DataTable } from "@/components/data-table/data-table";

export function LeadsTable() {
  const { data = [] } = useLeads();
  const columns = useMemo(() => leadColumns, []);
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);

  const table = useReactTable({
    data,
    columns,
    state: { sorting, columnFilters },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
  });

  return <DataTable table={table} />;
}
```

### Server-driven pagination + sorting (manual mode + React Query)

```tsx
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import {
  getCoreRowModel,
  useReactTable,
  type PaginationState,
  type SortingState,
} from "@tanstack/react-table";

export function ServerLeadsTable() {
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: 25,
  });
  const [sorting, setSorting] = useState<SortingState>([]);

  const { data } = useQuery({
    queryKey: ["leads", "list", { pagination, sorting }],
    queryFn: ({ signal }) =>
      fetchLeads({
        page: pagination.pageIndex,
        size: pagination.pageSize,
        sort: sorting[0]?.id,
        desc: sorting[0]?.desc,
        signal,
      }),
    placeholderData: keepPreviousData, // v5: prevents page flicker
  });

  const table = useReactTable({
    data: data?.rows ?? [],
    columns: leadColumns,
    pageCount: data?.pageCount ?? -1, // -1 = unknown total
    state: { pagination, sorting },
    onPaginationChange: setPagination,
    onSortingChange: setSorting,
    manualPagination: true,
    manualSorting: true,
    getCoreRowModel: getCoreRowModel(),
  });

  return <DataTable table={table} />;
}
```

### Virtualized body (10k+ rows)

```tsx
import { useVirtualizer } from "@tanstack/react-virtual";
import { useRef } from "react";

function VirtualBody({ table }: { table: ReturnType<typeof useReactTable> }) {
  const parentRef = useRef<HTMLDivElement>(null);
  const rows = table.getRowModel().rows;

  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 44,
    overscan: 10,
  });

  return (
    <div ref={parentRef} className="h-[600px] overflow-auto">
      <div style={{ height: virtualizer.getTotalSize(), position: "relative" }}>
        {virtualizer.getVirtualItems().map((vi) => {
          const row = rows[vi.index];
          return (
            <div
              key={row.id}
              data-index={vi.index}
              ref={virtualizer.measureElement}
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                width: "100%",
                transform: `translateY(${vi.start}px)`,
              }}
            >
              {row.getVisibleCells().map((cell) => (
                <span key={cell.id}>
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </span>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

## Conceptual Model

**A table is a pipeline, not a component.** TanStack Table's key
insight (Tanner Linsley, 2021) is that every "feature" of a data grid
— sort, filter, paginate, group, expand — is a **pure transformation
from one row model to the next**. `getCoreRowModel` produces the base
rows from `data`. `getFilteredRowModel` consumes that and returns only
passing rows. `getSortedRowModel` consumes that and sorts. And so on.

Because each transformation is its own function you import, the bundler
**tree-shakes the ones you don't use**. A read-only table pays for
`getCoreRowModel` and nothing else. A full-featured admin grid opts in
to the pipeline it needs. This is why the v8 API feels verbose
(`getSortedRowModel: getSortedRowModel()`) — that line IS the opt-in.

**Headless means you own the JSX.** The `table` instance gives you
`getHeaderGroups()`, `getRowModel().rows`, `row.getVisibleCells()`.
You render with your components. `flexRender` exists because a column's
`header` or `cell` can be a string, a JSX element, or a component
function — `flexRender` normalizes them so your render code is uniform.

**The three kinds of table state:**
1. **Uncontrolled** — pass `initialState`, the table owns it. Fine
   for throwaway prototypes, never for production pages because you
   can't read it from outside the table.
2. **Controlled** — pass `state.X` + `onXChange`. You own it in
   React state (or URL state, or Zustand). **This is the default for
   all EOS tables** because it's the only way to sync state with the
   URL and with React Query's `queryKey`.
3. **Mixed** — some state controlled, some not. Valid but confusing;
   prefer fully controlled.

**Client vs server mode per feature.** Every row model has a `manualX`
flag. `manualPagination: true` tells the table "I'm paginating server-
side, don't slice the rows." You still pass `pageCount` (or `rowCount`
in v8.13+) so the pagination UI knows how many pages exist. Same for
`manualSorting`, `manualFiltering`. You can mix modes: manual
pagination with client-side filtering is common (filter what we have,
fetch more when paging).

**Columns are the schema, data is the payload.** Memoize columns.
Never inline `columns={[...]}`. Every new array identity causes the
table to rebuild header groups, column sizing maps, and faceted caches.

## Gotchas

- **Unstable `data` or `columns` reference causes infinite re-render
  or state resets.** The #1 bug. If you write
  `useReactTable({ data: query.data ?? [], columns: [...] })` inline,
  every render creates a new empty array and a new columns array, so
  the table resets `sorting`, `pagination`, everything. Fix: destructure
  `const { data = EMPTY } = useQuery(...)` with a module-scope
  `const EMPTY: Lead[] = []`, and define `columns` at module scope or
  via `useMemo(() => [...], [])` with empty deps if they don't depend
  on props.

- **`accessorKey` vs `accessorFn` mix-up.** `accessorKey: "user.name"`
  does NOT traverse nested objects — it looks up the literal key
  `"user.name"`. For nested data use `accessorFn: (row) => row.user.name`
  and set `id: "userName"` because accessor functions have no implicit id.

- **Forgetting to opt into a row model silently disables the feature.**
  If you set `state.sorting` and `onSortingChange` but forget
  `getSortedRowModel: getSortedRowModel()`, sorting state updates but
  rows never reorder. No error, no warning. Same for filter, pagination,
  etc. Always pair state with its row model.

- **`manualPagination: true` without `pageCount` breaks the pagination
  UI.** The "last page" button and `getPageCount()` return 1. Pass
  `pageCount: data?.pageCount ?? -1` (or `rowCount` in v8.13+) from
  your server response.

- **`keepPreviousData` is removed from React Query v5.** The correct
  bridge is `placeholderData: keepPreviousData` (imported from
  `@tanstack/react-query`) OR `placeholderData: (prev) => prev`. Without
  it, every page change flashes a loading skeleton and the table
  "jumps" because `data` becomes undefined.

- **`flexRender` called wrong.** Must be
  `flexRender(cell.column.columnDef.cell, cell.getContext())` — not
  `flexRender(cell.getValue(), ...)`. `getValue` returns the raw
  accessor value; `columnDef.cell` is the renderer. Mixing them up
  either skips your custom cell or crashes.

- **Row selection state uses row IDs, not indices.** `rowSelection` is
  `Record<string, boolean>` keyed by `row.id`. By default `row.id` is
  the row index, which **changes when you sort or filter**, corrupting
  the selection. Always set `getRowId: (row) => row.id` (or whatever
  your stable PK is) on `useReactTable`.

- **`columnFilters` shape is an array, not an object.** It's
  `[{ id: "status", value: "new" }]`, not `{ status: "new" }`. Easy to
  get wrong when writing URL sync code.

- **StrictMode double-mount + module-level column state.** If you
  stash mutable state INSIDE a column def (e.g., a closure over a
  `useState` setter), React 18 StrictMode will invoke it twice and
  your first call's setter is stale. Keep column defs pure; put
  handlers in `meta` and read them from `row.original` + context.

- **Virtualizer with `estimateSize` too far off causes jitter.** If
  your rows are 60px but you set `estimateSize: () => 20`, the
  virtualizer calculates offsets wrong on first render and the scroll
  position "snaps" when real sizes measure in. Measure a few rows,
  set an accurate estimate, and use `virtualizer.measureElement` on
  the row element.

- **`getFacetedUniqueValues` runs over the pre-filtered rows by
  default.** So your facet dropdown shows options from rows the
  user already filtered out. Usually fine, but if you want only
  currently-visible options, use `table.getColumn(id)?.getFacetedRowModel()`
  downstream or build the list from `getFilteredRowModel()` yourself.

- **`enableMultiSort` defaults vary.** Shift-click multi-sort is on by
  default in v8. If your UX team wants single-sort only, set
  `enableMultiSort: false` at table level, not per column.

## References

- `references/best_practices.md` — full 19-section creator-level protocol.
- `references/examples.md` — EOS-shaped recipes (client table, server
  table with RQ, virtualized 10k, row selection with stable IDs,
  faceted filters, inline editing with RHF, URL-synced state).
- `references/anti_patterns.md` — real failure modes and fixes.
- `references/integrations.md` — composition with React 18, TypeScript,
  shadcn DataTable, TanStack Query, TanStack Virtual, Zod, RHF, Tailwind.
