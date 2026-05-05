# TanStack Table v8 — Creator-Level Best Practices

Tool: `@tanstack/react-table` v8.x
Last researched: 2026-04-06
Sources: tanstack.com/table/latest, ui.shadcn.com/docs/components/data-table,
Tanner Linsley talks, TkDodo & Dominik blog posts, GitHub issues (tanstack/table).

---

## Authentication

**N/A — no credentials.** TanStack Table is a headless client-side
state engine. There is no API, no server, no token, no secret, no
rate limit, no webhook. The "auth-like" concerns are:

- **Peer deps:** React 16.8+ / 17 / 18 / 19. EOS saas uses React 18
  strict mode; v8 is strict-mode safe.
- **Package split:** Import from `@tanstack/react-table` only — it
  re-exports from `@tanstack/table-core`. Do not install `table-core`
  directly; you'll duplicate types and break generics.
- **Version pinning:** pin to `^8.17.0` or later in `package.json` for
  `rowCount` support, v5-compatible `placeholderData` docs, and
  improved `getFacetedUniqueValues` perf.
- **Install commands:**
  ```bash
  npm i @tanstack/react-table
  npm i @tanstack/react-virtual   # only if virtualizing
  ```
- **Devtools:** `@tanstack/react-table-devtools` exists but is rarely
  needed — React DevTools already shows table state because it's all
  `useState`. Skip unless debugging facet/sort pipeline behavior.
- **Multi-tenant:** not applicable — all state is per-component-instance.

---

## Core Operations with Exact Signatures

### `useReactTable<TData>(options): Table<TData>`

The single React hook. Signature (trimmed to the fields EOS uses):

```ts
useReactTable<TData>({
  data: TData[],                              // required — memoized reference
  columns: ColumnDef<TData, any>[],           // required — memoized reference
  // Row models (tree-shakable, import from @tanstack/react-table)
  getCoreRowModel: () => (table) => RowModel<TData>,       // required
  getSortedRowModel?: () => (table) => RowModel<TData>,
  getFilteredRowModel?: () => (table) => RowModel<TData>,
  getPaginationRowModel?: () => (table) => RowModel<TData>,
  getExpandedRowModel?: () => (table) => RowModel<TData>,
  getGroupedRowModel?: () => (table) => RowModel<TData>,
  getFacetedRowModel?: () => (table) => RowModel<TData>,
  getFacetedUniqueValues?: () => (table, columnId) => Map<any, number>,
  getFacetedMinMaxValues?: () => (table, columnId) => [number, number],
  // Controlled state
  state?: Partial<TableState>,                // subset of: sorting, columnFilters, globalFilter, pagination, rowSelection, columnVisibility, columnOrder, columnSizing, expanded, grouping
  initialState?: Partial<TableState>,
  // Change handlers (required when state is passed for that field)
  onSortingChange?: OnChangeFn<SortingState>,
  onColumnFiltersChange?: OnChangeFn<ColumnFiltersState>,
  onGlobalFilterChange?: OnChangeFn<any>,
  onPaginationChange?: OnChangeFn<PaginationState>,
  onRowSelectionChange?: OnChangeFn<RowSelectionState>,
  onColumnVisibilityChange?: OnChangeFn<VisibilityState>,
  onExpandedChange?: OnChangeFn<ExpandedState>,
  // Manual (server-side) flags
  manualPagination?: boolean,
  manualSorting?: boolean,
  manualFiltering?: boolean,
  manualGrouping?: boolean,
  manualExpanding?: boolean,
  // Server-driven totals
  pageCount?: number,                         // -1 if unknown
  rowCount?: number,                          // v8.13+
  // Identity
  getRowId?: (row: TData, index: number, parent?: Row<TData>) => string,
  getSubRows?: (row: TData) => TData[] | undefined,
  // Feature toggles
  enableSorting?: boolean,
  enableMultiSort?: boolean,
  enableRowSelection?: boolean | ((row: Row<TData>) => boolean),
  enableColumnResizing?: boolean,
  columnResizeMode?: "onChange" | "onEnd",
  defaultColumn?: Partial<ColumnDef<TData, any>>,
  debugTable?: boolean,
  debugAll?: boolean,
});
```

### Key instance methods

```ts
table.getHeaderGroups(): HeaderGroup<TData>[]
table.getRowModel(): { rows: Row<TData>[], flatRows, rowsById }
table.getState(): TableState
table.setPageIndex(n)  setPageSize(n)  nextPage()  previousPage()
table.getCanPreviousPage(): boolean
table.getCanNextPage(): boolean
table.getPageCount(): number
table.getFilteredRowModel(): RowModel
table.getSelectedRowModel(): RowModel
table.getColumn(id): Column<TData> | undefined
table.resetSorting()  resetColumnFilters()  resetRowSelection()

// Row:
row.id                  // stable id from getRowId or index fallback
row.original            // the raw TData
row.getValue(columnId)  // accessor-extracted + filter-fn aware
row.getVisibleCells()
row.getIsSelected()  toggleSelected()  getCanSelect()
row.getIsExpanded()  toggleExpanded()  getCanExpand()
row.subRows

// Column:
column.getIsSorted(): false | "asc" | "desc"
column.toggleSorting(desc?: boolean, multi?: boolean)
column.getCanSort()  getCanFilter()  getCanHide()
column.setFilterValue(value)
column.getFacetedUniqueValues(): Map<any, number>
column.getFacetedMinMaxValues(): [number, number]
```

### `ColumnDef<TData, TValue>`

```ts
{
  id?: string,                                     // required when no accessorKey
  accessorKey?: keyof TData,                       // literal key (no dot nesting)
  accessorFn?: (row: TData, index: number) => TValue,
  header?: string | ((ctx: HeaderContext) => ReactNode),
  footer?: string | ((ctx: HeaderContext) => ReactNode),
  cell?: ((ctx: CellContext) => ReactNode),        // default = getValue()
  meta?: Record<string, unknown>,                  // your custom payload
  enableSorting?: boolean,
  enableColumnFilter?: boolean,
  enableGlobalFilter?: boolean,
  enableHiding?: boolean,
  enableResizing?: boolean,
  size?: number,
  minSize?: number,
  maxSize?: number,
  sortingFn?: SortingFnOption,     // "alphanumeric" | "text" | "datetime" | "basic" | custom
  filterFn?: FilterFnOption,       // "auto" | "includesString" | "equals" | "arrIncludes" | "arrIncludesAll" | "inNumberRange" | custom
  sortDescFirst?: boolean,
  sortUndefined?: false | -1 | 1 | "first" | "last",
  columns?: ColumnDef[],           // for grouped/parent headers
}
```

**Return values** from `useReactTable` are stable across renders (the
`table` instance is the same reference), but the state inside it is
not — that's what `table.getState()` reads.

---

## Pagination Patterns

### Client-side (all data in memory)

```ts
useReactTable({
  data,                               // full array
  columns,
  getCoreRowModel: getCoreRowModel(),
  getPaginationRowModel: getPaginationRowModel(),
  initialState: { pagination: { pageSize: 25, pageIndex: 0 } },
});
```

The table slices `data` internally. `table.getRowModel().rows` returns
only the current page's rows.

### Server-side (manual mode)

```ts
const [pagination, setPagination] = useState<PaginationState>({
  pageIndex: 0, pageSize: 25,
});

const { data } = useQuery({
  queryKey: ["leads", pagination],
  queryFn: () => api.listLeads(pagination),
  placeholderData: keepPreviousData,   // keeps old page visible
});

const table = useReactTable({
  data: data?.rows ?? [],
  columns,
  pageCount: data?.pageCount ?? -1,    // -1 = unknown total
  // or (v8.13+): rowCount: data?.total ?? 0,
  state: { pagination },
  onPaginationChange: setPagination,
  manualPagination: true,
  getCoreRowModel: getCoreRowModel(),
  // NO getPaginationRowModel — server slices it
});
```

### Pagination controls

```tsx
<Button disabled={!table.getCanPreviousPage()} onClick={() => table.previousPage()}>
  Previous
</Button>
<span>Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount()}</span>
<Button disabled={!table.getCanNextPage()} onClick={() => table.nextPage()}>
  Next
</Button>
<Select value={String(table.getState().pagination.pageSize)}
  onValueChange={(v) => table.setPageSize(Number(v))}>
  {[10, 25, 50, 100].map((n) => <SelectItem key={n} value={String(n)}>{n}</SelectItem>)}
</Select>
```

### Cursor-based ("load more") pagination

Not a native pattern — TanStack Table is page-based. For cursor APIs
use `useInfiniteQuery` from React Query, flatten pages into `data`,
and set `manualPagination: true` + `pageCount: -1`. Render a
"Load more" button wired to `fetchNextPage()`, not to the table.

---

## Rate Limits

**N/A — client library, no network calls.** Throttling concerns are at
the *data source* layer (TanStack Query + your backend). If you
debounce a text filter, debounce the `onGlobalFilterChange` handler
(or the URL sync), not the table itself. Typical pattern:

```ts
const [raw, setRaw] = useState("");
const debounced = useDebouncedValue(raw, 250);
const table = useReactTable({
  state: { globalFilter: debounced },
  onGlobalFilterChange: setRaw,   // still write raw for input responsiveness
  ...
});
```

---

## Error Codes and Recovery

**N/A — no runtime errors from the table itself** in normal use. The
errors you will see in practice:

- **`TypeError: Cannot read properties of undefined (reading 'map')`**
  inside `flexRender` — means you passed `cell.getValue()` (a primitive)
  instead of `cell.column.columnDef.cell` (a renderer). Fix the call
  site.
- **`Invalid hook call`** — you destructured or called `useReactTable`
  conditionally, or you have two React copies in the bundle. Check
  `npm ls react`.
- **`"cannot update a component while rendering a different component"`**
  — you called `onPaginationChange` synchronously during render, likely
  because you wrote `state: { pagination: { pageIndex: 0, ... } }`
  (new object every render) without a setter. Always lift state.
- **Infinite re-render / "Maximum update depth exceeded"** — unstable
  `data` or `columns` reference. See Anti-Patterns.

Recovery is always the same: read the stack, find the render where a
new reference is created, memoize it.

---

## SDK Idioms

### Import only what you use

```ts
// Good — tree-shakes unused row models
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
```

### Column definition helper for strong typing

When generic inference fights you, use the `createColumnHelper`:

```ts
import { createColumnHelper } from "@tanstack/react-table";

const columnHelper = createColumnHelper<Lead>();

const columns = [
  columnHelper.accessor("name", {
    header: "Name",
    cell: (info) => info.getValue(),       // typed as string
  }),
  columnHelper.accessor((row) => row.user.email, {
    id: "email",
    header: "Email",
  }),
  columnHelper.display({
    id: "actions",
    cell: ({ row }) => <RowMenu lead={row.original} />,
  }),
];
```

The helper enforces `accessorKey`/`accessorFn`/`display` split at the
type level so you can't forget `id` on an accessor function.

### `flexRender` every cell and header

```tsx
{table.getHeaderGroups().map((hg) => (
  <TableRow key={hg.id}>
    {hg.headers.map((h) => (
      <TableHead key={h.id}>
        {h.isPlaceholder ? null : flexRender(h.column.columnDef.header, h.getContext())}
      </TableHead>
    ))}
  </TableRow>
))}
{table.getRowModel().rows.map((row) => (
  <TableRow key={row.id} data-state={row.getIsSelected() && "selected"}>
    {row.getVisibleCells().map((cell) => (
      <TableCell key={cell.id}>
        {flexRender(cell.column.columnDef.cell, cell.getContext())}
      </TableCell>
    ))}
  </TableRow>
))}
```

### Stable `getRowId` for selection

```ts
useReactTable({
  getRowId: (row) => row.id,   // your DB primary key
  ...
});
```

Without this, `rowSelection` keys are array indices, which change on
sort/filter, silently corrupting selection state.

### Column meta for shared UI info

```ts
{
  accessorKey: "status",
  header: "Status",
  meta: { align: "right", className: "tabular-nums" },
}

// In DataTable render:
<TableCell className={cell.column.columnDef.meta?.className}>
```

`meta` is typed as `any` by default — declare a module augmentation
once to get autocomplete:

```ts
// src/types/react-table.d.ts
import "@tanstack/react-table";
declare module "@tanstack/react-table" {
  interface ColumnMeta<TData, TValue> {
    align?: "left" | "right";
    className?: string;
  }
}
```

---

## Anti-Patterns

See `anti_patterns.md` for the full list with before/after code. The
top five:

1. **Inlining `columns` or `data` in JSX** — causes state resets.
2. **Using `accessorKey: "user.name"`** — doesn't traverse, use `accessorFn`.
3. **Skipping `getRowId`** — selection breaks on sort.
4. **Forgetting the row model for enabled state** — sort state updates, rows don't.
5. **Calling `flexRender(cell.getValue(), ...)`** — renders nothing useful.

---

## Data Model

### Entity hierarchy

```
Table
 └─ HeaderGroup[]          table.getHeaderGroups()
     └─ Header[]            headerGroup.headers
         └─ Column          header.column
 └─ RowModel                table.getRowModel()
     └─ Row[]               rowModel.rows
         └─ Cell[]          row.getVisibleCells()
             └─ Column      cell.column
         └─ subRows: Row[]  (when getSubRows is set)
 └─ Column[]                table.getAllColumns()
```

### Key relationships

- A `Header` can span multiple columns (grouped headers via
  `columns: [...]` nesting).
- A `Row` always belongs to exactly one parent `RowModel` but may
  appear in multiple derived models (core → filtered → sorted →
  paginated). Each model is a transformation of the previous.
- `Cell` is ephemeral — created per render from `row × visibleColumns`.
- `row.id` is the **stable identity**. Default is index-based
  (`"0"`, `"1"`, `"0.0"` for subrows). Override with `getRowId`.

### Field constraints

- `ColumnDef.id` is **required** unless `accessorKey` is set. For
  `accessorFn` and `display` columns, `id` is mandatory.
- `ColumnDef.id` must be unique within a table.
- `accessorKey` must be a literal top-level key of `TData` — no dot
  paths, no array indices.
- Column groups (parent headers) are declared by setting `columns` on
  a parent def; the parent itself has no accessor.

### Immutable vs mutable

- `data` should be treated as immutable (pass a new array to change it).
- `columns` should be treated as immutable (memoize).
- Table state (sorting, filters, etc.) is mutable via setters.

---

## Webhooks and Events

**N/A — no webhooks.** The event-like surface is the `onXChange`
callbacks. They are `OnChangeFn<T> = (updater: T | ((old: T) => T)) => void`,
compatible with React's `useState` setter signature, which is why you
can pass `setSorting` directly. For side effects on state change, wrap:

```ts
onSortingChange: (updater) => {
  setSorting((old) => {
    const next = typeof updater === "function" ? updater(old) : updater;
    analytics.track("table_sort", { columns: next });
    return next;
  });
}
```

---

## Limits

- **Rows in memory:** no hard limit, but render perf degrades past
  ~500 rows without virtualization. At 10k+ rows, virtualize with
  `@tanstack/react-virtual` or your UI will jank.
- **Columns:** no hard limit; 50+ columns starts to feel slow on
  column resize and faceted filter computation.
- **State shape:** any JSON-serializable data works. Don't put
  functions, class instances, or circular refs in `meta` or column
  defs — breaks devtools and URL sync.
- **`pageCount`:** use `-1` when unknown. The UI will disable the
  "last page" button and use `getCanNextPage()` based on whether the
  current page is full.
- **Max sort columns:** unlimited with `enableMultiSort: true`, but
  UX-wise keep it under 3.
- **Filter value size:** any serializable value; large blobs in
  `columnFilters` will bloat `queryKey` when you sync them to RQ.

---

## Cost Model

**N/A — free, MIT-licensed, client-only.** The "cost" is bundle size:

- `@tanstack/react-table` core: ~14 KB min+gzip
- Each opt-in row model: ~1–3 KB
- `@tanstack/react-virtual`: ~4 KB min+gzip

Tree-shaking is real — importing only `getCoreRowModel` adds the base;
other models only ship if you import them.

Runtime cost: O(rows) for filter/sort per state change. Memoize
`data` and `columns` aggressively and the engine will short-circuit.

---

## Version Pinning

- **Current major:** v8 (v8.0 released Dec 2022; v7 is the old
  `react-table` package with different API — do not mix).
- **Recommended pin:** `"@tanstack/react-table": "^8.17.0"` for
  `rowCount` support and refined faceted models.
- **v7 → v8 migration:** complete API change. v7 used hook composition
  (`useTable`, `useSortBy`, `useFilters`). v8 uses a single hook with
  opt-in row models. There is no incremental path — migrate a table at
  a time. Column def shape is also different (`Header` → `header`,
  `accessor` → `accessorKey`/`accessorFn`).
- **Upcoming v9:** in design as of 2026; no breaking changes announced,
  focus is on solid.js/vue adapter parity and perf. Watch the
  tanstack/table GitHub for the RFC.
- **Deprecations:** `keepPreviousData` is not a Table concept — it's
  a React Query v4 option that was removed in RQ v5. Use
  `placeholderData: keepPreviousData` or `placeholderData: (prev) => prev`
  in the RQ layer, not the table.

---

## Design Intent and Tradeoffs

Tanner Linsley built React Table v1–v6 as a traditional component
library, then rewrote it twice — first as v7 (hook composition), then
as v8 (headless, framework-agnostic, single hook). The key insight
between v7 and v8 was that **a table is a state engine, not a component**,
and that state engine should work the same in React, Solid, Vue, Svelte,
and even vanilla JS.

The explicit tradeoffs:

- **Headless over batteries-included.** Unlike AG Grid or MUI DataGrid,
  TanStack Table ships **zero** markup. You write the JSX. This is a
  deliberate rejection of the "customize via 200 props" approach —
  because when you hit the wall, those libraries force you to eject.
  Headless has no wall: the `table` instance is just state; render it
  however you want.

- **Tree-shakable row models.** v7 bundled everything; v8 makes each
  row model an explicit import. The verbosity is the point — you pay
  only for what you use, and the bundler can prove it.

- **Generic-first TypeScript.** `ColumnDef<TData, TValue>` is fully
  typed, but the value generic is often `any` by design because a
  column's value type depends on its accessor. The `createColumnHelper`
  exists precisely to recover that narrowing.

- **State, not events.** No `onRowClick`, no `onSortChange(old, new)`.
  The API is pure state: you pass `sorting` in, you read `sorting` out
  via `getState()`, you update it via `onSortingChange`. Events are
  your own.

- **Framework-agnostic core.** `@tanstack/table-core` is pure TS with
  zero React. `@tanstack/react-table` is a thin adapter (~200 lines)
  that runs the core in a `useState` + `useMemo` wrapper. That's why
  a Solid adapter ships the same features — the logic lives in core.

What the tool is explicitly NOT:
- **Not a component library.** No CSS, no theme, no "dark mode" prop.
- **Not a data fetching library.** Pair with TanStack Query.
- **Not a spreadsheet.** No formula engine, no cell editing primitives
  beyond `meta`. Use handsontable or grid.js for that.
- **Not opinionated about layout.** Fixed headers, sticky columns,
  horizontal scroll — all CSS concerns you own.

---

## Problem-Solution Map and Hidden Capabilities

**Problems this tool solves (beyond "render rows"):**

1. **"Our sort/filter/paginate state keeps drifting from the URL."**
   Controlled state + `onXChange` → URL sync in one place. The table
   is the source of truth; the URL is a projection.
2. **"Our leads list re-fetches every render."** Unstable `queryKey`
   from new filter objects. Fix at the React Query layer, but the
   table's state shape (arrays of plain objects) serializes cleanly.
3. **"Our DataTable component has 30 props."** Move feature toggles
   into `ColumnDef.meta` and into the table's options. Consumers pass
   columns + data, DataTable renders.
4. **"Row selection breaks after sorting."** `getRowId` with a stable
   PK. The fix is one line and almost nobody sets it until they're
   burned.
5. **"Our inline editing form state is a mess."** Don't put form state
   in the table. Use React Hook Form, one form per editing row, mount
   the form inside a `cell` renderer, scope with `row.id` as the key.

**Hidden / underdocumented capabilities:**

- **`getFacetedUniqueValues`** — produces a `Map<value, count>` of
  unique values per column *after filtering*. This is the shadcn
  faceted filter dropdown with counts — without it you'd recompute on
  every keystroke. Import and opt in, then `column.getFacetedUniqueValues()`
  is a Map ready to render.
- **`sortUndefined`** — controls where `undefined` values sort.
  Useful for "missing data last" UX.
- **`sortingFns` registry** — you can register custom sorting functions
  on the table root and reference them by name in column defs:
  `sortingFn: "myCustomSort"`.
- **Column sizing as CSS variables** — `table.getTotalSize()` and
  `column.getSize()` produce numbers. Feed them into a CSS variable:
  `style={{ "--col-width": `${column.getSize()}px` }}`. This is how
  shadcn's resizable column guide works.
- **`row.getLeafRows()` and `row.getParentRows()`** — for grouped
  tables, walk the hierarchy without tracking it yourself.
- **`table.setOptions(updater)`** — the imperative escape hatch to
  update options without re-creating the table. Rarely needed but
  useful for dynamic column generation.
- **`columnPinning`** — pin columns to left/right with `state.columnPinning`
  and render `header.column.getIsPinned()`. Combined with CSS
  `position: sticky`, gives you frozen columns.
- **`enableRowSelection` as a function** — per-row selection eligibility:
  `enableRowSelection: (row) => row.original.status !== "archived"`.
- **`globalFilterFn`** — custom global search that can search across
  any column, not just the default "includes" on strings.

---

## Operational Behavior and Edge Cases

- **StrictMode double render is safe.** The `table` instance is
  memoized internally, so StrictMode's double-invoke doesn't duplicate
  state. You can build in dev without fear — the bugs that show up in
  strict mode are bugs that would show up in production too (unstable
  refs, stale closures).

- **`initialState` vs `state` precedence.** If you pass both, `state`
  wins. `initialState` only applies on mount. Don't use both for the
  same field — pick one per field.

- **Pagination and filtering interaction.** When filters change,
  the current `pageIndex` can become out-of-range (you were on page 5
  of 10, now there are only 2 pages). The table does **not** auto-reset
  to page 0; you must do it in your filter change handler:
  ```ts
  onColumnFiltersChange: (u) => {
    setColumnFilters(u);
    setPagination((p) => ({ ...p, pageIndex: 0 }));
  }
  ```

- **Sorting stability.** The default `alphanumeric` sorting is
  stable (rows that compare equal keep their relative order). If you
  write a custom `sortingFn`, preserve stability or multi-sort breaks.

- **Faceted facets on huge datasets.** `getFacetedUniqueValues` runs
  over every row in the filtered model. At 50k+ rows this stutters on
  filter typing. Solutions: debounce filter input, compute facets on
  the server, or use `getFacetedUniqueValues` only on columns that
  actually need the dropdown.

- **Row IDs with duplicates.** If your `getRowId` returns the same
  value for two rows, React will warn about duplicate keys and
  selection/expansion behavior becomes undefined. Always return a
  unique id.

- **`manualFiltering: true` but you still opt in `getFilteredRowModel`.**
  Valid and useful: the table will skip the filtering transform but
  still expose a "filtered" model identical to the core model. Usually
  you should **omit** the row model when `manualX: true` — no runtime
  error, just a wasted import.

- **Column resize events fire on every pixel.** Set
  `columnResizeMode: "onEnd"` unless you need live width updates,
  otherwise the table re-renders 60 times a second during drag.

- **Expanded state with async sub-rows.** `getSubRows` is sync. If you
  want to lazy-load children, store a placeholder in `row.original`
  and fetch in a `useEffect` keyed on `row.getIsExpanded()`. Write
  the loaded children back to the source array (immutably) and the
  table will re-render them.

- **Virtualization + sticky headers.** The virtualizer scrolls the
  body element; your `<thead>` must be sticky via CSS
  (`position: sticky; top: 0`) or it scrolls away. This is a layout
  concern, not a table concern.

---

## Ecosystem Position and Composition

**Where it sits:** the **state layer** between your data source
(TanStack Query, Apollo, raw fetch) and your markup layer (shadcn,
plain HTML, headlessui, etc.). It is the middleware, not the
endpoint.

**Natural complements:**
- **TanStack Query** — same author, same philosophy. Query for data,
  Table for display state. The two integrate seamlessly via manual
  pagination and `placeholderData`.
- **TanStack Virtual** — required above ~500 rows, same author,
  designed to compose with Table's row model.
- **shadcn/ui DataTable** — the canonical React render layer. Ships as
  copy-paste components in `components/ui/data-table/*`. Uses
  `flexRender`, Radix primitives under the hood.
- **Zod** — type the row data, infer `TData`, type the columns.
- **React Hook Form** — inline editing without coupling table state
  to form state.
- **Tailwind** — zero CSS conflicts because Table ships no CSS.
- **nuqs / URL state libs** — sync `sorting`, `columnFilters`,
  `pagination` to the URL for shareable views.

**Forced / anti-complements:**
- **Redux for table state.** Don't. Table already owns it. Using
  Redux duplicates the truth and invites stale bugs.
- **MUI DataGrid + TanStack Table** — they are competitors. Pick one
  per page; mixing gives you two state engines fighting over rendering.
- **AG Grid + TanStack Table** — same story. AG Grid is a fortress;
  Table is a scaffold. Don't wedge them together.
- **Form libraries for whole-table editing.** The "spreadsheet" UX
  is a different problem. Tools: handsontable, glide-data-grid,
  react-data-grid (the `adazzle` one).

**Data handoff patterns:**
- **Fetch → transform → Zod parse → Table.** Parse once at the fetch
  boundary; the table sees already-typed data.
- **Table state → URL → React Query key.** Serialize table state as
  search params, react to changes, pass into `queryKey`. The flow is
  unidirectional: URL ← table state ← user action.
- **Selection → batch action.** `table.getSelectedRowModel().rows.map(r => r.original.id)`
  → pass to a `useMutation` → invalidate the list query on success.

---

## Trajectory and Evolution

- **v8 is stable and in maintenance mode as of 2026.** Tanner Linsley
  and the TanStack team are focused on Query, Router, and Form — Table
  is "done enough" for v8 and receives bug fixes and perf PRs.
- **New in v8.13+:** `rowCount` option as a more intuitive alternative
  to `pageCount`. If you know the total rows, pass `rowCount` and the
  table derives `pageCount`.
- **New in v8.17+:** refined faceted value computation caching,
  smaller `getFacetedUniqueValues` hot path.
- **v9 in design:** no RFC published; focus is adapter parity (Solid,
  Vue, Svelte, Lit, Angular, Qwik all at or near parity) and shrinking
  the core further. No breaking API changes signaled.
- **Deprecation signals:** none for v8. The old v7 `react-table`
  package is the dead branch — do not start a new project on it.
- **Community patterns adopted:** the shadcn DataTable composition
  pattern, `createColumnHelper` for type ergonomics, and
  `placeholderData: keepPreviousData` for pagination all originated
  in the community and are now canonical in the docs.
- **Future-leaning features to watch:** columnPinning is getting
  better ergonomics, virtualizer hooks may move closer to Table's
  row model API.

**What to build on confidently:** the `useReactTable` API surface is
stable, the row model pattern is stable, `flexRender` is stable,
`ColumnDef` shape is stable.

**What to avoid:** custom sorting function registries on the root
(rarely needed, harder to type). `setOptions` imperative updates
(brittle, prefer state).

---

## Conceptual Model and Solution Recipes

### The mental model

Think of a table as a **function**:
`(data, columns, state) → (rows to render, headers to render)`

The function is pure. The state is controlled. The render is yours.

### Recipe 1: Paginated, sortable, filterable leads list (client-side)

1. Define `leadColumns: ColumnDef<Lead>[]` at module scope with
   `createColumnHelper`.
2. Fetch all leads via `useQuery({ queryKey: ["leads"], queryFn: fetchAll })`.
3. `useState` for `sorting`, `columnFilters`, `pagination`.
4. `useReactTable` with all three row models
   (`Core`, `Sorted`, `Filtered`, `Paginated`).
5. Render with shadcn `<DataTable>`.
6. Reset `pageIndex` to 0 in the filter change handler.

### Recipe 2: Server-driven leads list (10k+ rows)

1. Same column defs.
2. `useQuery` with `queryKey: ["leads", { pagination, sorting, filters }]`
   and `placeholderData: keepPreviousData`.
3. Backend returns `{ rows, pageCount, total }`.
4. `useReactTable` with `manualPagination`, `manualSorting`,
   `manualFiltering`, `pageCount: data?.pageCount ?? -1`, and ONLY
   `getCoreRowModel`.
5. Pagination controls via `table.previousPage()` / `nextPage()`.
6. Loading indicator gated on `isFetching && !isPlaceholderData`.

### Recipe 3: Bulk archive selected rows

1. Add a checkbox column with `id: "select"` using
   `row.getIsSelected()` / `row.toggleSelected()`.
2. Set `getRowId: (row) => row.id`.
3. Toolbar button reads `table.getSelectedRowModel().rows`.
4. `useMutation` to archive, `onSuccess` → `table.resetRowSelection()`
   + `qc.invalidateQueries({ queryKey: ["leads"] })`.

### Recipe 4: Virtualized 100k-row audit log

1. Fetch rows in chunks via `useInfiniteQuery`, flatten into `data`.
2. `useReactTable` with only `getCoreRowModel`.
3. Render body with `useVirtualizer` over
   `table.getRowModel().rows`.
4. On scroll to bottom, call `fetchNextPage()`.
5. Estimate row size accurately (use `measureElement`).

### Recipe 5: URL-synced filters and sort

1. Use `nuqs` or `useSearchParams` for `sorting`, `columnFilters`,
   `pagination`.
2. `useReactTable` with those as `state` and the `onXChange`
   handlers writing to the URL.
3. The URL is the source of truth — refresh preserves the view.

---

## Industry Expert and Cutting-Edge Usage

- **Shadcn/ui's DataTable pattern** (shadcn, 2023) canonicalized the
  headless + copy-paste approach. Every serious React SaaS in 2025–26
  uses some variant of this. The pattern is: generic `DataTable` owns
  the render, features compose by passing column defs.

- **Linear-style command-palette filters** — faceted filters rendered
  as a command menu rather than dropdowns. Powered by
  `getFacetedUniqueValues` + `cmdk`. Gives users type-to-filter across
  every column value in one input.

- **Airtable-style inline editing with RHF per row.** Each editing row
  mounts its own `useForm` scoped to `row.id`, saves via
  `useMutation`, reverts optimistic UI on error. No global form state.

- **URL-first tables (nuqs + TanStack Table).** The URL is the table's
  state container. Sorting, filters, pagination, selected row detail
  — all in search params. Refresh = same view. Shareable by copy.

- **Streaming rows via SSE + table re-render.** Push new rows into a
  React Query cache via `qc.setQueryData(key, (old) => [...old, row])`.
  The table re-renders automatically because `data` is the cache. Used
  for live dashboards (message feeds, job queues, analytics tickers).

- **AI-assisted column generation.** Feed a Zod schema into an LLM,
  get a `ColumnDef[]` with sensible defaults (date columns get
  `sortingFn: "datetime"`, enum fields get faceted filters). The
  `createColumnHelper` + `Schema.shape` inspection makes this
  deterministic — the `plugin_skill_audit` meta-skill could template
  it.

- **Server components (Next.js App Router) + Table.** Table is a
  client component by necessity (it holds state), but the row data
  can be fetched in a server component and passed as a serialized
  prop. Pair with TanStack Query's hydration for dynamic updates.

- **Composing with TanStack Router for type-safe URL-synced state.**
  TanStack Router's search param validation + Table's state shape
  gives end-to-end type safety from URL → table → render.

---

## Sources

- https://tanstack.com/table/latest/docs/introduction
- https://tanstack.com/table/latest/docs/guide/column-defs
- https://tanstack.com/table/latest/docs/guide/row-models
- https://tanstack.com/table/latest/docs/guide/pagination
- https://tanstack.com/table/latest/docs/guide/sorting
- https://tanstack.com/table/latest/docs/guide/column-filtering
- https://tanstack.com/table/latest/docs/guide/row-selection
- https://tanstack.com/table/latest/docs/guide/virtualization
- https://ui.shadcn.com/docs/components/data-table
- https://tanstack.com/virtual/latest
- https://github.com/TanStack/table (issues for edge cases)
