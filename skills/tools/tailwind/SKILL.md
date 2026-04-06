---
name: tailwind
description: "Use when building UI components with utility classes, configuring Tailwind CSS, creating responsive layouts, adding dark mode, or debugging styling issues in saas/ or Remotion projects."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://tailwindcss.com/docs"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "v4"
sdk_version: "tailwindcss 4.0.0"
speed_category: fast
trigger: both
effort: medium
context: fork
---

# Tool: Tailwind CSS v4

## What This Tool Does

Tailwind CSS is a utility-first CSS framework that provides low-level utility classes
to build custom designs directly in markup. Instead of writing custom CSS, you compose
styles using pre-built classes like `flex`, `pt-4`, `text-center`, `bg-blue-500`.

Tailwind v4 is a ground-up rewrite with these core changes from v3:
- **CSS-first configuration** — no more `tailwind.config.js`. All config lives in CSS
  using `@theme` and `@import "tailwindcss"`
- **Native CSS cascade layers** — utilities, components, and base are CSS layers
- **Lightning CSS engine** — replaces PostCSS for transforms, massively faster builds
- **Automatic content detection** — no more `content: [...]` array in config
- **New default color palette** — OKLCH-based colors for perceptual uniformity
- **Container queries** — `@container` and `@min-*`/`@max-*` built-in
- **3D transforms** — `rotate-x-*`, `rotate-y-*`, `perspective-*`
- **`@starting-style`** — animate entry transitions without JS
- **`not-*` variant** — negate any variant (`not-hover:opacity-50`)

## EOS Integration

### Remotion project (active)
`knowledge/skills/marketing/content/remotion/` — video content generation.

Config chain:
- `remotion.config.ts` — imports `@remotion/tailwind-v4` and applies `enableTailwind`
  to Webpack config via `Config.overrideWebpackConfig(enableTailwind)`
- `src/index.css` — contains `@import "tailwindcss";` (v4 CSS-first entry point)
- `src/Root.tsx` — imports `./index.css` to load Tailwind into all compositions
- `package.json` — `tailwindcss: 4.0.0`, `@remotion/tailwind-v4: 4.0.436`

Remotion-specific rules:
- Never use `transition-*` or `animate-*` Tailwind classes — always animate
  with Remotion's `useCurrentFrame()` hook for frame-accurate rendering
- Tailwind is for layout and static styling only in Remotion context
- CSS `@import "tailwindcss"` in `src/index.css` is the sole entry point

### saas/ project (planned)
`saas/` — Initiate Arena SaaS app. Currently API-only (Hono + Drizzle).
No frontend yet. When the React UI layer is built, Tailwind v4 will be
the styling framework. Stack will be: React 18+, Vite, Tailwind v4, shadcn/ui.

Expected setup:
- `src/index.css` with `@import "tailwindcss";`
- `@theme` block for brand colors (Lyfe Institute palette)
- Vite plugin: `@tailwindcss/vite` (v4's native Vite integration)
- shadcn/ui components use Tailwind utility classes + CSS variables

### Config file locations
| Project | Config Method | Location |
|---------|--------------|----------|
| Remotion | CSS-first (v4) | `src/index.css` + `remotion.config.ts` |
| saas/ | CSS-first (v4) | `src/index.css` (when frontend added) |

No `tailwind.config.js` or `tailwind.config.ts` exists anywhere in EOS.
This is correct for v4 — all configuration is CSS-based.

## Authentication

N/A — Tailwind CSS is a build-time tool with no API keys, tokens, or
authentication. It processes CSS at build time and produces static output.

## Quick Reference

### v4 CSS entry point (the only required setup)
```css
/* src/index.css */
@import "tailwindcss";
```

### Custom theme values (replaces tailwind.config.js `theme.extend`)
```css
@import "tailwindcss";

@theme {
  --color-brand: #1a1a2e;
  --color-brand-light: #16213e;
  --color-accent: #e94560;
  --font-display: "Inter", sans-serif;
  --breakpoint-3xl: 1920px;
}
```

### Responsive design
```html
<!-- Mobile-first: base → sm → md → lg → xl → 2xl -->
<div class="w-full md:w-1/2 lg:w-1/3">
  <h1 class="text-2xl md:text-4xl lg:text-6xl">Title</h1>
</div>
```

### Dark mode
```html
<!-- Uses prefers-color-scheme by default in v4 -->
<div class="bg-white dark:bg-gray-900 text-black dark:text-white">
  Content
</div>
```

### Flexbox and Grid layouts
```html
<!-- Flex row with gap -->
<div class="flex items-center justify-between gap-4">
  <div class="flex-1">Left</div>
  <div class="flex-shrink-0">Right</div>
</div>

<!-- Grid with responsive columns -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
  <div>Card 1</div>
  <div>Card 2</div>
  <div>Card 3</div>
</div>
```

### Container queries (new in v4)
```html
<div class="@container">
  <div class="@sm:flex @lg:grid @lg:grid-cols-2">
    Responds to container width, not viewport
  </div>
</div>
```

### Arbitrary values
```html
<div class="top-[117px] bg-[#1a1a2e] grid-cols-[1fr_2fr_1fr]">
  Escape hatch for one-off values
</div>
```

### State variants
```html
<button class="bg-blue-500 hover:bg-blue-600 active:bg-blue-700
               focus:ring-2 focus:ring-blue-300 disabled:opacity-50
               not-disabled:cursor-pointer">
  Click me
</button>
```

### Typography scale
```html
<h1 class="text-4xl font-bold tracking-tight">Heading</h1>
<p class="text-base leading-relaxed text-gray-600">Body text</p>
<span class="text-sm font-medium uppercase tracking-wide">Label</span>
```

### Spacing system
```
p-0  = 0px      p-1  = 0.25rem (4px)   p-2  = 0.5rem (8px)
p-3  = 0.75rem  p-4  = 1rem (16px)     p-6  = 1.5rem (24px)
p-8  = 2rem     p-12 = 3rem            p-16 = 4rem
p-20 = 5rem     p-24 = 6rem            p-32 = 8rem
```

### Animations (for saas/ — NOT for Remotion)
```html
<div class="animate-spin">Loading spinner</div>
<div class="animate-pulse">Skeleton loader</div>
<div class="transition-colors duration-200 hover:bg-gray-100">Hover effect</div>
```

### Custom utilities via CSS (replaces @layer utilities in v3)
```css
@import "tailwindcss";

@utility scrollbar-hide {
  -ms-overflow-style: none;
  scrollbar-width: none;
  &::-webkit-scrollbar {
    display: none;
  }
}
```

## Conceptual Model

```
Tailwind CSS v4
  |
  +-- CSS Entry Point (@import "tailwindcss")
  |     |-- Replaces tailwind.config.js entirely
  |     |-- @theme block defines design tokens
  |     |-- @utility defines custom utilities
  |     |-- @variant defines custom variants
  |     +-- @source adds explicit content paths (rarely needed)
  |
  +-- Utility Classes (the primitives)
  |     |-- Layout: flex, grid, block, hidden, container
  |     |-- Spacing: p-*, m-*, gap-*, space-*
  |     |-- Sizing: w-*, h-*, min-*, max-*
  |     |-- Typography: text-*, font-*, leading-*, tracking-*
  |     |-- Colors: bg-*, text-*, border-*, ring-*
  |     |-- Effects: shadow-*, opacity-*, blur-*
  |     +-- Borders: rounded-*, border-*, ring-*
  |
  +-- Variants (modifiers that scope utilities)
  |     |-- State: hover, focus, active, disabled, not-*
  |     |-- Responsive: sm, md, lg, xl, 2xl
  |     |-- Dark mode: dark
  |     |-- Container: @sm, @md, @lg
  |     |-- Group/Peer: group-hover, peer-checked
  |     +-- Custom: @variant directive
  |
  +-- Build Pipeline
        |-- v4: Lightning CSS (native, fast)
        |-- Remotion: Webpack via @remotion/tailwind-v4
        |-- Vite: @tailwindcss/vite plugin
        +-- PostCSS: @tailwindcss/postcss (legacy compat)
```

See references/best_practices.md for the full 19-section reference.

## Gotchas

### Remotion: no transition-* or animate-* classes
Tailwind's CSS animation and transition utilities conflict with Remotion's
frame-based rendering. Animations must use `useCurrentFrame()` for deterministic
frame output. Using `animate-spin` or `transition-colors` produces non-deterministic
results in rendered video frames.

### v4 has no tailwind.config.js
If you create a `tailwind.config.js` or `tailwind.config.ts`, v4 ignores it.
All configuration is CSS-based via `@theme`, `@utility`, and `@variant` directives
inside your CSS entry point. This is the single most common v3-to-v4 migration mistake.

### @apply is deprecated in v4
Tailwind v4 discourages `@apply` usage. It still works for backward compatibility
but is considered an anti-pattern. Use `@utility` directive for reusable styles
or extract React components instead.

### Content detection is automatic in v4
v4 automatically scans your project for class names. No `content: [...]` config
needed. If a file is outside the project root or in a non-standard location,
use `@source "../other-dir"` in your CSS to add it.

### @import must be first
`@import "tailwindcss"` must be the first rule in your CSS file (after other
`@import` statements). Putting styles before it causes silent failures where
utilities don't generate.

### Vite vs Webpack plugin
For Vite projects: use `@tailwindcss/vite` (native, fastest).
For Webpack projects (like Remotion): use `@tailwindcss/postcss` or the
framework-specific adapter (`@remotion/tailwind-v4`).
Do NOT mix them — pick one per project.

### OKLCH colors may render differently
v4's default palette uses OKLCH color space. In older browsers without OKLCH
support, colors fall back to sRGB. The visual difference is usually minor
but can affect brand color accuracy. Define exact brand colors with hex/rgb
in `@theme` to avoid this.

### Class name conflicts with CSS variables
v4 uses CSS custom properties (variables) extensively under the hood.
If your own CSS defines `--color-*`, `--font-*`, or `--spacing-*` variables
that collide with Tailwind's namespace, unexpected overrides occur.
Namespace your custom properties to avoid collisions.
