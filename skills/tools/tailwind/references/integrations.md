# Tailwind CSS — Integrations (EOS Stack)

How Tailwind v4 composes with the rest of the `saas/` frontend stack.
Each entry documents the contract: what each side provides, what must
never be broken, and where the seams are.

---

## React 18 / 19

**Contract:** Tailwind classes are applied via the `className` prop on
any JSX element. Tailwind is style-only; it has zero knowledge of React.

```tsx
<div className="flex items-center gap-4 p-4 rounded-lg border border-border" />
```

**Pattern — typed className prop on custom components:**

```tsx
import { cn } from "@/lib/utils";
import type { ComponentPropsWithoutRef } from "react";

interface StackProps extends ComponentPropsWithoutRef<"div"> {
  direction?: "row" | "col";
  gap?: 2 | 4 | 6 | 8;
}

export function Stack({ direction = "col", gap = 4, className, ...props }: StackProps) {
  const GAPS = { 2: "gap-2", 4: "gap-4", 6: "gap-6", 8: "gap-8" };
  return (
    <div
      className={cn(
        "flex",
        direction === "row" ? "flex-row" : "flex-col",
        GAPS[gap],
        className
      )}
      {...props}
    />
  );
}
```

Rules:
- ALWAYS accept `className` on public components and pass it to `cn()` last
- NEVER interpolate numeric props into class strings — use a lookup map
- Prefer `React.forwardRef` for shadcn-compatible components

---

## shadcn/ui

**Contract:** shadcn ships raw TSX source into `src/components/ui/`.
It depends on Tailwind utilities + CSS variables + `cn()` + CVA. shadcn
NEVER runs at build time — it's just code in your repo.

**Theming contract (critical):**
1. shadcn expects tokens like `--primary`, `--background`, `--muted`,
   `--border`, `--ring` defined as bare HSL triplets under `:root`
   and `.dark` selectors
2. Tailwind must expose them as color utilities via `@theme inline`
   (see examples.md recipe b)
3. Dark mode MUST use class strategy via `@custom-variant dark (&:is(.dark *))`
4. `cn()` must exist at `@/lib/utils` — shadcn components import it

**Never:**
- Edit vendored shadcn files directly for styling changes — change tokens
  in `index.css` instead
- Replace `cn()` with plain string concat
- Add `darkMode: "class"` JS config (v4 has no JS config)
- Use `hsl()` wrapper inside the `:root` vars — shadcn needs bare triplets
  so `bg-primary/80` opacity modifiers work

**Patching shadcn components:**
If you must override a shadcn default (e.g., make `Button` use `Space Grotesk`),
wrap it in your own component rather than editing the vendored file — this
keeps future shadcn updates applicable.

---

## Class Variance Authority (CVA)

**Contract:** CVA builds a typed function that maps variant props to
Tailwind class strings. Used inside shadcn-style components.

```ts
import { cva, type VariantProps } from "class-variance-authority";

const badgeVariants = cva(
  "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground",
        secondary: "bg-secondary text-secondary-foreground",
        destructive: "bg-destructive text-destructive-foreground",
        outline: "text-foreground border border-border",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

export type BadgeVariantProps = VariantProps<typeof badgeVariants>;
```

Rules:
- Base string goes first, variants second
- ALWAYS set `defaultVariants` (otherwise `variant={undefined}` produces
  no classes for that axis)
- Use `compoundVariants` for "when variant=X AND size=Y" rules
- Always pass `cva(...)` output through `cn()` so consumer `className`
  can override variant defaults

---

## tailwind-merge

**Contract:** `twMerge(classString)` keeps only the last class from
each conflict group. Pair with `clsx` via `cn()` so you can pass
conditionals, arrays, objects, and undefined safely.

```ts
// src/lib/utils.ts
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

Version pin: `tailwind-merge@^2.5` minimum for v4 utility awareness.
If you use extended v4 features (custom `@container` breakpoints,
custom prefix), configure `extendTailwindMerge({ ... })` once and
re-export.

---

## clsx

**Contract:** `clsx(...inputs)` serializes conditionals into a class
string. It does NOT resolve conflicts — that's `twMerge`'s job. Use
`clsx` alone only when you know there are no conflicts to merge.

```ts
// Both valid, both produce the same string:
clsx("flex", isActive && "text-primary", { "opacity-50": disabled });
clsx(["flex", isActive && "text-primary", disabled && "opacity-50"]);
```

Always prefer `cn()` over raw `clsx` in any component that accepts a
`className` prop from outside.

---

## Vite

**Contract:** `@tailwindcss/vite` is a first-party plugin that hooks
into Vite's dev server and build pipeline. It handles CSS parsing,
content scanning, HMR, and production optimization.

```ts
// vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
});
```

Rules:
- Use `@tailwindcss/vite`, NOT `@tailwindcss/postcss` in Vite projects
  (vite plugin is ~2x faster and has better HMR)
- Do not add a `postcss.config.js` — Vite plugin handles everything
- Content scanning is automatic; add `@source` in CSS only for external
  component libraries shipped as pre-compiled source

---

## TypeScript

**Contract:** Tailwind is plain strings from TS's perspective — no
type safety out of the box. Install the official VS Code extension
("Tailwind CSS IntelliSense") for autocomplete and hover previews.

**Tailwind IntelliSense v4 config:**

```json
// .vscode/settings.json
{
  "tailwindCSS.experimental.classRegex": [
    ["cva\\(([^)]*)\\)", "[\"'`]([^\"'`]*).*?[\"'`]"],
    ["cn\\(([^)]*)\\)", "[\"'`]([^\"'`]*).*?[\"'`]"]
  ],
  "tailwindCSS.classFunctions": ["cva", "cn", "clsx", "tw"]
}
```

This unlocks autocomplete inside `cva()` calls and `cn()` calls.

**Typed variant props via CVA:**

```tsx
import type { VariantProps } from "class-variance-authority";
type ButtonProps = VariantProps<typeof buttonVariants> &
  React.ButtonHTMLAttributes<HTMLButtonElement>;
```

`VariantProps` derives a union type from the CVA config, so TS catches
invalid variant names at compile time.

---

## React Hook Form + Zod (shadcn Form pattern)

**Contract:** shadcn's `<Form>`, `<FormField>`, `<FormItem>`,
`<FormLabel>`, `<FormControl>`, `<FormMessage>` components use Tailwind
utilities for layout and validation states. The integration is purely
visual — RHF handles state, shadcn handles styling, Tailwind handles
rendering.

```tsx
<Form {...form}>
  <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
    <FormField
      control={form.control}
      name="email"
      render={({ field }) => (
        <FormItem>
          <FormLabel>Email</FormLabel>
          <FormControl>
            <Input type="email" {...field} />
          </FormControl>
          <FormMessage />
        </FormItem>
      )}
    />
    <Button type="submit">Subscribe</Button>
  </form>
</Form>
```

Validation error styling is automatic: shadcn's `FormMessage` reads the
RHF error state and applies `text-destructive` via its own `cn()` call.
You don't style it manually.

---

## Remotion (video composition)

**Contract:** `@remotion/tailwind-v4` adds Tailwind v4 support to
Remotion's Webpack pipeline. Tailwind is used for STATIC layout only —
all animation happens through `useCurrentFrame()` + `interpolate()`,
never through Tailwind's `animate-*` or `transition-*` utilities.

```ts
// remotion.config.ts
import { Config } from "@remotion/cli/config";
import { enableTailwind } from "@remotion/tailwind-v4";
Config.overrideWebpackConfig(enableTailwind);
```

Rules:
- NEVER `animate-spin`, `animate-pulse`, `transition-*` in Remotion
- Fixed viewport means responsive breakpoints (`sm:`, `md:`) are irrelevant
- Use the large end of the type scale: `text-6xl`, `text-8xl`, `text-9xl`
- Dark backgrounds render more reliably than light ones in compressed video
