# TanStack Table v8 — Integrations

How `@tanstack/react-table` composes with the rest of the EOS SaaS stack.

---

## React 18 (and 19)

- Table state is just `useState` under the hood. StrictMode-safe in
  React 18; React 19 compatible (no concurrent rendering pitfalls).
- The `table` instance returned from `useReactTable` is stable per
  render — pass it freely to children without `useMemo`.
- React 19's `useActionState` does NOT replace table state. Forms
  embedded in cells still use React Hook Form; the table itself
  remains controlled via `useState`.

---

## TypeScript

- Always parameterize: `ColumnDef<TData, TValue>`, `Table<TData>`,
  `Row<TData>`. Never `ColumnDef<any>`.
- Use `createColumnHelper<TData>()` to get narrower per-column types
  (the helper distinguishes accessor / accessorFn / display columns
  at the type level).
- Augment `ColumnMeta` once in a `.d.ts`:
  ```ts
  import "@tanstack/react-table";
  declare module "@tanstack/react-table" {
    interface ColumnMeta<TData, TValue> {
      align?: "left" | "right" | "center";
      className?: string;
      filterVariant?: "text" | "select" | "range";
    }
  }
  ```
- Type the row data with Zod's `z.infer<typeof Schema>` so columns,
  the API response, and the form schemas all share one source.

---

## shadcn/ui

The shadcn DataTable pattern is the canonical render layer for
TanStack Table in React. Composition map:

| TanStack Table primitive       | shadcn component        |
|--------------------------------|-------------------------|
| `table.getHeaderGroups()`      | `<Table>` + `<TableHeader>` + `<TableRow>` + `<TableHead>` |
| `table.getRowModel().rows`     | `<TableBody>` + `<TableRow>` + `<TableCell>` |
| `flexRender`                   | inside each `<TableHead>` / `<TableCell>` |
| `column.getCanSort()`          | `<Button variant="ghost">` with `ArrowUpDown` icon |
| `column.getFacetedUniqueValues()` | `<Popover>` + `<Command>` (faceted filter) |
| `table.getAllColumns()` + `column.getCanHide()` | `<DropdownMenu>` (view options) |
| `table.previousPage() / nextPage()` | `<Button>` icons in pagination bar |
| `row.getIsSelected()` / `toggleSelected()` | `<Checkbox>` |

The shadcn DataTable is **copy-paste**: you own the file, you customize
freely. Don't try to npm-install it.

---

## TanStack React Query

The intended pairing. Patterns:

### Client-side (small lists)

```ts
const { data = EMPTY } = useQuery({ queryKey: ["leads"], queryFn: fetchAll });
useReactTable({ data, columns, getCoreRowModel: getCoreRowModel(), getSortedRowModel: getSortedRowModel(), getFilteredRowModel: getFilteredRowModel(), getPaginationRowModel: getPaginationRowModel() });
```

### Server-driven (large lists)

```ts
useQuery({
  queryKey: ["leads", { pagination, sorting, columnFilters }],
  queryFn: () => fetchPage({ pagination, sorting, columnFilters }),
  placeholderData: keepPreviousData,
});
useReactTable({
  data: data?.rows ?? EMPTY,
  columns,
  pageCount: data?.pageCount ?? -1,
  manualPagination: true,
  manualSorting: true,
  manualFiltering: true,
  state: { pagination, sorting, columnFilters },
  onPaginationChange: setPagination,
  onSortingChange: setSorting,
  onColumnFiltersChange: setColumnFilters,
  getCoreRowModel: getCoreRowModel(),
});
```

Critical: `placeholderData: keepPreviousData` keeps the previous page
visible so pagination doesn't flicker.

### Mutations + invalidation

```ts
const mutation = useMutation({
  mutationFn: archiveLeads,
  onSuccess: () => {
    table.resetRowSelection();
    return qc.invalidateQueries({ queryKey: ["leads"] });
  },
});
```

---

## TanStack React Virtual

For tables over ~500 rows. The virtualizer doesn't know about Table —
it just virtualizes the row array Table produces.

```ts
const rows = table.getRowModel().rows;
const virtualizer = useVirtualizer({
  count: rows.length,
  getScrollElement: () => parentRef.current,
  estimateSize: () => 44,
  overscan: 10,
});
```

Render the rows from `virtualizer.getVirtualItems()` with absolute
positioning + a spacer div the height of `getTotalSize()`. Use
`virtualizer.measureElement` for dynamic row heights.

Sticky headers: CSS `position: sticky; top: 0` on `<thead>`.

---

## Zod

```ts
export const LeadSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1),
  email: z.string().email(),
  status: z.enum(["new", "qualified", "won", "lost"]),
  createdAt: z.string().datetime(),
});
export type Lead = z.infer<typeof LeadSchema>;

// queryFn parses, table consumes already-typed data
const lead = LeadSchema.parse(await res.json());

// columns are fully typed
const columns: ColumnDef<Lead>[] = [...]
```

---

## React Hook Form

For inline editing one row at a time:

```tsx
function EditableNameCell({ lead }: { lead: Lead }) {
  const form = useForm({
    resolver: zodResolver(LeadSchema.pick({ name: true })),
    defaultValues: { name: lead.name },
  });
  // mount inside a column cell renderer
}
```

For batch edits, use one form per row, never one form for the whole
table — RHF doesn't compose that way and you'll fight stale closures.

---

## Tailwind CSS

Table ships zero CSS, so Tailwind is unconstrained. Patterns:

- Row hover: `hover:bg-muted/50`
- Selected: shadcn `<TableRow>` reads `data-state="selected"` →
  styled via `data-[state=selected]:bg-muted` in the component.
- Tabular numerals for status / amount columns:
  `meta: { className: "tabular-nums text-right" }` then read in cell.
- Sticky first column: `sticky left-0 bg-background z-10` on the cell.

---

## Wouter / TanStack Router / nuqs (URL state)

Sync `sorting`, `columnFilters`, `pagination` to URL search params so
views are shareable and refresh-safe.

With `nuqs`:

```ts
const [url, setUrl] = useQueryStates({
  page: parseAsInteger.withDefault(0),
  size: parseAsInteger.withDefault(25),
  sort: parseAsString.withDefault(""),
  desc: parseAsBoolean.withDefault(false),
});

const pagination = { pageIndex: url.page, pageSize: url.size };
const sorting = url.sort ? [{ id: url.sort, desc: url.desc }] : [];

useReactTable({
  state: { pagination, sorting },
  onPaginationChange: (u) => {
    const next = typeof u === "function" ? u(pagination) : u;
    setUrl({ page: next.pageIndex, size: next.pageSize });
  },
  onSortingChange: (u) => {
    const next = typeof u === "function" ? u(sorting) : u;
    setUrl({ sort: next[0]?.id ?? "", desc: !!next[0]?.desc });
  },
  ...
});
```

With TanStack Router, use route search param validation for the same
shape; the router gives you full type safety end-to-end.

---

## Express + Drizzle backend (EOS SaaS pattern)

Server-side pagination/sorting/filtering contract:

```ts
// Request
GET /api/leads?page=0&size=25&sort=name&desc=false&status=new&status=qualified

// Response
{
  rows: Lead[],
  pageCount: number,
  total: number
}
```

In Drizzle:

```ts
const where = and(
  filters.status?.length ? inArray(leads.status, filters.status) : undefined,
  filters.q ? ilike(leads.name, `%${filters.q}%`) : undefined,
);

const [rows, [{ count }]] = await Promise.all([
  db.select().from(leads).where(where)
    .orderBy(sort === "name" ? (desc ? descFn(leads.name) : asc(leads.name)) : asc(leads.id))
    .limit(size).offset(page * size),
  db.select({ count: sql<number>`count(*)::int` }).from(leads).where(where),
]);

return { rows, total: count, pageCount: Math.ceil(count / size) };
```

The frontend table state shape (`PaginationState`, `SortingState`,
`ColumnFiltersState`) maps almost 1:1 to query params, which maps
1:1 to the SQL query. Three layers, one shape.
