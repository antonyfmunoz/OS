---
name: vite
description: "Use when configuring, debugging, or optimizing Vite build/dev server, HMR, plugins, or production bundling in the EOS SaaS codebase (/opt/OS/saas) — authoring vite.config.ts, wiring @vitejs/plugin-react, setting up path aliases, proxying the Express backend, handling VITE_* env vars via import.meta.env, tuning optimizeDeps, configuring Rollup output (manualChunks, assetFileNames), setting up Vitest, diagnosing CJS/ESM interop errors, pre-bundling failures, HMR full-reload loops, or SSR externalization bugs. Also use when deciding between Vite 5.x and Vite 6 / Rolldown, or migrating from CRA/Webpack."
allowed-tools: "Read, Write, Edit, Bash, WebFetch, WebSearch"
version: 1.0
source_url: "https://vitejs.dev"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "5.x"
sdk_version: "vite@5"
speed_category: "fast"
trigger: both
effort: high
context: fork
---

# Tool: Vite

Vite is the build tool and dev server for every EOS SaaS surface. It is
what makes `pnpm dev` boot in <300ms, what serves TSX through native ESM
in development, what drives Rollup in production, and what owns the HMR
channel every React component relies on. When a component edit updates
the browser without a full reload, that is Vite.

This skill exists so agents working in `/opt/OS/saas` configure Vite the
way Evan You and the Vite team intended — ESM-native in development,
Rollup-optimal in production, with plugins composed in the right order
and `optimizeDeps` left alone unless there is a specific reason to touch it.

## What This Tool Does

Vite (French for "fast") is a two-mode build tool:

- **Development mode** — an ESM-native dev server backed by **esbuild**.
  Source files are transformed on-demand and served to the browser as
  native ES modules. No bundling. HMR is a surgical module-graph patch
  over a WebSocket — not a full reload.
- **Production mode** — a pre-configured **Rollup** build with tree
  shaking, code splitting, CSS code splitting, legacy fallback (via
  `@vitejs/plugin-legacy`), and asset fingerprinting.

This split is the core insight. esbuild is 10-100x faster than JS-based
bundlers but has weaker tree-shaking and plugin ecosystem; Rollup has
the best output but is slow. Vite uses each where it wins.

Core capabilities:
- **Native ESM dev server** — no bundling during `dev`; browser requests individual modules.
- **Dependency pre-bundling** — `node_modules` are pre-bundled ONCE with esbuild into a single ESM module (CJS→ESM conversion + flatten deep imports).
- **HMR via `import.meta.hot`** — fast-refresh for React via `@vitejs/plugin-react`, fine-grained module replacement.
- **Rollup production build** — `vite build` shells out to Rollup with Vite's preset config.
- **Plugin API** — a superset of Rollup's plugin API plus Vite-specific hooks (`config`, `configResolved`, `configureServer`, `transformIndexHtml`, `handleHotUpdate`).
- **CSS handling** — PostCSS, CSS modules, `@import` resolution, Tailwind, preprocessors, CSS code splitting in prod.
- **Env vars via `import.meta.env`** — `VITE_*` vars are statically replaced at build time.
- **SSR primitives** — `server.ssrLoadModule`, `ssr.external`, `ssr.noExternal`.
- **`vite preview`** — a minimal static server for verifying the production build locally.

## EOS Integration

**Where Vite lives:**
- `/opt/OS/saas/*/vite.config.ts` — the config file per SaaS app.
- `/opt/OS/saas/*/package.json` — scripts: `dev`, `build`, `preview`, `test`.
- `/opt/OS/saas/*/index.html` — the ENTRY POINT (not `src/main.tsx`).
  Vite treats `index.html` as a first-class source file.
- `/opt/OS/saas/*/src/main.tsx` — referenced from `index.html` via `<script type="module" src="/src/main.tsx">`.
- `/opt/OS/saas/*/src/vite-env.d.ts` — `import.meta.env` type augmentation.

**Stack partners (see references/integrations.md):**
- **React 18 + TS strict** — via `@vitejs/plugin-react` (SWC or Babel transform).
- **Tailwind + shadcn/ui** — via PostCSS (`postcss.config.js` with `tailwindcss` + `autoprefixer`).
- **Express backend** — proxied from Vite dev server via `server.proxy` (avoids CORS; Express runs on a separate port).
- **Path aliases** — `@/*` via both `tsconfig.json` `paths` AND `resolve.alias`, OR via `vite-tsconfig-paths` (single source of truth).
- **Vitest** — shares the same `vite.config.ts`; test config lives under a `test` key.
- **Drizzle ORM** — runs server-side; must NOT be bundled into the client. Keep it behind the Express proxy.

**The rule:** the browser never sees Drizzle, never sees server secrets, never sees `process.env`. Anything the browser needs goes through `import.meta.env.VITE_*` (build-time replaced) OR through the Express API (runtime, proxied).

## Authentication

Vite is a local build tool, not a SaaS. **No API keys, no accounts, no tokens.** The security surface is:

- **Dev server exposure** — by default Vite binds to `localhost` only. Binding to `0.0.0.0` (`--host`) exposes HMR + source to the network. Only do this on Tailscale (which EOS already uses) or behind a firewall.
- **Env var leakage** — ONLY vars prefixed `VITE_` are exposed to client code. Any other var in `.env` stays on the build machine. **Never prefix a secret with `VITE_`** — it will be inlined into the bundle and shipped to browsers.
- **`.env` files** — loaded by Vite in this precedence: `.env` → `.env.local` → `.env.[mode]` → `.env.[mode].local`. `.local` files are always gitignored by convention.
- **Source maps in production** — off by default; if enabled (`build.sourcemap: true`), they ship your source to browsers. Use `'hidden'` to keep them for error reporting without exposing them.

What replaces auth for a build tool: **version pinning and plugin audit**. Pin `vite` and every `@vitejs/*` plugin to exact versions. Audit plugins before adding — they run arbitrary code at build time and can modify output.

## Quick Reference

### Minimal React + TS config

```ts
// vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": {
        target: "http://localhost:3000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
    target: "es2022",
  },
});
```

### Env vars

```ts
// vite-env.d.ts
/// <reference types="vite/client" />
interface ImportMetaEnv {
  readonly VITE_API_URL: string;
  readonly VITE_POSTHOG_KEY: string;
}
interface ImportMeta {
  readonly env: ImportMetaEnv;
}
```

```ts
// anywhere in src/
const apiUrl = import.meta.env.VITE_API_URL; // NOT process.env
```

### Path alias (type + runtime must agree)

```json
// tsconfig.json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": { "@/*": ["./src/*"] }
  }
}
```

```ts
// vite.config.ts — MUST match tsconfig paths
resolve: { alias: { "@": path.resolve(__dirname, "./src") } }
```

Or use `vite-tsconfig-paths` to derive `resolve.alias` from tsconfig automatically (one source of truth).

### Production build with manual chunks

```ts
build: {
  rollupOptions: {
    output: {
      manualChunks: {
        react: ["react", "react-dom"],
        query: ["@tanstack/react-query"],
        ui: ["@radix-ui/react-dialog", "@radix-ui/react-popover"],
      },
    },
  },
  chunkSizeWarningLimit: 600,
}
```

### Vitest setup (same config file)

```ts
/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
  },
});
```

### Dev-only HMR API

```ts
if (import.meta.hot) {
  import.meta.hot.accept((newMod) => {
    // custom hot update logic
  });
}
```

## Conceptual Model

Think of Vite as **two tools glued together by a plugin API**, with a contract that both tools produce the same output semantics.

1. **`dev` is not bundled.** During `vite dev`, your source is served as native ES modules. The browser makes one HTTP request per module. This is why dev is instant — Vite only has to transform the files the browser asks for. A 2,000-file app boots as fast as a 20-file app.

2. **`node_modules` ARE bundled (once) in dev.** Vite pre-bundles `node_modules` with esbuild on first run and caches the result under `node_modules/.vite`. This converts CJS → ESM and flattens deep imports (e.g. `lodash/debounce` into one file) so the browser doesn't make 600 requests. When you add a new dep, Vite re-runs pre-bundling automatically.

3. **`build` IS bundled, by Rollup.** `vite build` runs Rollup with Vite's preset. Tree shaking, code splitting, CSS code splitting, minification (esbuild or terser), asset hashing. The output is what actually ships.

4. **Plugins have two lives.** A Vite plugin is a Rollup plugin with extra hooks. In dev, only the Vite hooks + a subset of Rollup hooks run. In prod, the full Rollup pipeline runs. Plugin order matters — `pre` plugins run first, then normal, then `post`.

5. **`import.meta.env` is a compile-time constant.** Vite statically replaces `import.meta.env.VITE_FOO` with the literal string value at build time. It is NOT a runtime lookup. You cannot dynamically construct the key.

6. **HMR is module-graph-aware.** When a file changes, Vite walks up the import graph to find a module that accepts hot updates (`import.meta.hot.accept`). React fast-refresh wires this for every component automatically. If no ancestor accepts, Vite falls back to a full page reload.

7. **`index.html` is the entry, not `main.tsx`.** Vite crawls `index.html` for `<script type="module">` and `<link>` tags to discover the real entry points. This is why you can have multi-page apps by just adding HTML files.

## Gotchas

- **`process.env` does not exist in browser code.** Use `import.meta.env`. If a dep references `process.env.NODE_ENV` at runtime, Vite replaces it at build time; if a dep references other `process.env.*` keys, you need `define: { 'process.env.X': JSON.stringify(...) }` or a shim plugin.

- **CJS-only deps break dev pre-bundling.** If a dep is published as CJS with deep imports, esbuild may fail to convert it. Fix by adding it to `optimizeDeps.include`. If it has mixed ESM/CJS, add it to `optimizeDeps.exclude` instead. Symptom: `Failed to resolve entry for package` or `does not provide an export named 'default'`.

- **`tsconfig.json` paths do NOT affect Vite bundling.** TypeScript only uses them for type checking. You must ALSO set `resolve.alias` in `vite.config.ts`, OR use `vite-tsconfig-paths` plugin. Otherwise dev works (via TS) but `vite build` fails with "Cannot resolve '@/...'".

- **HMR full-reload loop.** If a non-component file exports both a component and a non-component value, fast-refresh gives up and does a full reload on every edit. Fix: split files so they export ONLY components (React Refresh rule). The error is silent — just slow HMR.

- **`optimizeDeps.force` nuke.** When pre-bundling gets stuck (usually after swapping deps), `rm -rf node_modules/.vite` OR run `vite --force` once. Don't leave `--force` in the default script — it defeats caching.

- **Source maps exposed in prod.** `build.sourcemap: true` ships `.map` files AND adds `//# sourceMappingURL=` comments. Anyone with DevTools sees your source. Use `'hidden'` for error-reporting-only.

- **`server.proxy` preserves path.** `"/api": "http://localhost:3000"` forwards `/api/foo` to `http://localhost:3000/api/foo`. If your Express route is at `/foo`, use `rewrite: (p) => p.replace(/^\/api/, '')`.

- **`define` replacement is textual and unsafe.** `define: { __VERSION__: '1.0.0' }` replaces the literal text — without quotes that becomes `const v = 1.0.0` which is a syntax error. Always `JSON.stringify()` string values.

- **Public assets vs imported assets.** Files in `public/` are copied as-is and referenced by absolute path `/logo.png`. Files imported via `import logo from './logo.png'` are fingerprinted and rewritten. Don't reference `public/` files with `import`.

- **Worker files need `?worker` suffix.** `import MyWorker from './worker.ts?worker'` — the suffix tells Vite to build a separate worker bundle.

- **Vite 6 + Rolldown is coming.** Vite 6 is the transition; "rolldown-vite" replaces Rollup with a Rust-based bundler sharing the Rollup plugin API. Don't migrate production apps until Rolldown is stable.

## References

- `references/best_practices.md` — full 19-section creator-level protocol.
- `references/examples.md` — EOS-aligned realistic vite.config.ts patterns.
- `references/anti_patterns.md` — real failure modes and fixes.
- `references/integrations.md` — React / TS / Tailwind / shadcn / Express / Vitest stack composition.

## Source

- https://vitejs.dev (authoritative)
- https://vitejs.dev/config (config reference)
- https://vitejs.dev/guide (conceptual guide)
- https://github.com/vitejs/vite (source + release notes)
- https://antfu.me (Anthony Fu — Vite core team blog)
- https://patak.dev (Patak — Vite core team blog)
- https://rollupjs.org (Rollup — production bundler under Vite)
