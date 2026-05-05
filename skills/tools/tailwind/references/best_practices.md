# Tailwind CSS — Creator-Level Best Practices
Source: https://tailwindcss.com/docs
API Version: v4 (CSS-first configuration)
SDK Version: tailwindcss 4.0.0
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication

N/A — Tailwind CSS is a build-time CSS framework with no authentication layer.
It has no API keys, no OAuth, no tokens, no service accounts. It processes
source files at build time and produces static CSS output. The only "credentials"
are npm registry access for installing the package, which uses standard npm auth.

In EOS: Tailwind is installed as a project dependency via `npm install tailwindcss`.
No secrets in `.env`. No runtime authentication.

---

## Core Operations with Exact Signatures

Tailwind CSS is not an API — it is a build tool and CSS framework. "Operations"
are CSS directives and utility class patterns.

### CSS Directives (v4)

```css
/* Entry point — imports all of Tailwind */
@import "tailwindcss";

/* Define design tokens (replaces tailwind.config.js theme) */
@theme {
  --color-primary: #1a1a2e;
  --color-secondary: #16213e;
  --color-accent: #e94560;
  --font-sans: "Inter", ui-sans-serif, system-ui, sans-serif;
  --font-display: "Space Grotesk", sans-serif;
  --breakpoint-3xl: 1920px;
  --spacing-18: 4.5rem;
  --radius-xl: 1rem;
}

/* Define custom utilities (replaces @layer utilities + @apply) */
@utility container-narrow {
  max-width: 48rem;
  margin-inline: auto;
  padding-inline: 1rem;
}

/* Define custom variants */
@variant hocus (&:hover, &:focus);
@variant pointer-fine (@media (pointer: fine));

/* Add content sources for class detection */
@source "../components";
@source "../../node_modules/@my-lib/ui";

/* Import plugins */
@plugin "@tailwindcss/typography";
@plugin "@tailwindcss/forms";
```

### Utility Class Syntax

```
{variant}:{property}-{value}

Examples:
  hover:bg-blue-600        — on hover, background blue-600
  md:grid-cols-3           — at md breakpoint, 3 grid columns
  dark:text-white          — in dark mode, white text
  group-hover:opacity-100  — when parent .group is hovered
  @lg:flex-row             — container query: at lg container width
  not-last:border-b        — all except last child get bottom border
```

### Arbitrary Value Syntax

```
{property}-[{value}]

Examples:
  w-[calc(100%-2rem)]
  bg-[#1a1a2e]
  grid-cols-[200px_1fr_200px]
  text-[clamp(1rem,2.5vw,2rem)]
  top-[var(--header-height)]
```

### Arbitrary Variant Syntax

```
[{selector}]:{utility}

Examples:
  [&>svg]:w-5              — direct child SVGs width 5
  [&_p]:mt-4               — descendant paragraphs margin-top 4
  [@supports(grid)]:grid   — feature query
```

---

## Pagination Patterns

N/A — Tailwind CSS is a build tool, not a data API. There is no pagination.
The closest analogue is content detection: Tailwind v4 automatically scans
all files in the project directory for utility class usage. If content spans
multiple directories, use `@source` directives to add paths.

---

## Rate Limits

Tailwind has no API rate limits. The equivalent concern is **build performance**.

### Build Performance Characteristics

| Scenario | v3 (PostCSS) | v4 (Lightning CSS) |
|----------|-------------|-------------------|
| Initial build (1000 utilities) | ~800ms | ~100ms |
| Incremental rebuild | ~200ms | ~5ms |
| Full project scan | Configured via content[] | Automatic |
| CSS output size (production) | Purged to used classes | Same — automatic |

### What Slows Builds

- **Massive `@source` scope** — scanning node_modules or unrelated dirs
- **Complex `@apply` chains** — each `@apply` resolves at build time (deprecated in v4)
- **Thousands of arbitrary values** — each generates a unique class
- **Unused plugins** — typography/forms plugins add overhead even if unused

### Optimization

- Let v4's automatic detection work — don't add unnecessary `@source` directives
- Use `@tailwindcss/vite` for Vite projects (fastest integration)
- For Remotion/Webpack: `@remotion/tailwind-v4` handles the integration
- Production builds automatically tree-shake unused utilities

---

## Error Codes and Recovery

Tailwind errors manifest as build failures, not HTTP status codes.

### Common Build Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `Cannot find module 'tailwindcss'` | Not installed | `npm install tailwindcss` |
| `@import "tailwindcss" must be first` | CSS rules before import | Move `@import` to top |
| `Unknown at-rule @theme` | Using v4 syntax with v3 installed | Upgrade to v4 |
| `Unknown at-rule @utility` | Same as above | Upgrade to v4 |
| `Class not found` (no styles applied) | File not in detection scope | Add `@source` directive |
| `PostCSS plugin tailwindcss not found` | Wrong build integration | Use `@tailwindcss/vite` or `@tailwindcss/postcss` |
| Styles not updating on save | Stale build cache | Restart dev server |
| `@apply` of non-existing utility | Class doesn't exist or typo | Check class name spelling |

### Recovery Strategies

- **Classes not generating**: Check if the file is within Tailwind's scan scope.
  Add `@source "../path"` if needed. Restart dev server.
- **Styles look wrong in production**: Ensure production build runs (not dev).
  Check for dynamic class name construction (Tailwind can't detect `bg-${color}-500`).
- **Plugin errors**: Verify plugin version matches Tailwind major version.
  v4 plugins use `@plugin` directive, not `plugins: []` in JS config.

---

## SDK Idioms

Tailwind v4 represents a paradigm shift from v3. The "SDK" is the CSS-based
configuration system itself.

### v3 (JavaScript config — LEGACY, do not use in EOS)
```javascript
// tailwind.config.js — v3 pattern, NOT used in EOS
module.exports = {
  content: ['./src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: { brand: '#1a1a2e' },
    },
  },
  plugins: [require('@tailwindcss/typography')],
}
```

### v4 (CSS config — CURRENT, use this in EOS)
```css
/* src/index.css — v4 pattern */
@import "tailwindcss";

@theme {
  --color-brand: #1a1a2e;
}

@plugin "@tailwindcss/typography";
```

### Key v3 → v4 Migration Map

| v3 Pattern | v4 Equivalent |
|-----------|--------------|
| `tailwind.config.js` | `@theme {}` in CSS |
| `content: [...]` | Automatic (or `@source`) |
| `theme.extend.colors` | `--color-{name}: {value}` in `@theme` |
| `theme.extend.fontFamily` | `--font-{name}: {value}` in `@theme` |
| `theme.extend.spacing` | `--spacing-{name}: {value}` in `@theme` |
| `theme.extend.screens` | `--breakpoint-{name}: {value}` in `@theme` |
| `@layer utilities { .foo { @apply ... } }` | `@utility foo { ... }` |
| `plugins: [require('...')]` | `@plugin "..."` |
| `darkMode: 'class'` | `@variant dark (&:where(.dark, .dark *))` |
| `prefix: 'tw-'` | `@import "tailwindcss" prefix(tw)` |

### Build Integration per Framework

| Framework | Package | Setup |
|-----------|---------|-------|
| Vite | `@tailwindcss/vite` | Add to `vite.config.ts` plugins array |
| PostCSS | `@tailwindcss/postcss` | Add to `postcss.config.js` |
| Webpack | `@tailwindcss/postcss` | Via PostCSS loader |
| Remotion | `@remotion/tailwind-v4` | `Config.overrideWebpackConfig(enableTailwind)` |
| CLI | `@tailwindcss/cli` | `npx @tailwindcss/cli -i input.css -o output.css` |

---

## Anti-Patterns

### 1. Constructing class names dynamically
```tsx
// WRONG — Tailwind cannot detect these at build time
const color = "blue";
<div className={`bg-${color}-500`} />

// CORRECT — use complete class names
const colorClasses = {
  blue: "bg-blue-500",
  red: "bg-red-500",
  green: "bg-green-500",
};
<div className={colorClasses[color]} />
```

### 2. Using @apply for everything
```css
/* WRONG — defeats the purpose of utility-first */
.btn {
  @apply px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600;
}

/* CORRECT in v4 — extract a component in React */
/* Or use @utility for truly reusable patterns */
@utility btn-primary {
  padding: 0.5rem 1rem;
  background-color: var(--color-blue-500);
  color: white;
  border-radius: var(--radius-md);
}
```

### 3. Creating a tailwind.config.js in a v4 project
```
WRONG: Creating tailwind.config.js — v4 ignores it entirely
CORRECT: Put all configuration in CSS via @theme, @utility, @variant
```

### 4. Overusing arbitrary values
```html
<!-- WRONG — creates non-reusable one-offs -->
<div class="w-[347px] h-[219px] mt-[13px] p-[7px]">

<!-- CORRECT — use the spacing scale or define in @theme -->
<div class="w-80 h-56 mt-3 p-2">

<!-- If you truly need a custom value, add it to @theme -->
```

### 5. Not extracting repeated patterns into components
```tsx
// WRONG — duplicating 15 classes across 20 instances
{items.map(item => (
  <div className="flex items-center gap-3 p-4 rounded-lg border border-gray-200
                  hover:border-gray-300 transition-colors bg-white shadow-sm">
    {item.name}
  </div>
))}

// CORRECT — extract a component
function Card({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3 p-4 rounded-lg border border-gray-200
                    hover:border-gray-300 transition-colors bg-white shadow-sm">
      {children}
    </div>
  );
}
```

### 6. Using Tailwind animations in Remotion
```tsx
// WRONG — non-deterministic frame output
<div className="animate-spin">

// CORRECT — frame-based animation
const frame = useCurrentFrame();
const rotation = interpolate(frame, [0, 30], [0, 360]);
<div style={{ transform: `rotate(${rotation}deg)` }}>
```

### 7. Importing Tailwind via JS instead of CSS (v4)
```
WRONG: require('tailwindcss') in a PostCSS config and expecting v4 features
CORRECT: @import "tailwindcss" in your CSS file as the entry point
```

---

## Data Model

Tailwind's "data model" is its design token system. In v4, tokens are CSS
custom properties organized by namespace.

### Token Namespaces

| Namespace | CSS Variable Pattern | Example |
|-----------|---------------------|---------|
| Colors | `--color-{name}` | `--color-brand: #1a1a2e` |
| Fonts | `--font-{name}` | `--font-sans: "Inter", sans-serif` |
| Spacing | `--spacing-{name}` | `--spacing-18: 4.5rem` |
| Breakpoints | `--breakpoint-{name}` | `--breakpoint-3xl: 1920px` |
| Radii | `--radius-{name}` | `--radius-xl: 1rem` |
| Shadows | `--shadow-{name}` | `--shadow-soft: 0 2px 8px ...` |
| Animations | `--animate-{name}` | `--animate-fade-in: fade-in 0.5s` |
| Z-index | `--z-{name}` | `--z-modal: 100` |
| Opacity | `--opacity-{name}` | `--opacity-muted: 0.6` |

### Default Spacing Scale (rem-based, 1rem = 16px)

The scale is linear: each unit = 0.25rem = 4px.
`p-1` = 4px, `p-2` = 8px, `p-4` = 16px, `p-8` = 32px, `p-16` = 64px.

### Default Breakpoints

| Name | Min-width | Typical device |
|------|-----------|---------------|
| sm | 640px | Large phone landscape |
| md | 768px | Tablet |
| lg | 1024px | Laptop |
| xl | 1280px | Desktop |
| 2xl | 1536px | Large desktop |

### Color Scale

Each color has shades 50-950:
`50` (lightest) → `100` → `200` → `300` → `400` → `500` (base) →
`600` → `700` → `800` → `900` → `950` (darkest).

v4 uses OKLCH color space for perceptual uniformity across the scale.

---

## Webhooks and Events

N/A — Tailwind CSS is a build-time tool with no webhook or event system.
File watching during development is handled by the build tool integration
(Vite, Webpack, or CLI), not by Tailwind itself.

---

## Limits

### Class Name Limits
- No hard limit on number of utility classes per element
- No hard limit on total utilities in a project
- Practical limit: readability degrades past ~15 classes on one element
- Extract to components when a class list exceeds one line

### CSS Output Size
- Development: full utility sheet can be 3-5MB (includes all possible classes)
- Production: tree-shaken to only used classes, typically 5-30KB gzipped
- v4 is more aggressive at tree-shaking than v3

### @theme Limits
- Custom properties defined in @theme must follow the namespace convention
- Recursive/circular variable references cause build failure
- Maximum nesting depth in CSS is browser-limited, not Tailwind-limited

### Browser Support
- v4 requires browsers with CSS custom properties support (all modern browsers)
- OKLCH colors: Chrome 111+, Firefox 113+, Safari 15.4+
- Container queries: Chrome 105+, Firefox 110+, Safari 16+
- `@starting-style`: Chrome 117+, Firefox 129+, Safari 17.5+

---

## Cost Model

Tailwind CSS is **free and open source** under the MIT license.

- Core framework: free forever
- Official plugins (`@tailwindcss/typography`, `@tailwindcss/forms`, `@tailwindcss/container-queries`): free
- Tailwind UI (component library): paid — $299 one-time for all components
- Headless UI (unstyled components): free
- Heroicons (icon set): free

No per-build costs, no usage metering, no API fees.
The only cost is developer time learning and applying the framework.

In EOS: zero cost. Using the free core framework and free plugins only.

---

## Version Pinning

### Current versions in EOS
- `tailwindcss`: 4.0.0 (Remotion project)
- `@remotion/tailwind-v4`: 4.0.436 (Remotion-specific adapter)

### Version strategy
- Pin exact versions in package.json (no `^` for Tailwind major version)
- v4.x releases are backward compatible within the major version
- v3 → v4 is a breaking change (config format, default palette, behavior)

### Deprecations in v4
- `tailwind.config.js` / `tailwind.config.ts` — replaced by `@theme` in CSS
- `@apply` directive — still works but discouraged, use `@utility` instead
- `content: [...]` configuration — replaced by automatic detection + `@source`
- JavaScript plugin API (`plugin()` function) — replaced by `@plugin` directive
- `darkMode: 'class'` config — replaced by `@variant dark` in CSS
- `prefix` config — replaced by `@import "tailwindcss" prefix(tw)`
- PostCSS-based transforms — replaced by Lightning CSS (PostCSS adapter available for compat)

### v3 → v4 Migration Path
1. Remove `tailwind.config.js`
2. Replace `@tailwind base; @tailwind components; @tailwind utilities;` with `@import "tailwindcss";`
3. Move `theme.extend` values to `@theme {}` block with CSS variable syntax
4. Convert `plugins: [require('...')]` to `@plugin "..."`
5. Replace `@layer utilities { .foo { @apply ... } }` with `@utility foo { ... }`
6. Switch build integration from PostCSS plugin to framework-native (`@tailwindcss/vite`)
7. Test — automatic content detection should pick up all class usage
8. Run `npx @tailwindcss/upgrade` for automated assistance

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

Tailwind was created by Adam Wathan because he found that "semantic CSS" (naming
things like `.author-bio`, `.card`, `.nav-links`) creates a false abstraction layer
that doesn't actually reduce complexity — it just moves it from HTML to CSS while
creating a naming problem.

### Core design philosophy
- **Utility-first, not utility-only** — start with utilities, extract components
  when repetition emerges. The extraction point is React components, not CSS classes.
- **Constraint-based design** — the spacing scale (4px increments), color palette,
  and type scale create a finite design space. This makes designs consistent by
  default and inconsistent by explicit choice (arbitrary values).
- **Build-time, not runtime** — Tailwind generates CSS at build time, not in the
  browser. Zero runtime cost. The HTML is larger but the CSS is smaller.
- **Co-location over separation** — styles live in the markup, next to the structure
  they affect. This is intentional — the team believes the "separation of concerns"
  between HTML and CSS is a false separation because they always change together.

### Conscious tradeoffs
- **Ugly HTML** — class lists are long and hard to read. The tradeoff is that you
  never have to name things, never have to navigate between files, and refactoring
  is purely local.
- **No cascade** — utilities are flat, not cascading. This eliminates specificity
  wars but means you can't style deeply nested elements from a parent class.
- **Framework lock-in** — Tailwind class names are non-standard CSS. Migrating away
  means rewriting every className. The mitigation is that Tailwind's utility names
  map 1:1 to CSS properties, so the knowledge transfers even if the syntax doesn't.

### What Tailwind is NOT
- Not a component library (that's shadcn/ui, Headless UI)
- Not a design system (it's a design system toolkit)
- Not a CSS preprocessor (it doesn't extend CSS syntax — v4 IS CSS)
- Not runtime styling (it's build-time — unlike CSS-in-JS solutions)

---

## Problem-Solution Map and Hidden Capabilities

### Problem → Solution Map

| Problem | Tailwind Solution |
|---------|------------------|
| Consistent spacing across app | Use the spacing scale (p-4, m-6, gap-8) — never arbitrary pixels |
| Responsive layout | Mobile-first breakpoints (sm:, md:, lg:) |
| Dark mode | `dark:` variant (automatic via prefers-color-scheme) |
| Component-scoped responsive | Container queries (`@container`, `@sm:`, `@lg:`) |
| Brand colors across app | `@theme { --color-brand: ... }` then `bg-brand`, `text-brand` |
| Hover/focus/active states | State variants (`hover:`, `focus:`, `active:`) |
| Complex selectors | Arbitrary variants `[&>svg]:w-5`, `[&:nth-child(odd)]:bg-gray-50` |
| Reusable utility patterns | `@utility` directive for custom utilities |
| Conditional class application | Use `clsx` or `cn()` helper from shadcn/ui |
| Design token management | `@theme` block = single source of truth |

### Hidden Capabilities

1. **`@variant` composability** — define a custom variant once, compose it with
   any utility: `@variant hocus (&:hover, &:focus);` then use `hocus:bg-blue-500`.

2. **Negative values** — prefix with dash: `-mt-4` for negative margin-top.
   Works with any spacing utility.

3. **`group-*` and `peer-*` for parent/sibling state** — style a child based on
   parent hover without JS: `group-hover:opacity-100`. Peer variant styles based
   on sibling state: `peer-checked:bg-blue-500`.

4. **`@starting-style` for entry animations** — animate elements when they first
   appear in the DOM, no JS needed. Combine with `transition-*` utilities.

5. **`size-*` shorthand** — `size-8` sets both width and height to 2rem.
   Cleaner than `w-8 h-8`.

6. **`divide-*` for bordered lists** — `divide-y divide-gray-200` adds borders
   between children without styling first/last differently.

7. **`@theme inline`** — define theme values that generate CSS variables but don't
   generate utility classes, for values you only need as variables.

---

## Operational Behavior and Edge Cases

### Hot reload quirks
- Adding a new utility class to JSX: detected instantly by dev server
- Adding a class that requires a new `@source` path: requires dev server restart
- Modifying `@theme` values: hot reloads but may flash unstyled content briefly

### Class order does NOT determine specificity
```html
<!-- These produce the SAME result — last class does NOT win -->
<div class="bg-red-500 bg-blue-500">
<!-- Tailwind uses CSS layers, so specificity is flat -->
<!-- The "last in stylesheet" wins, which depends on Tailwind's internal order -->
<!-- NEVER rely on class order for override behavior -->
```

### Purging edge cases
- Classes in template literals are detected: `` `text-${size}` `` — NO, this fails
- Classes in comments ARE detected (Tailwind scans raw text, not AST)
- Classes in `data-*` attributes ARE detected
- Classes in JSON files ARE detected if the file is in scope

### Dark mode with class strategy
By default, v4 uses `prefers-color-scheme` (OS-level). To use a `.dark` class
on `<html>` for manual toggle:
```css
@variant dark (&:where(.dark, .dark *));
```

### Z-index stacking
Tailwind's default z-index values are: 0, 10, 20, 30, 40, 50, auto.
These are intentionally sparse to leave room for intermediate values.
Use `z-[60]` or define custom in `@theme` for app-specific layers.

---

## Ecosystem Position and Composition

### Where Tailwind sits in the stack
```
Design Tokens (Figma/brand guide)
    ↓
@theme block (Tailwind CSS config)
    ↓
Utility Classes (layout, spacing, color, typography)
    ↓
Component Library (shadcn/ui, Headless UI)
    ↓
Application UI (React components)
```

### Natural complements in EOS
| Tool | Role | Integration |
|------|------|-------------|
| React | Component framework | className prop carries Tailwind utilities |
| shadcn/ui | Component library | Built on Tailwind, uses `cn()` for class merging |
| Vite | Build tool | `@tailwindcss/vite` for native integration |
| Remotion | Video framework | `@remotion/tailwind-v4` for Webpack integration |
| clsx/tailwind-merge | Class merging | `cn()` helper resolves conflicting utilities |
| Heroicons | Icons | Designed for Tailwind sizing (w-5 h-5) |
| Headless UI | Accessible primitives | Styled entirely with Tailwind utilities |

### Forced integrations to avoid
- **CSS Modules + Tailwind** — they solve the same problem differently, combining creates confusion
- **styled-components + Tailwind** — runtime CSS-in-JS conflicts with build-time utilities
- **Bootstrap + Tailwind** — competing utility class names and reset styles clash

### The `cn()` pattern (critical for shadcn/ui)
```typescript
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Usage: merges and deduplicates Tailwind classes
cn("px-4 py-2 bg-blue-500", isActive && "bg-blue-700", className)
```

---

## Trajectory and Evolution

### v4 trajectory (current)
- CSS-first configuration is the future — JS config will not return
- Lightning CSS engine adoption across the ecosystem
- Deeper CSS spec integration (container queries, `@starting-style`, `@scope`)
- Plugin ecosystem migrating from JS API to `@plugin` CSS directive

### What's gaining investment
- **Container queries** — Tailwind is betting on container-responsive design
  over viewport-responsive as the primary layout paradigm
- **CSS-native features** — as browsers add features, Tailwind wraps them
  as utilities rather than inventing custom solutions
- **Oxide engine** — the Rust-based core that powers v4's performance

### What's being de-emphasized
- `@apply` — actively discouraged, may be removed in future major version
- JavaScript configuration — supported only for backward compat
- PostCSS plugin — the `@tailwindcss/postcss` adapter exists but native
  framework integrations are preferred
- Complex JS plugin API — moving toward CSS-native extensibility

### Signals for future direction
- Adam Wathan's emphasis on "Tailwind IS CSS" — v4 is intentionally
  less of a framework and more of a CSS authoring tool
- Tailwind UI continues as the primary revenue source — the framework
  stays free, components are the business model
- Catalyst (React component library) signals deeper investment in the
  React component ecosystem

---

## Conceptual Model and Solution Recipes

### Mental Model

Think of Tailwind as a **constrained design language**:
- **Nouns** = design tokens (@theme values: colors, spacing, fonts, breakpoints)
- **Verbs** = utilities (bg-, text-, flex, grid, p-, m-, w-, h-)
- **Adjectives** = variants (hover:, dark:, md:, @lg:, group-hover:)
- **Sentences** = `className="verb-noun adjective:verb-noun adjective:verb-noun"`

A styled element is a sentence: `"flex items-center gap-4 p-6 bg-white dark:bg-gray-900 rounded-xl shadow-sm hover:shadow-md transition-shadow"`

### Recipe 1: Responsive Card Grid (saas/ pattern)
```tsx
<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 p-6">
  {items.map(item => (
    <div key={item.id}
         className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm
                    hover:shadow-md transition-shadow border border-gray-100
                    dark:border-gray-700">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
        {item.title}
      </h3>
      <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
        {item.description}
      </p>
    </div>
  ))}
</div>
```

### Recipe 2: Form with Validation States
```tsx
<label className="block">
  <span className="text-sm font-medium text-gray-700 dark:text-gray-200">
    Email
  </span>
  <input
    type="email"
    className={cn(
      "mt-1 block w-full rounded-lg border px-3 py-2 text-sm",
      "focus:outline-none focus:ring-2",
      hasError
        ? "border-red-500 focus:ring-red-200 dark:focus:ring-red-800"
        : "border-gray-300 focus:ring-blue-200 dark:border-gray-600
           dark:focus:ring-blue-800"
    )}
  />
  {hasError && (
    <p className="mt-1 text-xs text-red-500">{errorMessage}</p>
  )}
</label>
```

### Recipe 3: Remotion Video Frame Layout
```tsx
const MyScene: React.FC = () => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <div className="flex h-full w-full items-center justify-center bg-gray-950">
      <div style={{ opacity }} className="text-center">
        <h1 className="text-7xl font-bold text-white tracking-tight">
          Initiate Arena
        </h1>
        <p className="mt-4 text-2xl text-gray-400">
          Your business operating system
        </p>
      </div>
    </div>
  );
};
```

### Recipe 4: Navigation with Active State
```tsx
<nav className="flex items-center gap-1 rounded-lg bg-gray-100 p-1
                dark:bg-gray-800">
  {tabs.map(tab => (
    <button
      key={tab.id}
      className={cn(
        "rounded-md px-4 py-2 text-sm font-medium transition-colors",
        activeTab === tab.id
          ? "bg-white text-gray-900 shadow-sm dark:bg-gray-700 dark:text-white"
          : "text-gray-600 hover:text-gray-900 dark:text-gray-400
             dark:hover:text-white"
      )}
    >
      {tab.label}
    </button>
  ))}
</nav>
```

### Recipe 5: Sidebar Layout (saas/ pattern)
```tsx
<div className="flex h-screen">
  <aside className="w-64 flex-shrink-0 border-r border-gray-200
                    bg-gray-50 dark:border-gray-700 dark:bg-gray-900">
    <div className="flex h-16 items-center px-6">
      <span className="text-lg font-bold">Initiate Arena</span>
    </div>
    <nav className="mt-4 space-y-1 px-3">
      {/* nav items */}
    </nav>
  </aside>
  <main className="flex-1 overflow-y-auto p-8">
    {/* page content */}
  </main>
</div>
```

---

## Industry Expert and Cutting-Edge Usage

### Design system tokenization
Top teams define their entire design system in `@theme` and export the CSS
variables for use in non-Tailwind contexts (emails, PDFs, native apps).
The `@theme` block becomes the single source of truth for the brand.

### AI-assisted Tailwind
- v0.dev (Vercel) generates full UI components with Tailwind classes
- Claude and GPT-4 produce high-quality Tailwind code because utility classes
  are explicit and unambiguous — no abstraction layers to confuse the model
- Best practice: give AI the `@theme` block as context so generated code
  uses your design tokens instead of default values

### Component-driven architecture with shadcn/ui
The dominant pattern in 2025-2026 React + Tailwind:
1. Use shadcn/ui as the component foundation (not installed as a dependency —
   code is copied into your project)
2. Customize via `@theme` for brand tokens
3. Use `cn()` utility for conditional class merging
4. Extend shadcn components with additional Tailwind variants

### Performance-first patterns
- Use `content-visibility: auto` via `[content-visibility:auto]` for long lists
- Prefer `gap-*` over `space-*` (gap doesn't add margins to first/last child)
- Use `will-change-transform` sparingly for smooth animations
- Prefer `translate-x-*` over `left-*` for animations (GPU-accelerated)

### Tailwind + Remotion for video
- Layout with Tailwind utilities, animate with `useCurrentFrame()`
- Use the full type scale for video: `text-6xl`, `text-8xl` for readability
- Background gradients via `bg-gradient-to-*` work perfectly for video backgrounds
- Fixed dimensions (1280x720, 1920x1080) mean responsive breakpoints are irrelevant —
  design for a single known viewport

---

## EOS Usage Patterns

### Current usage
- **Remotion project**: Layout and static styling for video compositions.
  `@remotion/tailwind-v4` adapter, `@import "tailwindcss"` entry point.
  No config file. No custom theme yet (default palette).

### Planned usage
- **saas/ frontend**: Full React app with Tailwind v4 + shadcn/ui.
  Will use `@tailwindcss/vite`, `@theme` with Lyfe Institute brand colors,
  `cn()` utility for class merging, dark mode support.

### Brand tokens (for @theme when saas/ frontend is built)
```css
@theme {
  /* Lyfe Institute / Initiate Arena palette — define when building frontend */
  --color-brand: /* primary brand color */;
  --color-brand-light: /* lighter variant */;
  --color-accent: /* action/CTA color */;
  --font-sans: "Inter", ui-sans-serif, system-ui, sans-serif;
  --font-display: "Space Grotesk", sans-serif;
}
```

---

## Gotchas

### Remotion: CSS animations break frame rendering
Using `animate-*` or `transition-*` utilities in Remotion produces
non-deterministic output. Each rendered frame may capture the animation
at a different point. Always use `useCurrentFrame()` + `interpolate()`.

### v4 config format confusion
The most common mistake when working with Tailwind in EOS: creating a
`tailwind.config.js` file. v4 does not use it. All config is CSS-based.
If a tailwind.config.js appears in the repo, delete it.

### Automatic content detection false positives
Tailwind v4 scans all text files in scope for anything that looks like a
class name. Comments, JSON keys, and variable names that match utility
patterns will cause those utilities to be included in the output. This
increases CSS size but doesn't break functionality.

### tailwind-merge version compatibility
When using `tailwind-merge` (for the `cn()` helper), ensure the version
supports v4's utility names. Some v4-only utilities may not be recognized
by older tailwind-merge versions, causing incorrect class deduplication.
