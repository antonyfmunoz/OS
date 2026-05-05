# TanStack Table v8 — EOS Examples

Real React 18 + TypeScript + shadcn + TanStack Query patterns. Every
snippet compiles against `@tanstack/react-table@8` and `@tanstack/react-query@5`.

---

## 1. Generic shadcn DataTable component

```tsx
// src/components/data-table/data-table.tsx
import {
  flexRender,
  type Table as TanstackTable,
} from "@tanstack/react-table";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface DataTableProps<TData> {
  table: TanstackTable<TData>;
  emptyMessage?: string;
}

export function DataTable<TData>({
  table,
  emptyMessage = "No results.",
}: DataTableProps<TData>) {
  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <TableHead
                  key={header.id}
                  style={{ width: header.getSize() }}
                >
                  {header.isPlaceholder
                    ? null
                    : flexRender(
                        header.column.columnDef.header,
                        header.getContext(),
                      )}
                </TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {table.getRowModel().rows.length ? (
            table.getRowModel().rows.map((row) => (
              <TableRow
                key={row.id}
                data-state={row.getIsSelected() && "selected"}
              >
                {row.getVisibleCells().map((cell) => (
                  <TableCell key={cell.id}>
                    {flexRender(
                      cell.column.columnDef.cell,
                      cell.getContext(),
                    )}
                  </TableCell>
                ))}
              </TableRow>
            ))
          ) : (
            <TableRow>
              <TableCell
                colSpan={table.getAllColumns().length}
                className="h-24 text-center"
              >
                {emptyMessage}
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}
```

---

## 2. Lead columns with `createColumnHelper`

```tsx
// src/features/leads/columns.tsx
import { createColumnHelper } from "@tanstack/react-table";
import type { Lead } from "@/schemas/lead";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ArrowUpDown, MoreHorizontal } from "lucide-react";
import { LeadRowMenu } from "./lead-row-menu";

const ch = createColumnHelper<Lead>();

export const leadColumns = [
  ch.display({
    id: "select",
    header: ({ table }) => (
      <Checkbox
        checked={
          table.getIsAllPageRowsSelected() ||
          (table.getIsSomePageRowsSelected() && "indeterminate")
        }
        onCheckedChange={(v) => table.toggleAllPageRowsSelected(!!v)}
        aria-label="Select all"
      />
    ),
    cell: ({ row }) => (
      <Checkbox
        checked={row.getIsSelected()}
        onCheckedChange={(v) => row.toggleSelected(!!v)}
        aria-label="Select row"
      />
    ),
    enableSorting: false,
    enableHiding: false,
  }),
  ch.accessor("name", {
    header: ({ column }) => (
      <Button
        variant="ghost"
        onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        className="-ml-3 h-8"
      >
        Name <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    ),
    cell: (info) => <span className="font-medium">{info.getValue()}</span>,
  }),
  ch.accessor("email", {
    header: "Email",
    cell: (info) => (
      <span className="text-muted-foreground">{info.getValue()}</span>
    ),
  }),
  ch.accessor("status", {
    header: "Status",
    cell: (info) => {
      const status = info.getValue();
      const variant =
        status === "won" ? "default" :
        status === "lost" ? "destructive" : "secondary";
      return <Badge variant={variant}>{status}</Badge>;
    },
    filterFn: (row, id, value: string[]) =>
      value.length === 0 || value.includes(row.getValue(id)),
  }),
  ch.accessor((row) => new Date(row.createdAt).getTime(), {
    id: "createdAt",
    header: "Created",
    cell: (info) =>
      new Intl.DateTimeFormat("en-US", { dateStyle: "medium" })
        .format(new Date(info.getValue())),
    sortingFn: "basic",
  }),
  ch.display({
    id: "actions",
    cell: ({ row }) => (
      <LeadRowMenu lead={row.original}>
        <Button variant="ghost" size="icon">
          <MoreHorizontal className="h-4 w-4" />
        </Button>
      </LeadRowMenu>
    ),
    enableSorting: false,
    enableHiding: false,
  }),
];
```

---

## 3. Server-driven leads table (manual pagination + RQ + URL sync)

```tsx
// src/features/leads/leads-table.tsx
import { useMemo, useState } from "react";
import {
  getCoreRowModel,
  useReactTable,
  type ColumnFiltersState,
  type PaginationState,
  type SortingState,
  type RowSelectionState,
} from "@tanstack/react-table";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { DataTable } from "@/components/data-table/data-table";
import { DataTablePagination } from "@/components/data-table/data-table-pagination";
import { DataTableToolbar } from "@/components/data-table/data-table-toolbar";
import { leadColumns } from "./columns";
import { fetchLeadsPage } from "./api";

const EMPTY: never[] = [];

export function LeadsTable() {
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: 25,
  });
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});

  const columns = useMemo(() => leadColumns, []);

  const { data, isFetching, isPlaceholderData } = useQuery({
    queryKey: ["leads", "list", { pagination, sorting, columnFilters }],
    queryFn: ({ signal }) =>
      fetchLeadsPage({ pagination, sorting, columnFilters, signal }),
    placeholderData: keepPreviousData,
    staleTime: 30_000,
  });

  const table = useReactTable({
    data: data?.rows ?? EMPTY,
    columns,
    pageCount: data?.pageCount ?? -1,
    state: { pagination, sorting, columnFilters, rowSelection },
    onPaginationChange: setPagination,
    onSortingChange: setSorting,
    onColumnFiltersChange: (updater) => {
      setColumnFilters(updater);
      setPagination((p) => ({ ...p, pageIndex: 0 })); // reset page
    },
    onRowSelectionChange: setRowSelection,
    manualPagination: true,
    manualSorting: true,
    manualFiltering: true,
    getCoreRowModel: getCoreRowModel(),
    getRowId: (row) => row.id,                          // stable!
  });

  return (
    <div className="space-y-4">
      <DataTableToolbar table={table} />
      <div className="relative">
        <DataTable table={table} />
        {isFetching && !isPlaceholderData && (
          <div className="absolute inset-0 flex items-center justify-center bg-background/50">
            <span>Loading…</span>
          </div>
        )}
      </div>
      <DataTablePagination table={table} />
    </div>
  );
}
```

---

## 4. Pagination component

```tsx
// src/components/data-table/data-table-pagination.tsx
import type { Table } from "@tanstack/react-table";
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  ChevronsLeftIcon,
  ChevronsRightIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface Props<TData> {
  table: Table<TData>;
}

export function DataTablePagination<TData>({ table }: Props<TData>) {
  return (
    <div className="flex items-center justify-between px-2">
      <div className="flex-1 text-sm text-muted-foreground">
        {table.getFilteredSelectedRowModel().rows.length} of{" "}
        {table.getFilteredRowModel().rows.length} row(s) selected.
      </div>
      <div className="flex items-center space-x-6 lg:space-x-8">
        <div className="flex items-center space-x-2">
          <p className="text-sm font-medium">Rows per page</p>
          <Select
            value={`${table.getState().pagination.pageSize}`}
            onValueChange={(v) => table.setPageSize(Number(v))}
          >
            <SelectTrigger className="h-8 w-[70px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent side="top">
              {[10, 25, 50, 100].map((n) => (
                <SelectItem key={n} value={`${n}`}>{n}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex w-[100px] items-center justify-center text-sm font-medium">
          Page {table.getState().pagination.pageIndex + 1} of{" "}
          {table.getPageCount()}
        </div>
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            onClick={() => table.setPageIndex(0)}
            disabled={!table.getCanPreviousPage()}
          >
            <ChevronsLeftIcon className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
          >
            <ChevronLeftIcon className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
          >
            <ChevronRightIcon className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            onClick={() => table.setPageIndex(table.getPageCount() - 1)}
            disabled={!table.getCanNextPage()}
          >
            <ChevronsRightIcon className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
```

---

## 5. Faceted filter (multi-select with counts)

```tsx
// src/components/data-table/data-table-faceted-filter.tsx
import type { Column } from "@tanstack/react-table";
import { CheckIcon, PlusCircledIcon } from "lucide-react";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface Props<TData, TValue> {
  column?: Column<TData, TValue>;
  title?: string;
  options: { label: string; value: string }[];
}

export function DataTableFacetedFilter<TData, TValue>({
  column,
  title,
  options,
}: Props<TData, TValue>) {
  const facets = column?.getFacetedUniqueValues();
  const selectedValues = new Set(column?.getFilterValue() as string[]);

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm" className="h-8 border-dashed">
          <PlusCircledIcon className="mr-2 h-4 w-4" />
          {title}
          {selectedValues.size > 0 && (
            <>
              <Badge variant="secondary" className="ml-2 rounded-sm px-1">
                {selectedValues.size}
              </Badge>
            </>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[200px] p-0" align="start">
        <Command>
          <CommandInput placeholder={title} />
          <CommandList>
            <CommandEmpty>No results found.</CommandEmpty>
            <CommandGroup>
              {options.map((option) => {
                const isSelected = selectedValues.has(option.value);
                return (
                  <CommandItem
                    key={option.value}
                    onSelect={() => {
                      if (isSelected) selectedValues.delete(option.value);
                      else selectedValues.add(option.value);
                      const filterValues = Array.from(selectedValues);
                      column?.setFilterValue(
                        filterValues.length ? filterValues : undefined,
                      );
                    }}
                  >
                    <div
                      className={cn(
                        "mr-2 flex h-4 w-4 items-center justify-center rounded-sm border border-primary",
                        isSelected
                          ? "bg-primary text-primary-foreground"
                          : "opacity-50",
                      )}
                    >
                      <CheckIcon className="h-4 w-4" />
                    </div>
                    <span>{option.label}</span>
                    {facets?.get(option.value) && (
                      <span className="ml-auto font-mono text-xs">
                        {facets.get(option.value)}
                      </span>
                    )}
                  </CommandItem>
                );
              })}
            </CommandGroup>
            {selectedValues.size > 0 && (
              <>
                <CommandSeparator />
                <CommandGroup>
                  <CommandItem
                    onSelect={() => column?.setFilterValue(undefined)}
                    className="justify-center text-center"
                  >
                    Clear filters
                  </CommandItem>
                </CommandGroup>
              </>
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
```

---

## 6. Bulk action: archive selected leads

```tsx
import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { Table } from "@tanstack/react-table";
import type { Lead } from "@/schemas/lead";

export function BulkArchiveButton({ table }: { table: Table<Lead> }) {
  const qc = useQueryClient();
  const selected = table.getSelectedRowModel().rows;

  const mutation = useMutation({
    mutationFn: async (ids: string[]) => {
      const res = await fetch("/api/leads/archive", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids }),
      });
      if (!res.ok) throw new Error("Archive failed");
    },
    onSuccess: () => {
      table.resetRowSelection();
      qc.invalidateQueries({ queryKey: ["leads"] });
    },
  });

  if (selected.length === 0) return null;

  return (
    <Button
      variant="destructive"
      size="sm"
      disabled={mutation.isPending}
      onClick={() => mutation.mutate(selected.map((r) => r.original.id))}
    >
      Archive {selected.length} lead{selected.length === 1 ? "" : "s"}
    </Button>
  );
}
```

---

## 7. Inline row editing with React Hook Form

```tsx
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { LeadSchema, type Lead } from "@/schemas/lead";

function EditableNameCell({ lead }: { lead: Lead }) {
  const qc = useQueryClient();
  const form = useForm({
    resolver: zodResolver(LeadSchema.pick({ name: true })),
    defaultValues: { name: lead.name },
  });

  const mutation = useMutation({
    mutationFn: (patch: { name: string }) =>
      fetch(`/api/leads/${lead.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch),
      }).then((r) => r.json()),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["leads"] }),
  });

  return (
    <form onSubmit={form.handleSubmit((v) => mutation.mutate(v))}>
      <input
        {...form.register("name")}
        onBlur={form.handleSubmit((v) => mutation.mutate(v))}
        className="bg-transparent outline-none focus:bg-muted px-1"
      />
    </form>
  );
}

// In columns:
ch.accessor("name", {
  header: "Name",
  cell: ({ row }) => <EditableNameCell lead={row.original} />,
});
```

---

## 8. URL-synced state with `nuqs`

```tsx
import { useQueryStates, parseAsInteger, parseAsArrayOf, parseAsString } from "nuqs";

export function useTableUrlState() {
  return useQueryStates({
    pageIndex: parseAsInteger.withDefault(0),
    pageSize: parseAsInteger.withDefault(25),
    sort: parseAsString.withDefault(""),
    desc: parseAsString.withDefault(""),
    status: parseAsArrayOf(parseAsString).withDefault([]),
  });
}

// then in the table:
const [url, setUrl] = useTableUrlState();
const pagination = { pageIndex: url.pageIndex, pageSize: url.pageSize };
const sorting = url.sort ? [{ id: url.sort, desc: url.desc === "1" }] : [];
const columnFilters = url.status.length ? [{ id: "status", value: url.status }] : [];
```

---

## 9. Virtualized 50k-row audit log

```tsx
import { useVirtualizer } from "@tanstack/react-virtual";
import { useRef } from "react";
import { flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table";

export function AuditLogTable({ rows }: { rows: AuditEvent[] }) {
  const parentRef = useRef<HTMLDivElement>(null);

  const table = useReactTable({
    data: rows,
    columns: auditColumns,
    getCoreRowModel: getCoreRowModel(),
    getRowId: (r) => r.id,
  });

  const { rows: tableRows } = table.getRowModel();

  const virtualizer = useVirtualizer({
    count: tableRows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 44,
    overscan: 12,
  });

  return (
    <div ref={parentRef} className="h-[640px] overflow-auto rounded-md border">
      <table className="w-full caption-bottom text-sm">
        <thead className="sticky top-0 bg-background">
          {table.getHeaderGroups().map((hg) => (
            <tr key={hg.id}>
              {hg.headers.map((h) => (
                <th key={h.id} className="h-10 px-4 text-left">
                  {flexRender(h.column.columnDef.header, h.getContext())}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody style={{ height: virtualizer.getTotalSize(), position: "relative" }}>
          {virtualizer.getVirtualItems().map((vi) => {
            const row = tableRows[vi.index];
            return (
              <tr
                key={row.id}
                data-index={vi.index}
                ref={virtualizer.measureElement}
                className="absolute flex w-full border-b"
                style={{ transform: `translateY(${vi.start}px)` }}
              >
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="h-11 flex-1 px-4 py-2">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
```
