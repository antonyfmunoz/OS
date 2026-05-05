# Tailwind CSS — Concrete EOS Examples

All recipes are copy-pasteable for the `saas/` React 18 + TS + Vite + shadcn/ui
stack. Dark mode uses the class strategy. Class composition uses `cn()`.

---

## (a) Vite + Tailwind v4 setup for React + TS

```bash
npm install tailwindcss@^4 @tailwindcss/vite
npm install clsx tailwind-merge class-variance-authority
```

```ts
// vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
});
```

```tsx
// src/main.tsx
import React from "react";
import ReactDOM from "react-dom/client";
import "./index.css";
import { App } from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(<App />);
```

---

## (b) `src/index.css` — @theme with shadcn CSS variables (HSL triplets)

This is the canonical shadcn + Tailwind v4 theming contract. Preserve it
exactly — touching any of these selectors breaks opacity modifiers or
dark mode or both.

```css
@import "tailwindcss";

/* Dark mode via class on <html> — required for shadcn toggle to work */
@custom-variant dark (&:is(.dark *));

/* Shadcn tokens as bare HSL triplets (no hsl() wrapper) */
:root {
  --background: 0 0% 100%;
  --foreground: 240 10% 3.9%;
  --card: 0 0% 100%;
  --card-foreground: 240 10% 3.9%;
  --popover: 0 0% 100%;
  --popover-foreground: 240 10% 3.9%;
  --primary: 240 5.9% 10%;
  --primary-foreground: 0 0% 98%;
  --secondary: 240 4.8% 95.9%;
  --secondary-foreground: 240 5.9% 10%;
  --muted: 240 4.8% 95.9%;
  --muted-foreground: 240 3.8% 46.1%;
  --accent: 240 4.8% 95.9%;
  --accent-foreground: 240 5.9% 10%;
  --destructive: 0 84.2% 60.2%;
  --destructive-foreground: 0 0% 98%;
  --border: 240 5.9% 90%;
  --input: 240 5.9% 90%;
  --ring: 240 5.9% 10%;
  --radius: 0.5rem;
}

.dark {
  --background: 240 10% 3.9%;
  --foreground: 0 0% 98%;
  --card: 240 10% 3.9%;
  --card-foreground: 0 0% 98%;
  --popover: 240 10% 3.9%;
  --popover-foreground: 0 0% 98%;
  --primary: 0 0% 98%;
  --primary-foreground: 240 5.9% 10%;
  --secondary: 240 3.7% 15.9%;
  --secondary-foreground: 0 0% 98%;
  --muted: 240 3.7% 15.9%;
  --muted-foreground: 240 5% 64.9%;
  --accent: 240 3.7% 15.9%;
  --accent-foreground: 0 0% 98%;
  --destructive: 0 62.8% 30.6%;
  --destructive-foreground: 0 0% 98%;
  --border: 240 3.7% 15.9%;
  --input: 240 3.7% 15.9%;
  --ring: 240 4.9% 83.9%;
}

/* @theme inline references the :root vars WITHOUT re-wrapping in hsl().
   This is what lets bg-primary/80 apply the /80 opacity modifier. */
@theme inline {
  --color-background: hsl(var(--background));
  --color-foreground: hsl(var(--foreground));
  --color-card: hsl(var(--card));
  --color-card-foreground: hsl(var(--card-foreground));
  --color-popover: hsl(var(--popover));
  --color-popover-foreground: hsl(var(--popover-foreground));
  --color-primary: hsl(var(--primary));
  --color-primary-foreground: hsl(var(--primary-foreground));
  --color-secondary: hsl(var(--secondary));
  --color-secondary-foreground: hsl(var(--secondary-foreground));
  --color-muted: hsl(var(--muted));
  --color-muted-foreground: hsl(var(--muted-foreground));
  --color-accent: hsl(var(--accent));
  --color-accent-foreground: hsl(var(--accent-foreground));
  --color-destructive: hsl(var(--destructive));
  --color-destructive-foreground: hsl(var(--destructive-foreground));
  --color-border: hsl(var(--border));
  --color-input: hsl(var(--input));
  --color-ring: hsl(var(--ring));

  --radius-sm: calc(var(--radius) - 4px);
  --radius-md: calc(var(--radius) - 2px);
  --radius-lg: var(--radius);

  --font-sans: "Inter", ui-sans-serif, system-ui, sans-serif;
  --font-display: "Space Grotesk", sans-serif;
}

@layer base {
  * { @apply border-border; }
  body { @apply bg-background text-foreground font-sans antialiased; }
}
```

Result: `bg-primary`, `text-muted-foreground`, `bg-primary/80`,
`dark:bg-background` all work, and toggling `.dark` on `<html>` flips the
entire palette.

---

## (c) Dark mode toggle with class strategy

```tsx
// src/lib/theme.ts
export type Theme = "light" | "dark" | "system";

export function applyTheme(theme: Theme) {
  const isDark =
    theme === "dark" ||
    (theme === "system" &&
      window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.classList.toggle("dark", isDark);
  if (theme === "system") localStorage.removeItem("theme");
  else localStorage.setItem("theme", theme);
}

export function initTheme() {
  const stored = (localStorage.getItem("theme") as Theme) ?? "system";
  applyTheme(stored);
}
```

```html
<!-- index.html — inline in <head> to prevent FOUC -->
<script>
  (function () {
    const t = localStorage.getItem("theme");
    const dark =
      t === "dark" ||
      (!t && window.matchMedia("(prefers-color-scheme: dark)").matches);
    document.documentElement.classList.toggle("dark", dark);
  })();
</script>
```

```tsx
// src/components/ThemeToggle.tsx
import { Moon, Sun } from "lucide-react";
import { applyTheme } from "@/lib/theme";
import { Button } from "@/components/ui/button";

export function ThemeToggle() {
  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={() => {
        const isDark = document.documentElement.classList.contains("dark");
        applyTheme(isDark ? "light" : "dark");
      }}
    >
      <Sun className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
      <Moon className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
    </Button>
  );
}
```

---

## (d) Responsive card grid (mobile-first)

```tsx
export function VentureGrid({ ventures }: { ventures: Venture[] }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {ventures.map((v) => (
        <article
          key={v.id}
          className="rounded-lg border border-border bg-card p-6 shadow-sm
                     transition-shadow hover:shadow-md"
        >
          <h3 className="text-lg font-semibold text-card-foreground">
            {v.name}
          </h3>
          <p className="mt-2 line-clamp-3 text-sm text-muted-foreground">
            {v.description}
          </p>
        </article>
      ))}
    </div>
  );
}
```

Mobile-first means the base class applies at all sizes; prefixed classes
(`sm:`, `lg:`) only override at that breakpoint and larger. Never reach
for `max-sm:` unless you have a deliberate reason.

---

## (e) Container queries for a dashboard widget

Container queries are preferred over viewport queries for any component
that can appear in a sidebar, a grid cell, or full-width — the component
adapts to its actual container width.

```tsx
export function MetricCard({ label, value, delta }: MetricCardProps) {
  return (
    <div className="@container rounded-lg border border-border bg-card p-4">
      <div className="flex flex-col @sm:flex-row @sm:items-center @sm:justify-between">
        <p className="text-sm font-medium text-muted-foreground">{label}</p>
        <span
          className={cn(
            "text-xs font-semibold",
            delta >= 0 ? "text-emerald-500" : "text-destructive"
          )}
        >
          {delta >= 0 ? "+" : ""}
          {delta}%
        </span>
      </div>
      <p className="mt-2 text-2xl @sm:text-3xl @lg:text-4xl font-bold">
        {value}
      </p>
    </div>
  );
}
```

`@container` on the wrapper opts into container queries for its descendants.
`@sm:`, `@md:`, `@lg:` target the container's inline size, not the viewport.

---

## (f) `cn()` + CVA variant composition (shadcn Button pattern)

```ts
// src/lib/utils.ts
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

```tsx
// src/components/ui/button.tsx
import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium " +
    "transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring " +
    "disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        destructive:
          "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline:
          "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
        secondary:
          "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        ref={ref}
        className={cn(buttonVariants({ variant, size, className }))}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";
```

`cn()` at the end means consumer-provided `className` wins over variant
defaults. Without `cn()` (using plain string concat), both `bg-primary`
and a consumer's `bg-red-500` would remain in the class list and whichever
came later in the stylesheet would win — non-deterministic.

---

## (g) Arbitrary values with justification

Arbitrary values are the escape hatch for one-offs. Use them when:

```tsx
// Pixel-perfect value from design that will never repeat
<div className="top-[73px]" /> // header height offset, one-off

// CSS variable reference
<div className="max-h-[var(--header-height)]" />

// calc() expression that has no spacing-scale equivalent
<div className="w-[calc(100%-2rem)]" />

// Arbitrary selector (rare, but legitimate)
<ul className="[&>li:nth-child(odd)]:bg-muted/30">
```

Do NOT use arbitrary values for anything that SHOULD live in `@theme`.
If you write `text-[#1a1a2e]` three times, promote it to
`--color-brand: #1a1a2e` inside `@theme` and use `text-brand`.

---

## (h) Legitimate `@apply` use — native form field reset

`@apply` is discouraged in v4 but remains legitimate for styling elements
you cannot attach a className to — native form controls that ship with
user agent stylesheets we need to override globally across the app.

```css
@layer base {
  input[type="text"],
  input[type="email"],
  input[type="password"],
  textarea,
  select {
    @apply rounded-md border border-input bg-background px-3 py-2 text-sm
           ring-offset-background placeholder:text-muted-foreground
           focus-visible:outline-none focus-visible:ring-2
           focus-visible:ring-ring focus-visible:ring-offset-2
           disabled:cursor-not-allowed disabled:opacity-50;
  }
}
```

This is a cross-cutting base reset, not a component — extracting a React
component does not help because native inputs appear in content we do not
control (rendered markdown, email previews, etc.).

---

## (i) Print styles

```tsx
<article className="p-8 print:p-0 print:text-black">
  <header className="mb-6 print:mb-2">
    <h1 className="text-3xl font-bold print:text-2xl">{invoice.number}</h1>
  </header>
  <nav className="flex gap-4 print:hidden">
    <button>Download</button>
    <button>Share</button>
  </nav>
  <table className="w-full print:border print:border-black">
    {/* rows */}
  </table>
</article>
```

`print:` variant targets `@media print`. Combine with `print:hidden` to
strip interactive UI from printed output.
