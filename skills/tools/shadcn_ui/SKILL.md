---
name: shadcn_ui
description: "Use when adding, modifying, or composing shadcn/ui components in /opt/OS/saas — running the `shadcn` CLI to vendor components, authoring or editing components.json, theming via CSS variables (HSL tokens + dark mode), integrating Radix UI primitives with Tailwind classes and CVA (class-variance-authority) variants, wiring the <Form> primitives to React Hook Form + zodResolver, building DataTable with TanStack Table, nesting Dialog/Popover/DropdownMenu with portals, using the cn() + tailwind-merge helper, extending component variants, resolving React 19 peer-dep issues, handling the New York vs Default style decision, or diagnosing why a re-run of `shadcn add` clobbered local edits."
allowed-tools: "Read, Write, Edit, Bash, WebFetch, WebSearch"
version: 1.0
source_url: "https://ui.shadcn.com/docs"
last_researched: "2026-04-09"
instantiated_from: templates/tools/_template/
api_version: "n/a (CLI + registry)"
sdk_version: "shadcn@latest"
speed_category: "medium"
trigger: both
effort: high
context: fork
---

# Tool: shadcn/ui

shadcn/ui is the component layer for every EOS SaaS surface. It is not
an npm package you import from — it is a CLI that copies component
source code into your repo. You own the files. You version them. You
edit them. The tradeoff is clear: no upstream upgrade path, full
control of every line.

This skill exists so agents working in `/opt/OS/saas` use shadcn/ui the
way shadcn (@shadcn on Twitter) designed it — Radix primitives for
behavior, Tailwind for style, CVA for variants, `cn()` for class
merging, CSS variables for theming, and the CLI as a one-way code
generator, not a dependency.

## What This Tool Does

shadcn/ui is a **component distribution system**, not a component
library. Three things make it different from MUI / Chakra / Mantine:

1. **Copy-paste, not install.** `npx shadcn@latest add button` writes
   `src/components/ui/button.tsx` into your repo. There is no
   `@shadcn/ui` runtime package. Deleting `node_modules` does not
   delete your button.
2. **Radix + Tailwind + CVA is the stack.** Every component is a thin
   wrapper: Radix UI primitive (accessibility + behavior) + Tailwind
   classes (style) + `class-variance-authority` (variant API) +
   `tailwind-merge` via `cn()` (safe class overrides).
3. **CSS variables for theming.** Colors are defined as HSL triplets
   in `:root` and `.dark` in `globals.css`. Tailwind maps them via
   `tailwind.config.ts`. Switching themes is a class toggle on `<html>`.

Core capabilities:
- **`shadcn` CLI** — `init`, `add`, `diff`, `build` (private registries).
- **components.json** — the config file that tells the CLI where to
  write components, which style to use, which aliases to emit.
- **Two styles** — `default` (classic Tailwind) and `new-york`
  (tighter, shadcn's preferred). Choose at `init`. Cannot mix.
- **Form primitives** — `<Form>`, `<FormField>`, `<FormItem>`,
  `<FormLabel>`, `<FormControl>`, `<FormMessage>`, `<FormDescription>` —
  thin adapters over React Hook Form's `<Controller>` + Radix Label +
  a React Context for field state. They exist so you never touch
  `aria-invalid` / `aria-describedby` by hand.
- **~50 components** — Button, Input, Select, Dialog, Sheet, Drawer,
  Popover, DropdownMenu, Command (cmdk), Calendar (react-day-picker),
  DataTable (TanStack Table recipe), Toast (via sonner or the legacy
  toast), Tooltip, Accordion, Tabs, and more.
- **Registries** — you can host your own component registry and point
  the CLI at it (`shadcn build` + a URL). This is how design systems
  ship to multiple apps.

## EOS Integration

**Where shadcn/ui lives:**
- `/opt/OS/saas/*/components.json` — CLI config per app.
- `/opt/OS/saas/*/src/components/ui/` — vendored primitives. EOS owns this.
- `/opt/OS/saas/*/src/components/` — composed app-level components
  that import from `@/components/ui/*`.
- `/opt/OS/saas/*/src/lib/utils.ts` — contains `cn()` helper (clsx +
  tailwind-merge). The CLI writes this on `init`.
- `/opt/OS/saas/*/src/app/globals.css` (or `src/index.css`) — CSS
  variables for `:root` and `.dark`.
- `/opt/OS/saas/*/tailwind.config.ts` — maps CSS variables to Tailwind
  color tokens (`hsl(var(--primary))`).

**Stack partners (see references/integrations.md):**
- **React 18 + TS strict** — every vendored file is `.tsx` and fully typed.
- **Vite** — works out of the box; the CLI detects Vite via
  `components.json.framework: "vite"`.
- **Tailwind** — required. shadcn/ui has no styles of its own.
- **Radix UI** — the CLI installs `@radix-ui/react-*` deps automatically
  per component. Never install them manually.
- **React Hook Form + Zod** — `<Form>` primitives wrap RHF's
  `<Controller>`. Use `zodResolver(schema)` in `useForm`.
- **TanStack Table v8** — shadcn's DataTable is a recipe, not a
  component. Copy the pattern from ui.shadcn.com/examples/tasks.
- **sonner** — the modern toast. Replaces the legacy `useToast` hook.
- **next-themes** (or a Vite equivalent) — dark mode class toggle.

**The rule:** import Radix primitives ONLY from `@/components/ui/*`.
Never `import * as DialogPrimitive from "@radix-ui/react-dialog"` in
app code. The vendored wrapper exists to centralize styling.

## Authentication

**Not applicable — shadcn/ui is a CLI + public registry.** There is no
API key, no account, no token. The CLI fetches JSON component
manifests from `https://ui.shadcn.com/r/*.json` at install time.

What replaces auth:

- **Registry URL pinning.** The public registry is the default. For
  private design systems you host your own registry (`shadcn build`
  generates `public/r/*.json`; point other apps at it via
  `registries` in `components.json`).
- **Version control IS your lockfile.** Because components are
  vendored into the repo, every change shows in `git diff`. There is
  no `package-lock.json` entry for `@shadcn/button` — the
  lockfile is the git SHA of `button.tsx`.
- **Peer-dep audit.** The CLI installs `@radix-ui/react-*` and
  `class-variance-authority`, `clsx`, `tailwind-merge`,
  `tailwindcss-animate`, `lucide-react` as real npm deps. Those DO
  have lockfile entries. Pin them.

## Quick Reference

### Initialize in an EOS Vite + TS + Tailwind app

```bash
cd /opt/OS/saas/my-app
npx shadcn@latest init
# Prompts:
#  - Which style? › new-york
#  - Which base color? › zinc
#  - CSS variables? › yes
# Writes: components.json, src/lib/utils.ts, src/app/globals.css updates,
#         tailwind.config.ts updates, installs deps.
```

### components.json (Vite + TS + Tailwind + @ alias)

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "rsc": false,
  "tsx": true,
  "tailwind": {
    "config": "tailwind.config.ts",
    "css": "src/app/globals.css",
    "baseColor": "zinc",
    "cssVariables": true,
    "prefix": ""
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  },
  "iconLibrary": "lucide"
}
```

### Add components

```bash
npx shadcn@latest add button input label form dialog select
npx shadcn@latest add sonner        # modern toast
npx shadcn@latest add table         # then follow DataTable recipe
npx shadcn@latest diff button       # show drift vs upstream
```

### Form with React Hook Form + Zod (the canonical pattern)

```tsx
"use client";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Form, FormControl, FormField, FormItem, FormLabel, FormMessage,
} from "@/components/ui/form";

const schema = z.object({
  email: z.string().email(),
  name: z.string().min(2),
});
type Values = z.infer<typeof schema>;

export function SignupForm() {
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", name: "" },
  });

  function onSubmit(values: Values) {
    // call API here
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Email</FormLabel>
              <FormControl><Input type="email" {...field} /></FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Name</FormLabel>
              <FormControl><Input {...field} /></FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <Button type="submit">Sign up</Button>
      </form>
    </Form>
  );
}
```

### Dialog

```tsx
import {
  Dialog, DialogContent, DialogDescription, DialogFooter,
  DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

export function ConfirmDelete({ onConfirm }: { onConfirm: () => void }) {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="destructive">Delete</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Are you sure?</DialogTitle>
          <DialogDescription>
            This action cannot be undone.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline">Cancel</Button>
          <Button variant="destructive" onClick={onConfirm}>
            Delete
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

### DataTable pattern (TanStack Table v8)

```tsx
import {
  ColumnDef, flexRender, getCoreRowModel, getPaginationRowModel,
  useReactTable,
} from "@tanstack/react-table";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";

export function DataTable<T>({ columns, data }: {
  columns: ColumnDef<T>[]; data: T[];
}) {
  const table = useReactTable({
    data, columns,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
  });
  return (
    <Table>
      <TableHeader>
        {table.getHeaderGroups().map((hg) => (
          <TableRow key={hg.id}>
            {hg.headers.map((h) => (
              <TableHead key={h.id}>
                {flexRender(h.column.columnDef.header, h.getContext())}
              </TableHead>
            ))}
          </TableRow>
        ))}
      </TableHeader>
      <TableBody>
        {table.getRowModel().rows.map((row) => (
          <TableRow key={row.id}>
            {row.getVisibleCells().map((c) => (
              <TableCell key={c.id}>
                {flexRender(c.column.columnDef.cell, c.getContext())}
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
```

### Theming with CSS variables (HSL triplets)

```css
/* src/app/globals.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 240 10% 3.9%;
    --primary: 240 5.9% 10%;
    --primary-foreground: 0 0% 98%;
    --border: 240 5.9% 90%;
    --ring: 240 10% 3.9%;
    --radius: 0.5rem;
  }
  .dark {
    --background: 240 10% 3.9%;
    --foreground: 0 0% 98%;
    --primary: 0 0% 98%;
    --primary-foreground: 240 5.9% 10%;
    --border: 240 3.7% 15.9%;
    --ring: 240 4.9% 83.9%;
  }
}
```

Values are **unquoted HSL triplets** (no `hsl(...)`, no commas). The
wrapper is in `tailwind.config.ts`:

```ts
colors: {
  background: "hsl(var(--background))",
  foreground: "hsl(var(--foreground))",
  primary: {
    DEFAULT: "hsl(var(--primary))",
    foreground: "hsl(var(--primary-foreground))",
  },
}
```

## Conceptual Model

Think of shadcn/ui as **a curated snippet library with a package
manager**, not a UI framework.

1. **Vendoring is the point.** The CLI copies files. It does not
   maintain a dependency you can `npm update`. The benefit: you can
   edit any component. The cost: you cannot `npm update` to get fixes;
   you must re-run `shadcn add` and reapply your diff.

2. **Four layers per component.**
   - **Radix primitive** — unstyled, accessible behavior
     (`@radix-ui/react-dialog`). Handles focus trap, ESC, ARIA.
   - **CVA variants** — `cva(base, { variants, defaultVariants })`
     produces a typed function that emits class strings per variant.
   - **Tailwind classes** — the actual visual language.
   - **`cn()` helper** — `twMerge(clsx(inputs))`. Lets callers pass
     `className` that safely overrides the component's defaults
     (tailwind-merge de-dupes conflicting utilities: last one wins).

3. **`asChild` is Radix's composition primitive.** `<DialogTrigger
   asChild><Button>Open</Button></DialogTrigger>` merges the trigger's
   props (onClick, aria-*) into the Button instead of wrapping it in
   another element. Forget `asChild` and you get `<button><button>`,
   which is invalid HTML and a focus bug.

4. **CSS variables are the theme contract.** Components reference
   `bg-background`, `text-foreground`, `border-border`. Swapping a
   theme means overriding the variables, not the component files. A
   design system ships as a `globals.css`, not a new component set.

5. **The Form primitive wraps React Hook Form's Controller.** `<Form>`
   is `<FormProvider>`. `<FormField>` is `<Controller>` + a context
   provider that exposes `id`, `name`, `formItemId`,
   `formDescriptionId`, `formMessageId`. `<FormControl>` reads that
   context and injects the right `id` + `aria-describedby` +
   `aria-invalid` onto the inner input via `asChild`. This is why RHF
   integration is zero-boilerplate.

6. **Variants are a value, not a subclass.** `<Button variant="outline"
   size="sm">` picks a CVA branch. Don't create `<OutlineButton>` —
   extend variants instead. Variant explosion is real: if you have 7
   variants × 5 sizes × 3 states, you have 105 class combinations.
   Prefer composition (compose two components) over a new variant.

7. **Registries turn shadcn into a design system tool.** `shadcn
   build` generates JSON manifests from your `registry/` folder.
   Point a second app's `components.json.registries` at the URL and
   `shadcn add @mybrand/button` pulls your branded version. This is
   how you ship EOS components across multiple SaaS repos without a
   monorepo.

## Gotchas

- **`shadcn add` overwrites your edits.** If you edited
  `src/components/ui/button.tsx` and re-run `npx shadcn@latest add
  button`, the CLI prompts to overwrite and most people hit Enter.
  Your edits are gone. Use `shadcn diff button` first. Commit before
  running `add`. Treat `ui/*.tsx` as YOUR files under version control,
  not generated output.

- **Tailwind `content` paths must include `src/components/ui/**`.**
  If they don't, shadcn classes get tree-shaken out and components
  render unstyled. The CLI's `init` sets this up; manual edits to
  `tailwind.config.ts` break it. Symptom: button is a naked anchor tag.

- **Dark mode: class vs attribute.** shadcn expects `darkMode:
  ["class"]` in `tailwind.config.ts` and toggles `<html class="dark">`.
  `next-themes` does this for Next. For Vite, either use a custom
  hook or add `data-theme` — but then you must set
  `darkMode: ["class", '[data-theme="dark"]']`. Mixing selectors
  silently half-applies the theme.

- **Forgetting `asChild` on Radix triggers.** `<DialogTrigger><Button>
  Open</Button></DialogTrigger>` renders a `<button>` (DialogTrigger's
  default) wrapping a `<button>` (Button). Nested buttons are invalid
  HTML, break keyboard nav, and fail accessibility audits. Always use
  `asChild` when the child is already the right element.

- **CVA variant explosion.** Each variant adds a class permutation.
  `variant × size × state × intent` grows multiplicatively. After ~50
  permutations, JIT Tailwind pre-generates them all and bundle grows.
  Rule: if a variant is used in 1 place, it's a prop. If it's used in
  3+ places with different content, it's a new component.

- **New York vs Default style is a one-way door.** `style` in
  `components.json` controls which registry the CLI pulls from. You
  cannot mix — running `add button` after changing the style rewrites
  the file in the new style and clobbers your edits. Pick at `init`
  and commit.

- **React 19 peer-dep warnings.** Some Radix packages still list React
  18 as a peer dep. `npm install` will warn or fail with
  `ERESOLVE`. Use `npm install --legacy-peer-deps` OR pin React to
  18.3.x until Radix catches up. The shadcn CLI added a
  `--legacy-peer-deps` flag specifically for this.

- **`cn()` without `tailwind-merge` is a footgun.** If you clone the
  helper and forget `twMerge`, callers' `className` props collide with
  the component's defaults in CSS source order (last rule wins — which
  is NOT always the caller's). Always use
  `twMerge(clsx(inputs))`, not `clsx` alone.

- **Dialog inside DropdownMenu without a portal races.** The menu
  unmounts on selection, which unmounts the Dialog before its open
  animation completes. Fix: render the Dialog at the page level and
  trigger via state, OR use `<DialogTrigger asChild>` inside a
  `<DropdownMenuItem onSelect={(e) => e.preventDefault()}>`.

- **`useToast` (legacy) vs `sonner` (current).** The docs moved to
  sonner in late 2024. New projects should run `shadcn add sonner` and
  import `toast` from `sonner`. The old `useToast` hook + `<Toaster>`
  still works but is no longer updated.

- **WebFetch on ui.shadcn.com returns partial JS-rendered content.**
  For deep research, use WebSearch or fetch the raw markdown from the
  shadcn/ui GitHub repo (`apps/www/content/docs/**/*.mdx`).

## References

- `references/best_practices.md` — full 19-section creator-level protocol.
- `references/examples.md` — EOS-aligned components.json, Form, DataTable, theming, custom CVA variants.
- `references/anti_patterns.md` — real failure modes and fixes.
- `references/integrations.md` — React / Vite / Tailwind / RHF / Zod / React Query / sonner / TanStack Table / theming stack composition.

## Source

- https://ui.shadcn.com (authoritative docs)
- https://ui.shadcn.com/docs/components.json (config schema)
- https://ui.shadcn.com/docs/cli (CLI reference)
- https://ui.shadcn.com/docs/theming (CSS variables + dark mode)
- https://github.com/shadcn-ui/ui (source + registry format)
- https://www.radix-ui.com/primitives (underlying primitives)
- https://cva.style (class-variance-authority docs)
- https://github.com/dcastil/tailwind-merge (tailwind-merge docs)
- https://react-hook-form.com (RHF — Form primitive backend)
- https://sonner.emilkowal.ski (current toast implementation)
