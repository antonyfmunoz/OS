# Vite — Creator-Level Best Practices
Source: https://vitejs.dev
API Version: 5.x (Vite 6 in transition)
SDK Version: vite@5
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication

Vite is a local build tool. There is no API, no account, no token. The security surface is entirely about **what gets inlined into the bundle** and **who can reach the dev server**.

- **Client env vars**: only variables prefixed `VITE_` are exposed to client code via `import.meta.env`. All others stay in the Node process. NEVER put secrets behind `VITE_*`.
- **Env file precedence**: `.env` → `.env.local` → `.env.[mode]` → `.env.[mode].local`. Later overrides earlier. `.local` files are gitignored by convention; commit only `.env.example`.
- **Mode**: `vite dev` uses `development` mode by default; `vite build` uses `production`. Override with `--mode staging` to load `.env.staging`.
- **Custom prefix**: override with `envPrefix: ['VITE_', 'PUBLIC_']` in config (use with caution — breaks the "VITE_ = public" mental model).
- **Dev server bind**: defaults to `localhost`. `--host` binds `0.0.0.0`. Use only behind Tailscale/firewall. `server.https` requires a cert.
- **Source maps**: `build.sourcemap` can be `true | false | 'inline' | 'hidden'`. `hidden` emits maps without `//# sourceMappingURL=` — use for Sentry upload without exposing.
- **HMR WebSocket**: same port as dev server by default. If fronted by a reverse proxy, configure `server.hmr.host`/`server.hmr.clientPort`.

In EOS, `.env` lives next to the SaaS `package.json`. Server-side secrets live in `eos_ai/.env` and never cross into `/opt/OS/saas/*/`.

## Core Operations with Exact Signatures

The "API" of Vite is its **config object** (`UserConfig`) and its **plugin hooks**. Key options:

```ts
defineConfig({
  root: string,                    // project root, default process.cwd()
  base: string,                    // public base path, default '/'
  mode: string,                    // 'development' | 'production' | custom
  publicDir: string | false,       // default 'public'
  cacheDir: string,                // default 'node_modules/.vite'
  plugins: PluginOption[],
  resolve: {
    alias: Record<string, string> | Array<{find, replacement}>,
    dedupe: string[],              // force same version across the graph
    conditions: string[],          // package.json exports conditions
    extensions: string[],          // default ['.mjs','.js','.mts','.ts','.jsx','.tsx','.json']
    preserveSymlinks: boolean,
  },
  css: {
    modules: CSSModulesOptions,
    postcss: string | PostCSSConfig,
    devSourcemap: boolean,
  },
  server: {
    host: string | boolean,        // default 'localhost'
    port: number,                  // default 5173
    strictPort: boolean,           // fail if port taken instead of fallback
    https: ServerOptions,
    open: boolean | string,
    proxy: Record<string, ProxyOptions>,
    cors: boolean | CorsOptions,
    hmr: boolean | { host?, port?, clientPort?, overlay? },
    watch: WatchOptions,           // chokidar options
    fs: { strict: boolean, allow: string[], deny: string[] },
  },
  build: {
    target: 'modules' | string | string[],  // default 'modules' (es2020+)
    outDir: string,                // default 'dist'
    assetsDir: string,             // default 'assets'
    assetsInlineLimit: number,     // default 4096 bytes
    cssCodeSplit: boolean,         // default true
    sourcemap: boolean | 'inline' | 'hidden',
    minify: 'esbuild' | 'terser' | false, // default 'esbuild'
    rollupOptions: RollupOptions,  // passthrough
    lib: LibraryOptions,           // library mode
    emptyOutDir: boolean,          // default true if outDir inside root
    chunkSizeWarningLimit: number, // default 500 kB
    reportCompressedSize: boolean, // default true; disable for speed
  },
  preview: { port: number, host, strictPort },
  optimizeDeps: {
    entries: string[],
    include: string[],             // force pre-bundle
    exclude: string[],             // skip pre-bundle
    esbuildOptions: EsbuildOptions,
    force: boolean,                // re-bundle on boot
  },
  ssr: {
    external: string[],            // mark as external in SSR
    noExternal: string[] | true,   // bundle into SSR output
    target: 'node' | 'webworker',
  },
  define: Record<string, string>,  // static replacements (JSON-stringify values!)
  envPrefix: string | string[],    // default 'VITE_'
  envDir: string,
  test: VitestUserConfig,          // when vitest is installed
})
```

Plugin hooks (execute order: `config` → `configResolved` → `options` → `buildStart` → `resolveId` → `load` → `transform` → `buildEnd` → `closeBundle`; plus Vite-specific: `configureServer`, `configurePreviewServer`, `transformIndexHtml`, `handleHotUpdate`).

## Pagination Patterns

N/A for a build tool. The analogue is **dependency graph traversal**. Vite crawls the module graph starting from `index.html` entries. `vite build` performs a full Rollup traversal; `vite dev` performs lazy traversal (only files the browser requests). The "page" unit is a module; the "cursor" is the module graph's import edges.

## Rate Limits

N/A for a build tool. The analogue is **HMR update throughput and dev-server concurrency**:

- **HMR debounce**: Vite batches file changes within ~10ms windows before emitting an update.
- **Dev server concurrency**: limited by Node's event loop; no hard request cap.
- **Pre-bundle concurrency**: `optimizeDeps` runs esbuild with `worker` concurrency set automatically.
- **File watcher**: uses chokidar; on Linux, inotify limits apply (`fs.inotify.max_user_watches`). Symptom on large repos: "Cannot watch for file changes". Fix: raise the limit.

## Error Codes and Recovery

Vite errors come from three layers — Vite itself, esbuild (dev), Rollup (build):

- **`[vite] Internal server error: Failed to resolve import "X" from "Y"`** — missing dep OR wrong alias OR case-sensitive path mismatch. Fix: `pnpm add X` or fix the alias.
- **`[vite] Pre-transform error: Failed to load url`** — usually a file extension Vite doesn't understand. Fix: add the extension or a loader plugin.
- **`[plugin:vite:esbuild] Transform failed with N errors`** — syntax error in source. The output includes line/column.
- **`[vite] The file does not exist at "node_modules/.vite/deps/..."`** — stale pre-bundle cache. Fix: `rm -rf node_modules/.vite` and restart. Vite usually auto-recovers by re-bundling, but sometimes the cache is wedged.
- **`[vite] Outdated Optimize Dep`** — pre-bundle was invalidated mid-run; page auto-reloads.
- **`Rollup failed to resolve import`** in `vite build` — the dev server was more forgiving than Rollup. Add to `rollupOptions.external` if it's an optional dep, or fix the import.
- **`"default" is not exported by ...` (CJS interop)** — a CJS module's default export wasn't detected. Fix: `optimizeDeps.include: ['that-package']`.
- **`Top-level await is not available in the configured target environment`** — set `build.target: 'es2022'` or higher.
- **`Error: EMFILE: too many open files`** — file watcher + OS limit. `ulimit -n 8192` or raise inotify limit on Linux.

Recovery strategy: dev-server errors rarely require a full restart. The error overlay in the browser shows the exact file + line. Build-time errors always require re-running `vite build`.

## SDK Idioms

- **Always use `defineConfig`**. It gives IDE autocomplete and type-checks the config against `UserConfig`.
- **Async config**: return a function `({ mode, command }) => ({...})` when config depends on mode/command. The function can be `async`.
- **Conditional plugins**: `plugins: [react(), mode === 'production' && legacy()].filter(Boolean)`.
- **Plugin enforce order**: `{ enforce: 'pre' }` runs before core plugins, `'post'` runs after. Without enforce, runs between.
- **Reuse server instance for middleware**: `configureServer(server) { server.middlewares.use(myMiddleware) }`.
- **Read resolved config**: `configResolved(resolved) { this.root = resolved.root }`.
- **Virtual modules**: prefix with `\0` in `resolveId` to signal "this is a virtual module, Rollup should not touch it".
- **HMR API from app code**: always guard with `if (import.meta.hot) { ... }` so prod build tree-shakes it.
- **Library mode**: `build.lib = { entry, formats: ['es', 'cjs'], fileName: 'my-lib' }` for publishing packages.
- **Multi-page**: `build.rollupOptions.input = { main: '/index.html', admin: '/admin.html' }`.

## Anti-Patterns

- **Using `process.env` in browser code.** Use `import.meta.env.VITE_*`.
- **Putting secrets behind `VITE_*`.** They ship to the browser. Keep server-only vars unprefixed and read them in Express.
- **Setting `optimizeDeps.force: true` permanently.** Defeats the pre-bundle cache; every boot reruns esbuild over `node_modules`.
- **`build.sourcemap: true` in production without thought.** Ships your source code to end users. Use `'hidden'` + Sentry upload.
- **Mixing `tsconfig.paths` with no `resolve.alias`.** Works in dev (via TS), fails in `vite build`. Use `vite-tsconfig-paths` as the single source of truth.
- **`export default` and `export const` a component together.** Breaks React Fast Refresh — every edit triggers a full page reload. Split the file.
- **`define: { FOO: '1.0.0' }`.** Textual replacement; becomes `const x = 1.0.0` → syntax error. Always `JSON.stringify`.
- **Importing files out of project root** without adding to `server.fs.allow` — silent 403 in dev.
- **Using `require()` in vite.config.ts.** Vite config is ESM-first. Use `import`. Top-level await is fine.

## Data Model

Vite's primary "entities":

- **Module graph** — every file (source + deps) is a node; imports are edges. `server.moduleGraph` exposes it in plugins.
- **`ModuleNode`** — has `id`, `url`, `importers`, `importedModules`, `transformResult`, `lastHMRTimestamp`.
- **Plugins** — ordered array, each with hooks. `pre` plugins, then user plugins, then core, then `post` plugins.
- **Environments (Vite 6+)** — new concept: `client`, `ssr`, and custom environments each with their own module graph and plugin pipeline. In Vite 5, ssr shares the plugin pipeline with a mode flag.
- **Assets** — imported files outside the JS graph (images, fonts). Hashed in build; served raw in dev.

Field constraints: `resolve.alias` keys must be unique; `server.port` must be 0-65535; `build.assetsInlineLimit` must be an integer (bytes).

## Webhooks and Events

N/A in the HTTP sense. The analogue is **plugin hooks and the HMR API**:

- **Rollup hooks** (run during build AND dev): `options`, `buildStart`, `resolveId`, `load`, `transform`, `moduleParsed`, `buildEnd`, `renderStart`, `generateBundle`, `writeBundle`, `closeBundle`.
- **Vite-specific hooks**: `config(config, env)`, `configResolved(resolvedConfig)`, `configureServer(server)`, `configurePreviewServer(server)`, `transformIndexHtml(html, ctx)`, `handleHotUpdate({ file, modules, server, read })`.
- **HMR client API**: `import.meta.hot.accept(cb)`, `hot.accept('./dep', cb)`, `hot.dispose(cb)`, `hot.prune(cb)`, `hot.invalidate()`, `hot.on(event, cb)`, `hot.send(event, data)`.
- **HMR server API** (in plugins): `server.ws.send({ type: 'custom', event, data })` — push arbitrary events to the client.

Delivery: local WebSocket, no retries, at-most-once. If the socket drops, Vite reconnects and falls back to full reload.

## Limits

- **Module graph size**: no hard limit, but dev boot time grows with `optimizeDeps` work, not with total source count.
- **Max source file size**: bounded by Node memory. Practical limit ~50MB per file.
- **`assetsInlineLimit`**: default 4096 bytes — assets smaller inlined as base64, larger emitted as files.
- **`chunkSizeWarningLimit`**: default 500 kB; warning only, not an error.
- **Rollup entry count**: bounded by OS file descriptors.
- **HMR payload**: no hard size limit, but large payloads (>1MB) trigger full reload.
- **Max open files (watcher)**: OS-level; Linux default 1024 — raise for monorepos.

## Cost Model

Vite is open source and free. The analogue cost model is **build performance budget**:

- **Dev boot**: ~200-800ms on small apps; ~1-3s on larger apps after first pre-bundle. Subsequent boots are cached.
- **Build time**: dominated by Rollup tree-shaking and minification. `reportCompressedSize: false` can save 20-50% on CI.
- **Bundle size budget**: target <200KB gzipped initial JS for a React+shadcn app. Over 500KB the warning triggers.
- **Pre-bundle cache**: `node_modules/.vite` — invalidated on lockfile or config change. Deleting recovers from wedge.
- **HMR latency**: usually <50ms file-change-to-browser for React components. >500ms means fast-refresh is falling back to full reload.

## Version Pinning

- **Pin vite exactly**: `"vite": "5.4.x"` — not `^5.4.0`. Minor versions have introduced plugin-API changes.
- **Plugin version compatibility**: `@vitejs/plugin-react` major version tracks Vite major. Pin them together.
- **Rollup version**: Vite 5 ships with Rollup 4. Don't install `rollup` as a direct dep — let Vite's transitive version win.
- **esbuild version**: Vite pins esbuild transitively. Never install a different esbuild version — mismatches cause pre-bundle failures.
- **Node version**: Vite 5 requires Node 18+. Vite 6 requires Node 18+ with some features on 20+. EOS uses Node 20.
- **Deprecation**: Vite 4 is EOL. Vite 5 is current stable. Vite 6 is transition to Rolldown. Vite 7 will be Rolldown-default.

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

Evan You built Vite after years of maintaining Vue CLI (Webpack-based) and watching dev boot times grow from "instant" to "60 seconds" as apps scaled. The core insight: **in 2020, every target browser natively supported ES modules**. If you could serve unbundled source, dev would be O(1) in app size instead of O(n).

The consciously-made tradeoffs:

- **Unbundled dev, bundled prod.** Rejected the "use one tool everywhere" doctrine. Esbuild for dev transforms, Rollup for prod output. Each is the best at its job.
- **esbuild over swc for dev transforms.** Faster, simpler, written in Go. Accepts the "less extensible" tradeoff.
- **Rollup (not Webpack) for prod.** Better tree-shaking, cleaner plugin API, ESM-native.
- **Convention over configuration.** The default config is production-ready. You should write <30 lines of vite.config.ts for a typical app.
- **Plugin API = Rollup plus extras.** Reuses Rollup's ecosystem; doesn't fork it.
- **HTML as entry.** Rejects the "JS is the entry" Webpack model. HTML is the web's real entry point.

What Vite is NOT: a task runner (use pnpm scripts), a test runner (use Vitest — a Vite-native sibling), a linter, a formatter, or a Node app server. It's a build tool for browser applications.

## Problem-Solution Map and Hidden Capabilities

Beyond "make dev fast", Vite solves:

- **Monorepo consistency** — one build tool across many apps, each with its own `vite.config.ts`.
- **Library publishing** — `build.lib` mode outputs ESM+CJS+type-only bundles for npm.
- **SSR without a framework** — `server.ssrLoadModule` lets you write your own SSR server; no need for Next/Remix.
- **Multi-page apps** — `rollupOptions.input` with multiple HTML files gives MPA with shared chunks.
- **Worker bundles** — `?worker` suffix builds workers as separate bundles with shared dep graph.
- **Virtual modules** — plugins can create modules that don't exist on disk (e.g., `virtual:routes`).
- **`?raw`, `?url`, `?inline`** — import query suffixes to control asset handling.
- **`import.meta.glob`** — compile-time glob import for "load all files in dir" patterns.
- **`server.middlewares`** — arbitrary Connect middleware in the dev server.
- **Custom HMR events** — plugins can send data to the client over the HMR websocket.

Hidden gems most users miss: `define` for feature flags, `resolve.dedupe` for fixing duplicate React, `build.rollupOptions.treeshake.moduleSideEffects: false` for aggressive tree-shaking, `css.transformer: 'lightningcss'` for faster CSS processing (experimental).

## Operational Behavior and Edge Cases

- **First boot is slower** than subsequent boots due to `optimizeDeps` pre-bundling. Warn CI and demo users.
- **HMR silently degrades to full reload** when fast-refresh can't patch. The only signal is slower HMR.
- **Symlinked packages** (pnpm, yalc) can confuse the module resolver. `resolve.preserveSymlinks: false` is the default and usually right; flip only if deps double-import.
- **Case-insensitive file systems** (macOS, Windows) let dev succeed on wrong-case imports that fail on Linux CI. Always run `vite build` on Linux CI.
- **Watcher misses** on NFS/SMB mounts. Fall back to `server.watch.usePolling: true` (high CPU but reliable).
- **`cacheDir` across branches** — switching git branches can leave a stale pre-bundle. `rm -rf node_modules/.vite` after heavy branch switches.
- **Circular imports** work in dev but can break tree-shaking in prod; Rollup warns.
- **Dynamic imports with variables** (`import(\`./pages/${name}.tsx\`)`) require `import.meta.glob` instead for code splitting.
- **PostCSS config discovery** walks up from root; a stray `postcss.config.js` two dirs up can hijack Tailwind.
- **`base` path + absolute URLs** — if `base: '/app/'`, all asset URLs are prefixed, but `fetch('/api/...')` is NOT. Client-side routing needs separate handling.

## Ecosystem Position and Composition

Vite sits at the **build/dev layer** of the frontend stack. It replaces Webpack + Webpack Dev Server + Babel-loader + various plugins.

Natural complements:
- **React / Vue / Svelte / Solid / Preact** — official plugins for each.
- **TypeScript** — built-in via esbuild (transpile only — type-check separately with `tsc --noEmit`).
- **Tailwind** — via PostCSS plugin.
- **Vitest** — test runner that reuses `vite.config.ts`.
- **Nuxt / SvelteKit / Astro / Remix (v2+) / Qwik** — meta-frameworks built ON TOP of Vite.
- **Storybook 7+** — Vite builder option is now default for many frameworks.

Forced integrations / avoid:
- **Vite + Webpack in the same app** — don't. Pick one.
- **CRA (Create React App) migration** — Vite is the official recommended replacement; CRA is deprecated.
- **`tsc` as the transpiler** — Vite uses esbuild. Don't try to make Vite use tsc; use tsc only for type checking in CI.

Composition pattern for EOS: Express (backend) + Vite (frontend dev proxy) + Rollup (prod build). Express serves `/api/*`; Vite owns everything else in dev; in prod, Express serves the built `dist/` as static files and still handles `/api/*`.

## Trajectory and Evolution

- **Vite 5 (current)** — Rollup 4, Node 18+, `server.hmr` improvements, stable.
- **Vite 6** — introduced Environment API (multi-environment builds: client, SSR, edge, worker). Begins the Rolldown migration path via "rolldown-vite" opt-in package.
- **Rolldown** — a Rust bundler by the Vite/Oxc team, Rollup-plugin-compatible. Ships with Vite 7 as default.
- **Oxc** — a Rust toolchain (resolver, parser, transformer, minifier, linter) that will gradually replace Babel/esbuild dependencies across the Vite ecosystem.
- **Environment API** — the big architectural bet. Lets frameworks define custom environments (e.g., Cloudflare Workers) with isolated module graphs and plugins.
- **Deprecated**: `server.https` shortcut (use `@vitejs/plugin-basic-ssl`), CJS-only config files (`vite.config.cjs` still works but ESM is preferred).
- **Investing in**: SSR/RSC support, Environment API, Rolldown integration, faster CSS processing (Lightning CSS).

For EOS: stay on Vite 5.x until Rolldown is stable in Vite 7. Don't adopt the Environment API yet unless doing SSR.

## Conceptual Model and Solution Recipes

The right mental model: **Vite is a module graph transformer with two execution engines**. The graph is the same; dev uses esbuild-per-module, prod uses Rollup-whole-graph. Plugins transform the graph. The config is a declarative description of how the graph should be built and served.

### Recipe 1 — React SPA with Tailwind + Express proxy (EOS default)

```
1. pnpm create vite my-app --template react-ts
2. pnpm add -D @vitejs/plugin-react tailwindcss postcss autoprefixer
3. npx tailwindcss init -p
4. Configure server.proxy for /api → Express
5. Set resolve.alias for @/* → ./src
6. Add VITE_API_URL to .env
7. pnpm dev (instant) → pnpm build → pnpm preview
```

### Recipe 2 — Library publishing

```
1. Set build.lib.entry = 'src/index.ts'
2. Set build.lib.formats = ['es', 'cjs']
3. Set build.rollupOptions.external = ['react', 'react-dom']
4. Use vite-plugin-dts for .d.ts emission
5. Set package.json exports map
```

### Recipe 3 — Monorepo with shared UI package

```
1. Root pnpm workspace
2. packages/ui — Vite library mode
3. apps/web — Vite app importing @acme/ui
4. resolve.dedupe: ['react', 'react-dom'] in app config
5. Run builds in dependency order via pnpm -r build
```

### Recipe 4 — Multi-page admin + marketing

```
build.rollupOptions.input = {
  main: resolve(__dirname, 'index.html'),
  admin: resolve(__dirname, 'admin/index.html'),
}
```

### Recipe 5 — Debug a slow HMR

```
1. Check browser console for "full reload" warnings
2. Inspect the file that triggered it
3. Ensure it exports ONLY React components
4. If mixed, extract non-component exports to a sibling file
5. Verify fast-refresh is active in DevTools → Components tab
```

## Industry Expert and Cutting-Edge Usage

Current frontier patterns from Vite core team (Anthony Fu, Patak, Bjorn Lu) and expert users:

- **`unplugin-*` ecosystem** — cross-bundler plugins (Vite + Webpack + Rollup + Rspack). `unplugin-auto-import`, `unplugin-icons`, `unplugin-vue-components`.
- **`vite-plugin-inspect`** — visualize plugin transform pipeline. Essential for debugging plugin issues.
- **`vite-plugin-pwa`** — Workbox-based PWA with precaching and runtime caching, zero-config for most cases.
- **`vite-plugin-compression`** — pre-compress assets (gzip + brotli) at build time for static hosting.
- **`vite-bundle-visualizer`** — Rollup Visualizer wrapper for `vite build` output analysis.
- **`@vitejs/plugin-react-swc`** — drop-in SWC replacement for `@vitejs/plugin-react` (faster transforms, Rust-based).
- **Partial hydration via Astro** — Astro uses Vite internally; islands architecture ships minimal JS.
- **Custom HMR channels** — plugins push structured events to clients for in-app dev tooling (e.g., DB schema changes → reload query cache).
- **`import.meta.glob('./*.md', { eager: true })`** — compile-time content collection for docs/blog sites.
- **Environment API (Vite 6)** — frameworks define client + ssr + edge environments with independent module graphs. Pattern adopted by Nuxt 4 and SvelteKit 3.
- **Lightning CSS transformer** — `css.transformer: 'lightningcss'` gives Rust-speed CSS processing; experimental but production-ready for Tailwind users.
- **Top tier apps on Vite**: Nuxt, SvelteKit, Astro, Remix, Qwik, Vike, Analog (Angular-on-Vite), Storybook.

The cutting-edge pattern for 2026: **Vite as the universal frontend build tool**. Every major meta-framework is migrating to Vite if they haven't already. Knowing Vite deeply pays off across every React/Vue/Svelte/Angular/Solid project.

---

## EOS Usage Patterns

- Every `/opt/OS/saas/*/` app uses Vite 5 with `@vitejs/plugin-react`.
- Path alias `@/*` → `./src/*` via both `tsconfig` and `resolve.alias`.
- Express backend runs on `localhost:3000`; Vite proxies `/api` → Express in dev.
- Production: `vite build` → `dist/` → served as static by Express in prod.
- Env vars: `VITE_API_URL`, `VITE_POSTHOG_KEY`, `VITE_SENTRY_DSN`. Secrets stay in `eos_ai/.env`.
- Vitest runs against the same `vite.config.ts` under a `test` key.

## Gotchas

- `tsconfig.paths` without matching `resolve.alias` → dev works, build fails. Use `vite-tsconfig-paths` as single source of truth.
- `process.env.FOO` in browser code → undefined at runtime. Use `import.meta.env.VITE_FOO`.
- Files exporting both components and non-components break React Fast Refresh silently (full reloads instead of HMR).
- Stale `node_modules/.vite` after dep swap → `rm -rf node_modules/.vite` and restart.
- `build.sourcemap: true` leaks source to end users. Use `'hidden'`.
- `define` values must be `JSON.stringify`'d — raw strings become syntax errors.
- On Linux, large repos hit inotify watch limits; raise `fs.inotify.max_user_watches`.
- Case-mismatch imports pass on macOS/Windows dev, fail on Linux CI. Always run `vite build` on Linux in CI.
