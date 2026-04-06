# shadcn/ui — Stack Integrations

How shadcn/ui composes with the EOS frontend stack. Every section is
a tested pattern, not a theoretical combination.

---

## React 18 + TypeScript strict

- Every vendored component is `.tsx` with proper `React.forwardRef`
  and `displayName`. TS strict mode catches missing `asChild` prop
  types and wrong variant values.
- `VariantProps<typeof buttonVariants>` gives you exhaustive variant
  autocomplete in IDE.
- React 19 requires `--legacy-peer-deps` until all Radix packages
  update their peer dep range. Pin React 18.3.x for EOS until then.

---

## Vite

- Works out-of-box. `components.json.framework` is inferred.
- Vite's path alias MUST mirror `components.json.aliases`. Either
  set `resolve.alias` in `vite.config.ts` OR install
  `vite-tsconfig-paths`.
- `index.css` (Vite convention) instead of `app/globals.css` (Next
  convention) — set in `components.json.tailwind.css`.
- HMR works perfectly with shadcn's forwardRef components; no extra
  config needed.

---

## Tailwind CSS

- Required. shadcn/ui has no styles of its own.
- `content` paths MUST include your `src/components/ui/**` glob,
  otherwise tree-shaking kills component classes.
- `darkMode: ["class"]` is the canonical setting.
- `tailwindcss-animate` plugin is required for Radix animations
  (Dialog open/close, Popover fade). The CLI installs it on `init`.
- Tailwind v4 (new CSS-first engine) is supported by the latest
  shadcn CLI — `@theme` directive replaces `tailwind.config.ts`.
  EOS is on v3.4.x; migrate when ready.

---

## React Hook Form + Zod

The canonical pairing. shadcn ships `<Form>` primitives specifically
to wrap RHF's `<Controller>`.

```tsx
const form = useForm<Values>({
  resolver: zodResolver(schema),
  defaultValues: { /* every field */ },
  mode: "onBlur",  // validate on blur, not every keystroke
});
```

- `<Form {...form}>` = `<FormProvider>`.
- `<FormField>` = `<Controller>` + context for ids.
- `<FormControl>` uses Radix `<Slot>` with `asChild` to inject `id`,
  `aria-describedby`, `aria-invalid` onto your input.
- One Zod schema can drive: RHF validation, TS types via `z.infer`,
  API payload shape, and (paired with Drizzle) DB insert shape.

---

## React Query (TanStack Query)

Pair with shadcn for async state:

- **Mutations + Dialogs:** control `open` state from the parent;
  close in `onSuccess`.
- **Mutations + sonner:** use `toast.promise(mutation.mutateAsync(...))`
  for loading/success/error in one call.
- **Tables + Pagination:** use `manualPagination: true` in TanStack
  Table and drive page state into a React Query `queryKey`.
  `placeholderData: keepPreviousData` prevents table flicker.
- **Suspense mode:** `useSuspenseQuery` + shadcn `<Skeleton>`
  fallback = zero boilerplate loading states.

```tsx
const { data } = useSuspenseQuery({ queryKey: ["leads"], queryFn: fetchLeads });
// Wrap route in <Suspense fallback={<LeadsSkeleton />}>
```

---

## sonner (toast)

Current recommendation over legacy `useToast`.

```bash
npx shadcn@latest add sonner
```
```tsx
// src/main.tsx
import { Toaster } from "@/components/ui/sonner";
<Toaster richColors closeButton position="top-right" />

// anywhere
import { toast } from "sonner";
toast.success("Saved");
toast.error("Failed", { description: err.message });
toast.promise(mutation.mutateAsync(payload), {
  loading: "Saving...",
  success: "Saved",
  error: (e) => e.message,
});
// Dedupe: stable id prevents stacking identical toasts
toast("Retrying...", { id: "retry" });
```

Portal target: sonner portals to `document.body` by default. That's
the right choice for 99% of apps.

---

## TanStack Table v8

shadcn's DataTable is a recipe, not a component. The primitives
(`<Table>`, `<TableHeader>`, `<TableBody>`, `<TableRow>`,
`<TableCell>`, `<TableHead>`) are thin Tailwind-styled `<table>`
wrappers. You bring the headless logic.

```tsx
const table = useReactTable({
  data, columns,
  getCoreRowModel: getCoreRowModel(),
  getSortedRowModel: getSortedRowModel(),
  getPaginationRowModel: getPaginationRowModel(),
  getFilteredRowModel: getFilteredRowModel(),
  state: { sorting, columnFilters },
  onSortingChange: setSorting,
  onColumnFiltersChange: setColumnFilters,
});
```

Key integration notes:
- Column `cell` and `header` can return JSX — use shadcn Buttons,
  Badges, DropdownMenus freely.
- Use `flexRender` to render header/cell definitions.
- For row actions (edit/delete), put a DropdownMenu in the last
  column and lift Dialog state to the table parent.

---

## Theming: next-themes (Next) or custom Vite provider

**Next.js:**
```tsx
import { ThemeProvider } from "next-themes";
<ThemeProvider attribute="class" defaultTheme="system" enableSystem>
  {children}
</ThemeProvider>
```

**Vite:** build a custom provider (see `examples.md` section 7) that
toggles `document.documentElement.classList.add("dark")` and
persists to `localStorage`. ~30 lines.

Both approaches pair with shadcn's CSS variables automatically —
shadcn components reference `bg-background` / `text-foreground`
which switch on the `.dark` class.

---

## Radix UI (the behavior layer)

shadcn is a thin styled wrapper over Radix. When you need a
primitive shadcn doesn't wrap (e.g., `@radix-ui/react-aspect-ratio`),
the pattern is:

1. `npm i @radix-ui/react-aspect-ratio`
2. Create `src/components/ui/aspect-ratio.tsx`:
   ```tsx
   "use client";
   import * as AspectRatioPrimitive from "@radix-ui/react-aspect-ratio";
   const AspectRatio = AspectRatioPrimitive.Root;
   export { AspectRatio };
   ```
3. Import from `@/components/ui/aspect-ratio` in app code.

This centralizes the styling contract even for primitives shadcn
doesn't ship. Always route Radix imports through
`@/components/ui/*`, never direct.

---

## lucide-react (icons)

Default icon set. Set in `components.json.iconLibrary: "lucide"`.
Icons are tree-shakable:

```tsx
import { Check, ChevronDown, Loader2 } from "lucide-react";
<Loader2 className="h-4 w-4 animate-spin" />
```

Alternative: `iconLibrary: "radix"` uses `@radix-ui/react-icons`
(smaller set, geometric style).

---

## cmdk (under Command)

shadcn's `<Command>` is cmdk (Paco Coursey) styled with Tailwind.
The `<CommandDialog>` compound (Command inside a Dialog) is the
⌘K pattern Linear popularized.

```tsx
const [open, setOpen] = useState(false);
useEffect(() => {
  const down = (e: KeyboardEvent) => {
    if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault(); setOpen((v) => !v);
    }
  };
  document.addEventListener("keydown", down);
  return () => document.removeEventListener("keydown", down);
}, []);

<CommandDialog open={open} onOpenChange={setOpen}>
  <CommandInput placeholder="Search..." />
  <CommandList>
    <CommandEmpty>No results.</CommandEmpty>
    <CommandGroup heading="Leads">
      {leads.map((l) => (
        <CommandItem key={l.id} onSelect={() => navigate(`/leads/${l.id}`)}>
          {l.name}
        </CommandItem>
      ))}
    </CommandGroup>
  </CommandList>
</CommandDialog>
```

---

## Drizzle ORM (server-side only)

shadcn lives client-side. Drizzle lives server-side. The bridge:

1. Define a Zod schema for a lead.
2. `z.infer<typeof leadSchema>` → TS type.
3. Use the TS type in Drizzle's `insert`/`select` calls.
4. Use the Zod schema in the shadcn Form.
5. Single source of truth — the schema.

NEVER import Drizzle from client code. Keep API calls behind
`/api/*` proxied by Vite dev server.

---

## Express backend proxy

In Vite dev:
```ts
server: {
  proxy: {
    "/api": { target: "http://localhost:3000", changeOrigin: true },
  },
}
```

shadcn Forms submit via `fetch("/api/...")` which transparently
forwards to Express. In production, the same path works if the
Express server serves the Vite `dist/` as static.

---

## Stack summary (EOS canonical)

```
Browser
  └─ React 18 (TS strict)
       └─ Vite (dev + Rollup build)
            └─ Tailwind v3.4 (CSS variables + dark mode class)
                 └─ shadcn/ui (vendored)
                      ├─ Radix UI primitives (behavior + a11y)
                      ├─ class-variance-authority (variants)
                      ├─ tailwind-merge via cn() (class merging)
                      ├─ lucide-react (icons)
                      ├─ React Hook Form + zodResolver (forms)
                      ├─ TanStack Query (async state)
                      ├─ TanStack Table v8 (data grids)
                      ├─ sonner (toasts)
                      ├─ cmdk (command palette)
                      ├─ vaul (mobile drawers)
                      └─ react-day-picker (calendar)
                           └─ fetch /api/* → Vite proxy
                                └─ Express + Drizzle + Neon Postgres
```

Every layer knows exactly one thing. The glue is the Zod schema and
the `cn()` helper. That's it.
