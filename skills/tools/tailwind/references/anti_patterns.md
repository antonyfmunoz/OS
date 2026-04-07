# Tailwind CSS — Anti-Patterns (Real Failures)

These are the specific mistakes that break large React + Tailwind v4 apps.
Each entry = symptom, wrong code, correct code, why.

---

## 1. Dynamic class name construction

**Symptom:** Class works in dev, vanishes in production build.

```tsx
// WRONG — JIT scanner sees "bg-" + "-500" and cannot resolve
const color = venture.status === "active" ? "green" : "red";
<div className={`bg-${color}-500 text-${color}-900`} />

// WRONG — same problem with object key lookup that builds string
<div className={`text-${size}xl`} />
```

```tsx
// CORRECT — full class names in a lookup map
const STATUS_CLASSES = {
  active: "bg-green-500 text-green-900",
  paused: "bg-yellow-500 text-yellow-900",
  archived: "bg-red-500 text-red-900",
} as const;
<div className={STATUS_CLASSES[venture.status]} />
```

**Why:** Tailwind v4's content scanner is a regex-based text scan, not an
AST walk. It matches complete, contiguous class name tokens. A template
literal with a variable hole produces no complete token to match.
Safelists exist in v4 via `@source inline(...)` but are a last resort —
the lookup map is always better.

---

## 2. `@apply` abuse (rebuilding a component library in CSS)

**Symptom:** `src/styles/components.css` grows to 500 lines of `.btn`,
`.card`, `.input`, `.alert-primary`, etc. You're fighting Tailwind, not
using it. Style changes require round-trips to a CSS file that has all
the problems semantic CSS was supposed to have.

```css
/* WRONG — this is semantic CSS with extra steps */
.btn-primary {
  @apply px-4 py-2 bg-primary text-primary-foreground rounded-md
         hover:bg-primary/90 focus-visible:ring-2;
}
.btn-destructive {
  @apply px-4 py-2 bg-destructive text-destructive-foreground rounded-md
         hover:bg-destructive/90 focus-visible:ring-2;
}
/* ... 15 more variants ... */
```

```tsx
// CORRECT — extract a React component with CVA variants
// See examples.md recipe (f) for the full Button pattern
```

**Why:** The whole point of utility-first is that component extraction
happens in React, not CSS. CVA gives you typed, composable variants.
`@apply` chains are invisible to tailwind-merge, hard to override, and
re-introduce specificity wars. The ONLY legitimate `@apply` use is
global base resets for elements you can't attach a className to — see
examples.md recipe (h).

---

## 3. Variant explosion via boolean props instead of CVA

```tsx
// WRONG — every new prop doubles the conditional hell
<div
  className={cn(
    "rounded-md p-4",
    isActive && "bg-primary text-primary-foreground",
    isDanger && "bg-destructive text-destructive-foreground",
    isLarge && "text-lg p-6",
    isSmall && "text-sm p-2",
    isOutlined && "border border-border bg-transparent",
    isOutlined && isActive && "border-primary text-primary"
  )}
/>
```

```tsx
// CORRECT — one variant prop, explicit values, CVA handles compounds
const alertVariants = cva("rounded-md", {
  variants: {
    tone: { default: "bg-muted", primary: "bg-primary text-primary-foreground", danger: "bg-destructive text-destructive-foreground" },
    size: { sm: "p-2 text-sm", md: "p-4", lg: "p-6 text-lg" },
    outlined: { true: "border border-border bg-transparent" },
  },
  compoundVariants: [
    { outlined: true, tone: "primary", className: "border-primary text-primary" },
  ],
  defaultVariants: { tone: "default", size: "md" },
});
```

**Why:** Boolean-prop conditional chains become unreadable at 4+ options
and make typechecking mutual exclusion impossible. CVA's variant map
makes the API explicit, type-safe, and handles compound cases cleanly.

---

## 4. Inline arbitrary values as first resort

```tsx
// WRONG — arbitrary values scattered across 40 components
<div className="p-[17px] text-[15px] gap-[11px] w-[347px]" />
```

```tsx
// CORRECT — use the default scale, OR promote to @theme
<div className="p-4 text-sm gap-3 w-80" />

// If design truly needs a custom size, add it once in @theme:
// @theme { --spacing-18: 4.5rem; --text-sm-plus: 0.9375rem; }
```

**Why:** Arbitrary values defeat the constraint-based design benefit.
Twenty different paddings means you don't have a design system — you
have an inconsistent mess. Promote repeated one-offs to `@theme`; use
inline arbitrary values only for genuine one-offs (see examples.md (g)).

---

## 5. Unconditional `dark:` prefix on every color

```tsx
// WRONG — maintenance nightmare, double the classes
<div className="bg-white dark:bg-gray-900 text-gray-900 dark:text-white
                border-gray-200 dark:border-gray-800 hover:bg-gray-50
                dark:hover:bg-gray-800" />
```

```tsx
// CORRECT — use shadcn semantic tokens that flip automatically
<div className="bg-card text-card-foreground border-border hover:bg-accent" />
```

**Why:** shadcn's whole point is that `--card`, `--card-foreground`,
`--border` already have dark mode values defined under `.dark` in your
`index.css`. When `.dark` is toggled, those tokens resolve to different
colors. Writing `dark:` on every utility bypasses the entire token system
and makes theming changes require a sweeping find-and-replace.

---

## 6. Forgetting `tailwind-merge` when composing classes

```tsx
// WRONG — duplicate conflicting classes, last-in-stylesheet wins
function Badge({ className, ...props }) {
  return <span className={`bg-primary text-white px-2 ${className}`} {...props} />;
}

// Caller does: <Badge className="bg-red-500" />
// Result: BOTH bg-primary and bg-red-500 are in the class list.
// Which wins is non-deterministic (depends on Tailwind's internal order).
```

```tsx
// CORRECT — cn() calls twMerge which resolves conflicts
import { cn } from "@/lib/utils";
function Badge({ className, ...props }) {
  return <span className={cn("bg-primary text-white px-2", className)} {...props} />;
}
```

**Why:** Plain string concatenation leaves both classes in the DOM.
Tailwind generates CSS with a fixed internal utility order; which class
"wins" depends on that order, not on which you wrote last. `twMerge`
knows the conflict groups (e.g., all `bg-*` utilities conflict) and
keeps only the last one from each group.

---

## 7. Putting content-related classes inside `@apply`

```css
/* WRONG — @apply cannot express hover/focus/responsive cleanly */
.card-header {
  @apply text-lg font-bold;
  /* How do you add "hover:text-primary md:text-xl"?
     @apply has awkward variant syntax and loses specificity info. */
}
```

```tsx
// CORRECT — variants belong in JSX where they read naturally
<h3 className="text-lg font-bold hover:text-primary md:text-xl">
```

**Why:** Variant prefixes (`hover:`, `md:`, `dark:`, `group-hover:`) are
exactly what `@apply` is bad at. Keep variants in JSX where they compose
cleanly with state and responsive design.

---

## 8. Missing `@theme inline` for shadcn CSS variables

```css
/* WRONG — variable resolves at @theme scope, NOT at usage scope */
@theme {
  --color-primary: hsl(var(--primary));
}
/* Result: dark mode .dark override never applies. bg-primary stays
   light-mode color even when <html class="dark"> is set. */
```

```css
/* CORRECT — inline defers variable resolution to usage site */
@theme inline {
  --color-primary: hsl(var(--primary));
}
```

**Why:** Without `inline`, the `var(--primary)` is resolved when the
`@theme` block is processed, baking in whatever `:root` had at that time.
With `inline`, the reference stays literal in the generated CSS, so
`var(--primary)` resolves at the element's computed-style time — which
correctly picks up `.dark` overrides in the cascade.

---

## 9. Creating `tailwind.config.js` in a v4 project

```js
// WRONG — v4 silently ignores this file entirely
// tailwind.config.js
module.exports = { darkMode: "class", theme: { extend: { ... } } };
```

```css
/* CORRECT — everything lives in CSS in v4 */
@import "tailwindcss";
@custom-variant dark (&:is(.dark *));
@theme { --color-brand: #1a1a2e; }
```

**Why:** v4 has no JS config. `darkMode`, `content`, `theme.extend`,
`plugins`, `prefix` — all moved to CSS directives. A dev creating a
`tailwind.config.js` out of muscle memory gets a file that does nothing,
then wonders why their `darkMode: "class"` config has no effect.

---

## 10. Stale `tailwind-merge` version with v4 utilities

**Symptom:** `cn("size-8", "w-10")` keeps both classes because old
tailwind-merge doesn't know `size-*` conflicts with `w-*`/`h-*`.

**Fix:** Pin `tailwind-merge@^2.5` or later. For v4-only utilities
(`@container`, `bg-linear-*`, 3D transforms), verify the version in
tailwind-merge's CHANGELOG supports them before using.

---

## 11. `@source` pointed at `node_modules` blindly

```css
/* WRONG — scans all of node_modules, 10x build time */
@source "../../node_modules";
```

```css
/* CORRECT — narrow the scope to the specific package you need */
@source "../../node_modules/@lyfe/ui-components/dist";
```

**Why:** v4's automatic detection already skips `node_modules`. Only
add `@source` paths for packages that ship pre-compiled components
with Tailwind classes (rare). Scanning all of `node_modules` destroys
build performance.
