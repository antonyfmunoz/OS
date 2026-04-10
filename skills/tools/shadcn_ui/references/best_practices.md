# shadcn/ui — Creator-Level Best Practices

Research date: 2026-04-06
Sources: ui.shadcn.com, github.com/shadcn-ui/ui, radix-ui.com, cva.style,
github.com/dcastil/tailwind-merge, react-hook-form.com, sonner.emilkowal.ski,
shadcn (@shadcn) interviews and tweets.

This document follows the 19-section Tool Mastery research protocol.
Tier 1 = technical mastery. Tier 2 = creator intelligence.

---

## Authentication
**Not applicable in the traditional sense.** shadcn/ui is a CLI that
fetches component manifests from a public HTTP registry. There is no
API key, no OAuth, no account.

What replaces auth:

- **Public registry:** `https://ui.shadcn.com/r/styles/{style}/{component}.json`
  returned as JSON. `shadcn add button` = HTTP GET + file write.
- **Private registries:** `shadcn build` walks a `registry/` folder and
  emits JSON manifests into `public/r/`. Host them on any static
  server. Consumers set `registries` in `components.json`:
  ```json
  {
    "registries": {
      "@mybrand": {
        "url": "https://design.mybrand.com/r/{name}.json",
        "headers": { "Authorization": "Bearer ${REGISTRY_TOKEN}" }
      }
    }
  }
  ```
  Registry tokens live in env vars, expanded by the CLI at install
  time. This is the only place a "secret" exists in shadcn/ui.
- **Peer dependency trust:** `shadcn add` installs `@radix-ui/react-*`,
  `class-variance-authority`, `clsx`, `tailwind-merge`,
  `tailwindcss-animate`, and `lucide-react` as real npm deps. Pin
  them in `package.json` and commit the lockfile.

EOS env vars: **none for the public registry.** If EOS ever hosts a
private registry, `REGISTRY_TOKEN` goes in `/opt/OS/saas/*/.env.local`
and is referenced by `components.json`.

---

## Core Operations
shadcn/ui's "API" is the CLI and the vendored components. The
signatures below are current as of shadcn@2.x.

### CLI commands

```bash
# Initialize project — writes components.json, utils.ts, updates globals.css
npx shadcn@latest init [options]
  --defaults              # skip prompts, use defaults
  --force                 # overwrite existing components.json
  --yes                   # skip confirmation
  --cwd <path>            # working directory
  --src-dir / --no-src-dir
  --css-variables / --no-css-variables
  --base-color <color>    # slate | gray | zinc | neutral | stone
  --style <style>         # default | new-york

# Add a component (or list of components)
npx shadcn@latest add [components...] [options]
  --yes                   # skip confirmation
  --overwrite             # overwrite existing files without asking
  --path <path>           # override destination
  --all                   # add every component in the registry
  --cwd <path>

# Show upstream drift for a component
npx shadcn@latest diff [component]

# Build a private registry from ./registry/*
npx shadcn@latest build [registry] [options]
  --output <dir>          # default: public/r
  --cwd <path>
```

### CVA signature (class-variance-authority)

```ts
import { cva, type VariantProps } from "class-variance-authority";

const buttonVariants = cva(
  // base classes always applied
  "inline-flex items-center justify-center rounded-md text-sm font-medium",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        destructive: "bg-destructive text-destructive-foreground",
        outline: "border border-input bg-background hover:bg-accent",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-9 px-4 py-2",
        sm: "h-8 rounded-md px-3 text-xs",
        lg: "h-10 rounded-md px-8",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
    compoundVariants: [
      { variant: "outline", size: "lg", class: "px-6" },
    ],
  }
);

type ButtonVariants = VariantProps<typeof buttonVariants>;
// { variant?: "default"|"destructive"|..., size?: "default"|"sm"|"lg"|"icon" }
```

### `cn()` helper signature

```ts
// src/lib/utils.ts — emitted by `shadcn init`
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

### Form primitive signatures (React Hook Form adapter)

```tsx
<Form {...form}>                                      // = FormProvider
  <FormField
    control={form.control}
    name="fieldName"                                   // typed from schema
    render={({ field, fieldState, formState }) => (...)}
  />
  <FormItem />           // wraps label + control + message, provides id context
  <FormLabel />          // <Label htmlFor={formItemId} />
  <FormControl />        // Slot with asChild — injects id, aria-describedby, aria-invalid
  <FormDescription />    // hint text, id={formDescriptionId}
  <FormMessage />        // validation error, id={formMessageId}
</Form>
```

### components.json schema (the full surface)

```jsonc
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "default" | "new-york",
  "rsc": boolean,                  // React Server Components (Next.js app router)
  "tsx": boolean,                  // tsx vs jsx output
  "tailwind": {
    "config": "tailwind.config.ts",
    "css": "src/app/globals.css",
    "baseColor": "slate"|"gray"|"zinc"|"neutral"|"stone",
    "cssVariables": boolean,
    "prefix": ""                   // Tailwind class prefix, rarely used
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  },
  "iconLibrary": "lucide" | "radix",
  "registries": { /* optional private registries */ }
}
```

---

## Pagination
**Not applicable in the library sense.** shadcn has no paginated API.
What matters is **DataTable pagination**, which is a TanStack Table
recipe shadcn ships as an example.

### TanStack Table pagination with shadcn Table

```tsx
const table = useReactTable({
  data,
  columns,
  getCoreRowModel: getCoreRowModel(),
  getPaginationRowModel: getPaginationRowModel(),
  initialState: { pagination: { pageSize: 20, pageIndex: 0 } },
});

// Controls
<Button
  variant="outline"
  size="sm"
  onClick={() => table.previousPage()}
  disabled={!table.getCanPreviousPage()}
>Previous</Button>
<Button
  variant="outline"
  size="sm"
  onClick={() => table.nextPage()}
  disabled={!table.getCanNextPage()}
>Next</Button>

// Server-side (manual) pagination
useReactTable({
  data,
  columns,
  manualPagination: true,
  pageCount: totalPages,              // from server
  state: { pagination },
  onPaginationChange: setPagination,  // trigger refetch via React Query
});
```

Combine with React Query's `keepPreviousData: true` for smooth page
transitions without spinners on every page change.

### Command (cmdk) pagination

The `<Command>` component does not paginate — it filters in-memory.
For large result sets, debounce the input and page via an external
API; render only the current page inside `<CommandList>`.

---

## Rate Limits
**Not applicable to runtime.** Vendored components have zero network
cost at runtime.

The only rate-relevant surface is the **CLI → registry fetch**, which
is just HTTPS GETs to `ui.shadcn.com/r/*.json`. In practice:
- Public registry has no documented per-IP rate limit, but treat it
  as generous (no published number). Cached by Cloudflare.
- Private registries inherit whatever rate-limiting the host imposes.
  Host on Cloudflare Pages / Vercel / S3+CloudFront → effectively
  unlimited for team usage.
- `shadcn add --all` makes ~50 sequential requests. Safe. Run once.

What actually needs rate-limit awareness in a shadcn UI:
- **Toast spam** (via sonner) — the library dedupes by id but you
  must pass stable ids to prevent stacks of identical toasts during
  retry loops. Use `toast("msg", { id: "save-failure" })`.
- **Combobox/Command async search** — debounce 200-300ms before
  hitting backend; otherwise keypress = request.

---

## Error Codes
### CLI error modes

- **`ERESOLVE` during `shadcn add`** — npm peer-dep conflict, usually
  React 19 vs Radix peer React 18. Fix: re-run with
  `--legacy-peer-deps` (CLI passes through to npm) OR downgrade React
  to 18.3.x.
- **`Cannot find module 'tailwindcss'`** — `init` ran before Tailwind
  was installed. Fix: `npm i -D tailwindcss postcss autoprefixer &&
  npx tailwindcss init -p` first.
- **`components.json not found`** — `add` requires an initialized
  project. Run `shadcn init` first.
- **"No such component in registry"** — mistyped name or wrong
  `style`. `shadcn` is the binary, `shadcn-ui` is an OLD alias; some
  tutorials show `npx shadcn-ui@latest add ...` which now proxies but
  will eventually stop. Always use `shadcn@latest`.
- **`Failed to parse JSON`** from registry — private registry URL
  returned HTML (e.g., auth wall). Verify the URL resolves to raw
  JSON.
- **`Path alias "@/..." could not be resolved`** — `aliases` in
  `components.json` are OUT OF SYNC with `tsconfig.json` `paths` and
  `vite.config.ts` `resolve.alias`. All three must match.

### Runtime component error modes

These come from Radix, not shadcn itself:
- **`Cannot update a component while rendering a different component`** —
  calling `setState` inside a Radix event handler that fires during
  the open transition. Wrap in `queueMicrotask`.
- **`useLayoutEffect does nothing on the server`** — Radix uses
  `useLayoutEffect`. In Next RSC / SSR, wrap Radix components in a
  client component (`"use client"`).
- **Focus trap bug after Dialog closes** — usually caused by closing
  a Dialog that was inside an unmounted DropdownMenu. Fix in the
  Dialog-in-DropdownMenu gotcha below.

Recovery pattern for the CLI: **always commit before `shadcn add`.**
If an overwrite destroys edits, `git restore` is the fix.

---

## SDK Idioms
shadcn/ui has no runtime SDK. The "SDK" is:

1. **The CLI** (`shadcn@latest`) — idiomatic usage:
   - Use `npx shadcn@latest`, not a locally installed version.
     Pinning the CLI version locks you to a registry schema; `@latest`
     stays current with the registry.
   - Commit `components.json`. It's your project config, not
     generated output.
   - Commit everything under `src/components/ui/*`. Treat as owned
     code.
   - Run `shadcn diff` before `shadcn add` on an existing component.

2. **CVA** (`class-variance-authority`) — idiomatic usage:
   - Always type variant props via `VariantProps<typeof variantsFn>`.
   - Use `compoundVariants` for intersections (e.g., `variant="outline"
     + size="lg"` needs extra padding).
   - Use `defaultVariants` so consumers can omit props.

3. **`cn()`** — idiomatic usage:
   - ALWAYS call it at the top of every component's className prop:
     `<div className={cn(baseClasses, className)}>`. This allows
     callers to override.
   - Never concatenate class strings with `+` — tailwind-merge is the
     only safe way to handle overrides.

4. **Radix primitives** — idiomatic usage:
   - Import via `* as XPrimitive` in the vendored wrapper file.
   - Wrap each piece (`Root`, `Trigger`, `Content`, ...) with
     `React.forwardRef` and a `displayName`.
   - Use `asChild` on every primitive that might wrap app-level
     elements (Trigger, Close, Action).
   - Respect Radix's event semantics — use `onOpenChange`, not
     `onClick` to close a dialog.

5. **React Hook Form + shadcn Form** — idiomatic usage:
   - Always wrap `<FormControl>` around ONE child input with
     `asChild` semantics (FormControl uses Radix Slot internally).
   - Use `zodResolver(schema)` for schema validation.
   - Pass `defaultValues` to `useForm` — never rely on uncontrolled.
   - Use `form.reset()` after successful submit, not `setValue` loops.

---

## Anti-Patterns
Lifted from shadcn/ui GitHub issues, the EOS experience so far, and
community posts. See `anti_patterns.md` for the full annotated list.
Headlines:

1. **Editing `src/components/ui/*` then re-running `shadcn add`
   without a diff.** Overwrites your work. Fix: commit first, run
   `diff` first.
2. **Using `className` without `cn()` in component wrappers.**
   Caller overrides collide unpredictably. Fix: always
   `className={cn("base classes", className)}`.
3. **Forgetting `asChild` on Radix Triggers wrapping a `<Button>`.**
   Produces nested buttons. Fix: `<DialogTrigger asChild><Button>...`.
4. **Nesting `<Dialog>` inside `<DropdownMenuItem>` without
   `e.preventDefault()`.** The menu unmounts on select, killing the
   dialog. Fix: `onSelect={(e) => e.preventDefault()}`.
5. **Creating a new variant for every one-off style.** CVA variant
   explosion. Fix: compose, don't extend.
6. **Mixing Default and New York styles** in one repo. The CLI
   overwrites files with whichever `style` is set now. Pick one.
7. **Manual `npm i @radix-ui/react-dialog`** instead of `shadcn add
   dialog`. Skips the wrapper, loses the styling contract, creates
   drift.
8. **Using `useToast` legacy hook in new code** when sonner is the
   current recommendation.
9. **Theming by editing component files** instead of CSS variables.
   A design system ships as `globals.css`, not as new components.
10. **Relying on `tsconfig.json paths` alone** — Vite/Rollup do not
    honor TS paths at runtime. You MUST mirror the alias in
    `vite.config.ts resolve.alias` OR use `vite-tsconfig-paths`.

---

## Data Model
shadcn/ui has no data model of its own, but its **configuration**,
**registry**, and **theme** have schemas worth knowing.

### components.json (project config)

See Section 2 for the full schema. Key relationships:
- `style` + `tailwind.baseColor` determine which registry files the
  CLI fetches.
- `aliases.ui` is where components are written (default
  `@/components/ui`).
- `aliases.utils` must export `cn` — the CLI imports it from there.
- `tailwind.cssVariables: true` flips the registry to the CSS
  variable versions of every component (the other branch uses
  hardcoded Tailwind colors).

### Registry manifest (one JSON per component)

```jsonc
{
  "name": "button",
  "type": "registry:ui",
  "dependencies": ["@radix-ui/react-slot"],
  "registryDependencies": [],       // other shadcn components required
  "files": [
    {
      "path": "ui/button.tsx",
      "content": "...",
      "type": "registry:ui",
      "target": ""
    }
  ],
  "tailwind": { "config": { /* theme extensions */ } },
  "cssVars": { "light": {...}, "dark": {...} }
}
```

### Theme tokens (CSS variables)

The canonical token set:
- **Surfaces:** `--background`, `--foreground`, `--card`,
  `--card-foreground`, `--popover`, `--popover-foreground`
- **Brand:** `--primary`, `--primary-foreground`, `--secondary`,
  `--secondary-foreground`, `--accent`, `--accent-foreground`
- **Semantic:** `--destructive`, `--destructive-foreground`,
  `--muted`, `--muted-foreground`
- **Structural:** `--border`, `--input`, `--ring`
- **Geometry:** `--radius`
- **Charts (opt-in):** `--chart-1` ... `--chart-5`
- **Sidebar (opt-in):** `--sidebar`, `--sidebar-foreground`, etc.

All color values are **unquoted HSL triplets** (e.g.,
`240 10% 3.9%`). Tailwind wraps them as `hsl(var(--primary))`. This
unquoted form is what lets you do `bg-primary/90` (opacity modifier).

### Immutable fields

- Once you commit a vendored component, its path is yours. The CLI
  will re-write to the SAME path on `add`, not create a new file.
- `style` is practically immutable — changing it in `components.json`
  without a full re-add leaves you half in each style.

---

## Webhooks
**Not applicable.** There is no event stream, no webhook, no
observability plane. The "events" relevant to shadcn are:

1. **Registry update workflow** — when shadcn (@shadcn) ships a
   component change upstream, consumers must re-run `shadcn add` to
   adopt it. There is no push notification. Watch:
   - https://github.com/shadcn-ui/ui/releases
   - https://x.com/shadcn (announces majors)
   - `shadcn diff` in CI to surface drift.

2. **Component lifecycle events (Radix):**
   - `onOpenChange(open: boolean)` on Dialog / Popover / Sheet /
     Drawer / DropdownMenu / Tooltip / HoverCard / ContextMenu /
     Collapsible.
   - `onValueChange(value)` on Select / RadioGroup / Tabs /
     ToggleGroup / Slider.
   - `onCheckedChange(checked)` on Checkbox / Switch.
   - `onSelect(event)` on DropdownMenuItem / CommandItem /
     ContextMenuItem.

Use these instead of `onClick` — Radix also fires them on keyboard
navigation (Enter, Space), which `onClick` does not always catch.

---

## Limits
Practical limits worth knowing:

- **Bundle impact:** adding ~20 shadcn components + Radix deps adds
  roughly 60-120 KB gzipped to your bundle (varies with tree-shaking).
  DataTable + TanStack Table adds ~30 KB more. Command (cmdk) adds
  ~15 KB.
- **CVA variant count:** soft ceiling around ~50 permutations per
  component before Tailwind JIT bloat becomes measurable.
- **Registry dependency depth:** `registryDependencies` can cascade
  (e.g., Form pulls Label, Slot, React Hook Form). No hard limit,
  but the CLI resolves sequentially — expect ~2-5s per `add` on a
  slow connection.
- **components.json max file size:** not enforced, but keep under
  5KB for readability.
- **Dark mode selector depth:** Tailwind's `darkMode: ["class"]`
  only supports ONE selector. Use the array form to support
  multiple (`["class", '[data-theme="dark"]']`).
- **Radix Portal constraints:** Portal children render at
  `document.body` by default. If your app is inside a scoped CSS
  container (e.g., shadow DOM), override via `<DialogPortal
  container={...}>`.
- **Form `defaultValues`:** must cover EVERY field in the schema.
  Missing a key → RHF treats the field as uncontrolled → shadcn's
  `<FormControl>` throws a "switched from uncontrolled to controlled"
  warning.

---

## Cost Model
**Direct cost: $0.** shadcn/ui is MIT licensed. The public registry
is free. No SaaS plan, no seat licensing.

**Indirect costs that matter:**

- **Bundle size = bandwidth + TTI.** Every vendored component ships
  in your bundle. Code-split heavy components (DataTable, Calendar,
  Command) via `React.lazy`.
- **Maintenance cost = audit drift.** Because you own the files,
  upstream fixes don't flow to you. Budget ~15 min/month to run
  `shadcn diff` across components and decide whether to pull updates.
- **Radix + peer deps:** all MIT. No cost.
- **Private registry hosting (optional):** a few MB of static JSON on
  any static host. Effectively free on Cloudflare Pages / Vercel /
  GitHub Pages.
- **Design time:** the real cost. shadcn's value is a tight, curated
  default style. Diverging from it costs designer time. Budget this
  before picking "let's extend every variant."

Monitoring: **bundle analyzer.** Use `rollup-plugin-visualizer` or
`vite-bundle-visualizer` to see how much each shadcn component
contributes. Kill components you imported but don't use.

---

## Version Pinning
shadcn/ui is weird here because there is no versioned runtime
package. You pin:

1. **The CLI via `npx shadcn@latest`** — don't pin the CLI; it stays
   current with registry format changes. If you must pin, use
   `shadcn@2.x` to lock the major.
2. **Radix peer deps** via `package.json`:
   ```json
   "@radix-ui/react-dialog": "1.1.4",
   "@radix-ui/react-slot": "1.1.1",
   "class-variance-authority": "0.7.1",
   "clsx": "2.1.1",
   "tailwind-merge": "2.5.5",
   "tailwindcss-animate": "1.0.7",
   "lucide-react": "0.468.0"
   ```
3. **The vendored component file** — its git SHA is your version.
4. **React peer** — Radix is currently in transition to React 19
   peer support. Until all Radix packages list React 19, pin React
   to 18.3.x or use `--legacy-peer-deps`.
5. **Tailwind** — shadcn targets Tailwind v3.4+. Tailwind v4 (new
   engine) is supported by the latest shadcn CLI but requires
   different config (CSS-first). Confirm with `shadcn init --help`.
6. **React Hook Form** — v7.x (the Form primitives assume v7 API).
7. **Zod** — any 3.x is fine; shadcn docs show `zod@3`.
8. **TanStack Table** — v8 for DataTable.
9. **sonner** — ^1.5 for current API.

Deprecation policy: shadcn does not publish a deprecation schedule.
Watch the GitHub releases and @shadcn on Twitter.

Currently in flight as of 2026-04-06:
- Tailwind v4 support (CSS-first config, `@theme` directive).
- React 19 peer-dep rollout across Radix.
- New `shadcn registry` DX for private design systems.

---

## Design Intent
shadcn (the creator, @shadcn) built this in 2023 because every
existing React component library had the same problem: **you don't
own your components.** If MUI ships a breaking change, you eat it.
If you want to tweak Chakra's button padding, you override, you
fight, you lose.

The insight: **distribute source code, not a package.** This inverts
the usual tradeoff.

**Conscious tradeoffs:**
- Gave up upstream upgrade path → gained full control of every line.
- Gave up "one import from the library" → gained zero lock-in.
- Gave up abstract theming APIs → gained CSS variables + Tailwind,
  which every developer already knows.
- Gave up framework-agnostic components → chose Radix + Tailwind,
  the best-in-class combo at time of building.

**What shadcn is NOT:**
- NOT a component library. It's a distribution mechanism.
- NOT a design system. It's a starting point for one.
- NOT a CSS framework. It uses Tailwind; it does not replace it.
- NOT a form library. It wraps React Hook Form.
- NOT a table library. It wraps TanStack Table.
- NOT a stateful UI framework. It's stateless primitives.

**Philosophy** (from shadcn's posts and interviews):
- "I don't think of this as a library. I think of it as a reference
  implementation."
- "Copy the parts you want. Leave the parts you don't."
- "The CLI is optional. You can literally copy from the website."

**Prior art that influenced the design:**
- Radix UI — the behavior layer. shadcn is essentially "what does a
  nicely-styled default Radix look like."
- Tailwind UI — Adam Wathan's commercial component set. Same "copy
  the JSX" philosophy but gated behind a paywall. shadcn made it
  free and added a CLI.
- CVA — from Joe Bell. Makes variant management type-safe and
  cacheable.
- tailwind-merge — from Dany Castillo. Makes `cn()` safe.
- Chakra / MUI — the counter-example. shadcn is explicitly "not that."

---

## Problem-Solution Map
**Real problems solved:**

1. **"I want a great-looking UI without design skill."** shadcn's
   defaults (especially New York style) look production-ready out of
   the box. Ship faster.
2. **"I need accessible components but don't want to build them."**
   Radix handles WAI-ARIA; shadcn handles the look.
3. **"I want to deeply customize a component."** Open the file. Edit.
   Commit. No library escape hatches needed.
4. **"I want a design system across multiple apps."** Build a private
   registry. Every app pulls from the same URL.
5. **"I want dark mode without re-styling every component."** CSS
   variables + a class toggle on `<html>` flips the whole UI.
6. **"I want my forms accessible without writing `aria-*` props."**
   The `<Form>` primitive wires it via context.

**Hidden capabilities most users miss:**

1. **`shadcn diff`** — shows upstream changes to any component you
   already have. Almost nobody runs this. It's how you stay current
   without blind overwrites.
2. **Private registries with auth headers.** Ship a branded button
   set to multiple repos with `npx shadcn add @mybrand/button`. This
   turns shadcn into a real design system distribution tool.
3. **Blocks** — `ui.shadcn.com/blocks` ships full-page composed
   layouts (dashboards, sidebars, auth pages). Vendor a whole page:
   `shadcn add dashboard-01`.
4. **Registry-level theme injection.** A registry manifest can
   include `cssVars` that get merged into your `globals.css` on
   `add`. Ship a theme + components as one artifact.
5. **Form primitives work with any RHF backend.** The `<Form>` /
   `<FormField>` pattern does not require Zod — any RHF resolver
   (Yup, Valibot, Joi) works. The Zod pairing is convention.
6. **`asChild` everywhere.** Most shadcn/Radix primitives accept
   `asChild`. You can wrap a Next `<Link>` with `<Button asChild>` to
   get a link that looks like a button without losing routing.
7. **`compoundVariants` in CVA** — lets you express "if variant=X
   AND size=Y, also add class Z". Most users never use this.
8. **Custom icon library.** `iconLibrary: "radix"` in components.json
   switches from lucide to Radix icons across the registry.
9. **`onOpenChange` + React Query** — close a dialog automatically on
   mutation success by passing `open` as state and resetting in
   `onSuccess`.
10. **The `sonner` `toast.promise` API** — one call handles loading,
    success, and error states. Massively underused.

---

## Operational Behavior
- **`shadcn add` runs npm install as a side effect.** If your network
  is slow, the CLI appears to hang. It's just `npm install` under
  the hood. First-time `init` can take 60+ seconds.
- **New York vs Default is stored in components.json and CANNOT be
  changed per-component.** Running `add` in a project with
  `style: "new-york"` will always fetch the New York variant.
- **`cssVariables: false` and `cssVariables: true` pull DIFFERENT
  component files** from the registry. Flipping this flag and
  re-running `add` rewrites components with hardcoded colors.
- **The `<Form>` primitive requires `defaultValues`.** Without them,
  RHF treats fields as uncontrolled and the FormControl `<Slot>`
  throws a "component switched from uncontrolled to controlled"
  warning on first change.
- **`<DialogContent>` with an `<input autoFocus>` inside races the
  focus trap.** Radix moves focus on open; your autoFocus gets
  overridden. Use Radix's `onOpenAutoFocus` to control focus:
  `<DialogContent onOpenAutoFocus={(e) => { e.preventDefault(); inputRef.current?.focus(); }}>`.
- **Command (cmdk) filters case-insensitively but diacritic-sensitively.**
  "résumé" won't match "resume". Use `<Command shouldFilter={false}>`
  and filter manually for diacritic-insensitive search.
- **Tooltip + Button inside a DropdownMenuItem crashes focus.** The
  DropdownMenu grabs focus; the Tooltip never appears. Either drop
  the tooltip or use `DropdownMenuSub` instead.
- **`sonner` toasts are portaled to `document.body`.** If you render
  `<Toaster>` inside a scoped container, toasts still escape. Set
  the portal target via the `<Toaster>` prop.
- **Radix Popover inside a virtualized list unmounts on scroll.**
  The list recycles the row; Popover state lives there. Lift Popover
  state to the parent.
- **SSR / RSC + `useLayoutEffect` warnings.** Radix components use
  `useLayoutEffect`. In Next App Router, mark pages that use them
  `"use client"`.
- **Form reset after submit:** `form.reset()` resets to the initial
  `defaultValues`. To reset to NEW defaults after a save, pass the
  new values: `form.reset(newValues)`.
- **Calendar (`react-day-picker`) time zone gotcha:** it renders in
  the browser's local zone by default. For UTC-only dates, pass
  `timeZone="UTC"` to the Calendar wrapper.
- **CVA + `tailwind-merge` edge case:** conflicting arbitrary values
  (`p-[3px]` vs `p-4`) are NOT merged — they collide. Use consistent
  class shapes.

---

## Ecosystem Position
shadcn/ui sits at the **presentation layer**. It is:

- **Above Tailwind** (consumes Tailwind classes).
- **Above Radix** (wraps Radix primitives).
- **Below app components** (composed into domain-specific UI).
- **Orthogonal to state** (doesn't care about Redux / Zustand /
  React Query).
- **Orthogonal to routing** (works with Next / Remix / TanStack
  Router / React Router).

**Natural complements:**
- **React Hook Form + Zod** — the canonical form stack. shadcn ships
  `<Form>` specifically to wrap RHF.
- **TanStack Table** — shadcn's DataTable is literally a TanStack
  Table recipe. Official example: `ui.shadcn.com/examples/tasks`.
- **TanStack Query** — for async state. Pair with Dialog's
  `onOpenChange` + `toast.promise` for mutation feedback.
- **sonner** — current toast choice. `shadcn add sonner`.
- **cmdk** — the command palette under shadcn's `<Command>`.
- **react-day-picker** — under shadcn's `<Calendar>`.
- **vaul** — under shadcn's `<Drawer>` (mobile bottom sheet).
- **embla-carousel** — under shadcn's `<Carousel>`.
- **recharts** — under shadcn's `<Chart>` (newer addition).
- **next-themes** (Next) / custom Vite theme provider — for dark
  mode class toggling.
- **lucide-react** — default icon set (configurable).

**Forced integrations that fail:**
- **MUI + shadcn in the same app** — both define their own theming
  system; styles fight. Pick one.
- **Tailwind v4 + older shadcn CLI** — v4's new engine needs CLI
  updates. Use latest CLI.
- **Styled-components / Emotion + shadcn** — the `className` flow
  gets confused; tailwind-merge can't merge styled-components'
  generated classes. Don't mix.
- **React Aria Components + Radix** — both are behavior layers.
  Pick one; shadcn chose Radix.

**Data handoff:**
- Form data lands in RHF → validated by Zod → passed to React Query
  `mutateAsync` → feedback via sonner.
- Table data lands in React Query → columns defined once → handed
  to `useReactTable` → rendered by shadcn Table primitives.
- Theme data lands in CSS variables → consumed by Tailwind tokens
  → rendered by every component automatically.

---

## Trajectory
Where shadcn/ui is going as of 2026-04-06:

- **Registries as first-class.** The CLI shipped `shadcn build` and
  `registries` in `components.json` specifically to enable private
  design systems. This is the clearest signal of direction: shadcn
  wants to be the distribution mechanism for component design
  systems, not just one brand's components.
- **Tailwind v4 CSS-first config.** Full support is rolling in; the
  CLI's `init` now handles v4 projects.
- **React Server Components-aware components.** shadcn flags
  `"use client"` where needed; expect finer granularity as RSC
  matures.
- **Blocks growing beyond components.** `ui.shadcn.com/blocks` keeps
  adding full-page compositions. Expect entire app templates
  distributed as registries.
- **AI-assisted theming.** shadcn launched a theme generator that
  takes a brand color and outputs CSS variables. Expect deeper AI
  integration (prompt → full theme).
- **More bundled recipes** (Charts, Editor, Dashboard) as the
  project matures from components to higher-order building blocks.

Deprecation signals:
- **Legacy `useToast` + `<Toaster>`** — still in docs but sonner is
  the recommended path for new projects. Expect legacy to be
  archived within a year.
- **Default style** — both styles are maintained, but New York gets
  more attention in docs and examples.
- **`npx shadcn-ui@latest`** — old package name. Current is
  `npx shadcn@latest`. The old alias proxies but will eventually
  stop.
- **Hardcoded Tailwind colors** (`cssVariables: false`) — everyone
  uses CSS variables now. Expect the flag to remain but the non-var
  path to bit-rot.

Build on: registries, CSS variables, sonner, the Form primitives,
Tailwind v3.4+ patterns.
Do not build on: legacy useToast, hardcoded colors, the old package
name, Default style for new projects.

---

## Conceptual Model
**Mental model in one sentence:** shadcn/ui is how you ship the
Radix + Tailwind combo without writing the boilerplate each time,
with a CLI that acts as `npm install` for source code.

**Primitives:**
- Radix behavior primitives (Dialog, Popover, Select, ...).
- Tailwind utility classes.
- CVA variant functions.
- `cn()` merger.
- CSS variables.
- The CLI + registry.

**Verbs:**
- `init` (set up the project).
- `add` (vendor a component).
- `diff` (check drift).
- `build` (publish a registry).
- Wrap (compose primitives into app components).
- Theme (override CSS variables).

### Recipe 1 — EOS SaaS auth form

```
1. shadcn init (new-york, zinc, css vars)
2. shadcn add button input label form
3. Define Zod schema: { email, password }
4. useForm with zodResolver(schema) + defaultValues
5. Wrap in <Form> → <FormField> per field → <FormControl>
6. Submit via React Query mutation
7. toast.promise(mutation) for loading/success/error feedback
8. Redirect on success via router.push (Next) / navigate (Vite)
```

### Recipe 2 — CRUD dashboard with DataTable

```
1. shadcn add table button input dropdown-menu dialog
2. Define ColumnDef<T> array with cell renderers
3. useReactTable({ data, columns, getCoreRowModel, getPaginationRowModel })
4. Render <Table> using flexRender
5. Row actions via <DropdownMenu> with "Edit" / "Delete" items
6. Edit opens <Dialog> with a shadcn Form inside (Recipe 1)
7. Delete triggers a confirm Dialog + React Query mutation
8. Refetch via queryClient.invalidateQueries on success
```

### Recipe 3 — Theme switcher

```
1. Add CSS variables for :root and .dark in globals.css
2. darkMode: ["class"] in tailwind.config.ts
3. Vite: build a tiny ThemeProvider that reads localStorage
   and toggles className on <html>
4. shadcn add dropdown-menu button
5. Theme toggle component: DropdownMenu with Light / Dark / System
6. On select, update provider state + persist to localStorage
```

### Recipe 4 — Global command palette

```
1. shadcn add command dialog
2. Wrap <Command> in <CommandDialog> (built-in composition)
3. Bind ⌘K to toggle open state via useEffect + keydown
4. Populate <CommandList> from a static list + async search
5. Debounce async search ~250ms via React Query
6. On select, navigate via router / run action / close dialog
```

### Recipe 5 — Private design system registry

```
1. In your design-system repo: create registry/ folder with ui/*.tsx
2. Add registry.json defining each component's manifest
3. npx shadcn build → writes public/r/*.json
4. Deploy public/ to Cloudflare Pages / Vercel static
5. In consumer apps: components.json → registries.@mybrand.url
6. npx shadcn add @mybrand/button → vendors from your registry
```

---

## Industry Expert Usage
How the frontier uses shadcn/ui in 2026:

- **Vercel, Linear, Supabase, Resend, Cal.com** all ship interfaces
  built on or heavily inspired by shadcn + Radix + Tailwind. The
  "shadcn aesthetic" (tight spacing, zinc/slate grays, subtle
  shadows, New York style) is now the default for modern SaaS.
- **AI app builders (v0.dev, bolt.new, Lovable, Tempo Labs)** emit
  shadcn/Radix/Tailwind code by default because it's the best
  LLM-generatable component stack. v0.dev is shadcn's own project.
  This means shadcn IS the canonical "LLM writes a UI" target.
- **Design-to-code pipelines** (Figma → code) output shadcn first
  because CSS variables map cleanly to Figma tokens and CVA maps
  cleanly to Figma variants.
- **Private design systems as static sites.** Teams host
  `design.company.com` as the private shadcn registry + docs. One
  URL is both human-readable docs and machine-readable component
  source. This is the killer DX shadcn enabled.
- **AI-driven theming.** `tweakcn.com` and shadcn's own theme
  editor let users paste a brand color and get a full theme CSS
  variable block. Expect this to become conversational ("make it
  feel more luxurious, darker accents") in 2026.
- **Form schemas as the single source of truth.** Expert pattern:
  one Zod schema drives (a) RHF validation, (b) shadcn Form UI, (c)
  API request typing, (d) DB insert typing via Drizzle. One file,
  end-to-end type safety.
- **Command palette as primary navigation.** Following Linear, teams
  wire `<Command>` (⌘K) as the main nav for power users. shadcn's
  Command primitive makes this a one-day build.
- **Skeleton-free loading via suspense + React Query.** Expert
  pattern: wrap DataTables and Dialogs in `<Suspense>` with shadcn
  `<Skeleton>` as fallback. React Query's `useSuspenseQuery` makes
  this first-class.
- **Composable layouts via Blocks.** Teams are moving from
  per-component adoption to full block adoption — `shadcn add
  dashboard-01` gives you a complete shell, and you edit from there.
- **Registry-native MCP servers.** Experimental: expose a shadcn
  registry as an MCP tool so AI agents can query and install
  components on behalf of the user. Not mainstream yet but the
  distribution model (URL → JSON manifest) is ideal for this.

**The frontier pattern to adopt now:**
1. Use `shadcn add` via Claude Code / Cursor — let the AI vendor the
   component, compose it, and wire up the form/query in one go.
2. Keep a single Zod schema as the truth for UI + API + DB.
3. Use blocks for new pages, not individual components.
4. Run `shadcn diff` weekly in CI; surface drift as a PR comment.
5. If you ship >2 apps, host your own registry from day one.

---
