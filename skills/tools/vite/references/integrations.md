# Vite — Stack Integrations (EOS SaaS)

How Vite composes with the exact stack used in `/opt/OS/saas/*/`: React 18, TypeScript strict, Tailwind, shadcn/ui, React Query, React Hook Form + Zod, Express backend, Drizzle ORM, Vitest.

---

## React 18

**Plugin:** `@vitejs/plugin-react` (Babel-based, default) OR `@vitejs/plugin-react-swc` (SWC-based, faster).

```ts
import react from "@vitejs/plugin-react";
plugins: [react()]
```

What it does:
- Transforms JSX via Babel (or SWC).
- Wires React Fast Refresh for HMR.
- Injects the automatic JSX runtime (`react/jsx-runtime`).
- Handles `.tsx` and `.jsx` files.

Pin `react` and `react-dom` to the same exact version. Use `resolve.dedupe: ['react', 'react-dom']` in monorepos.

---

## TypeScript (strict)

Vite handles TS via **esbuild's transpile-only mode**. It does NOT type-check. TS paths are NOT respected by the resolver.

```json
// tsconfig.json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "isolatedModules": true,
    "noEmit": true,
    "strict": true,
    "jsx": "react-jsx",
    "types": ["vite/client"]
  }
}
```

`isolatedModules: true` is required — esbuild transpiles files in isolation, so it can't see across-file type info.

Always run `tsc --noEmit` before `vite build` in CI. Use `vite-tsconfig-paths` to share `paths` between TS and Vite.

---

## Tailwind CSS

**Setup:** PostCSS plugin, no Vite config changes needed.

```js
// postcss.config.js
export default {
  plugins: { tailwindcss: {}, autoprefixer: {} },
};
```

```js
// tailwind.config.js
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  // ...
};
```

```css
/* src/index.css */
@tailwind base;
@tailwind components;
@tailwind utilities;
```

```tsx
// src/main.tsx
import "./index.css";
```

Tailwind's JIT watches the `content` globs; Vite watches the CSS file. On class change: Tailwind rebuilds CSS → Vite HMR patches → browser updates, no reload.

Optional: `css.transformer: 'lightningcss'` in vite.config.ts for faster CSS processing (Vite 5+).

---

## shadcn/ui

shadcn/ui is NOT an npm package — it's a CLI that copies component source into your `src/components/ui/`. Vite treats them as regular source files.

Requirements:
- Tailwind + PostCSS configured.
- Path alias `@/*` → `./src/*` (shadcn expects this).
- `tailwindcss-animate` plugin.
- `class-variance-authority`, `clsx`, `tailwind-merge` deps.

shadcn components use Radix primitives under the hood. Group them in `manualChunks.radix` for better caching:

```ts
build: {
  rollupOptions: {
    output: {
      manualChunks: {
        radix: ["@radix-ui/react-dialog", "@radix-ui/react-popover", "@radix-ui/react-dropdown-menu"],
      },
    },
  },
}
```

---

## @tanstack/react-query

No Vite-specific configuration. Just import and use.

```tsx
// src/main.tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, refetchOnWindowFocus: false } },
});

root.render(
  <QueryClientProvider client={queryClient}>
    <App />
  </QueryClientProvider>
);
```

Optimize chunking:
```ts
manualChunks: { query: ["@tanstack/react-query"] }
```

React Query should be the ONLY way client components touch the Express backend — goes through the Vite proxy in dev, through the static-served build in prod.

---

## React Hook Form + Zod

```ts
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

const schema = z.object({ email: z.string().email() });
const form = useForm({ resolver: zodResolver(schema) });
```

No Vite config. Zod is ESM-native; pre-bundles cleanly.

---

## Express backend (dev proxy)

Vite serves the frontend on 5173; Express runs on 3000. Vite proxies `/api` to Express so the browser only sees one origin (no CORS).

```ts
server: {
  proxy: {
    "/api": {
      target: "http://localhost:3000",
      changeOrigin: true,
    },
  },
}
```

In production:
```ts
// Express serves dist/ statically + API routes
app.use("/api", apiRouter);
app.use(express.static("dist"));
app.get("*", (_, res) => res.sendFile(path.resolve("dist/index.html")));
```

Run both in dev with one command:
```json
"dev": "concurrently \"tsx watch server/index.ts\" \"vite\""
```

---

## Drizzle ORM (server-only, NEVER bundled to client)

Drizzle runs only on the Express server. It must never appear in the client bundle — it depends on `pg`, `node:crypto`, and other Node builtins.

**Rule:** `server/` code is not reachable from `src/` code. Enforce with an ESLint rule:

```js
// .eslintrc.cjs
rules: {
  "no-restricted-imports": ["error", {
    patterns: [{ group: ["**/server/**"], message: "Server code must not be imported in client code" }],
  }],
}
```

Client talks to Drizzle-backed routes only via `fetch("/api/...")`.

---

## Vitest

Vitest is a Vite-native test runner. It reuses your `vite.config.ts` — same plugins, same aliases, same CSS handling.

```ts
/// <reference types="vitest" />
export default defineConfig({
  plugins: [react(), tsconfigPaths()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: true,
  },
});
```

Benefits:
- Same transform pipeline as dev (no Jest/Babel mismatch).
- Instant startup (no separate config).
- HMR-like watch mode via `vitest --watch`.

---

## PostHog / Sentry / analytics

Load via `import.meta.env.VITE_POSTHOG_KEY`. Lazy-init in a root effect.

```tsx
useEffect(() => {
  if (import.meta.env.VITE_POSTHOG_KEY) {
    posthog.init(import.meta.env.VITE_POSTHOG_KEY, {
      api_host: import.meta.env.VITE_POSTHOG_HOST,
    });
  }
}, []);
```

For Sentry source maps: `build.sourcemap: "hidden"` + Sentry CLI upload step.

---

## Monorepo (pnpm workspace)

```
/opt/OS/saas/
  package.json          (workspace root)
  pnpm-workspace.yaml
  packages/
    ui/                 (shared shadcn + Tailwind config)
  apps/
    initiate-arena/
      vite.config.ts
    creator-os/
      vite.config.ts
```

`pnpm-workspace.yaml`:
```yaml
packages:
  - "apps/*"
  - "packages/*"
```

Each app imports `@acme/ui` as a workspace package. Vite resolves it via pnpm symlinks. Use `resolve.dedupe: ['react', 'react-dom']` in each app to prevent duplicate React instances.

---

## Composition summary

```
Browser
  ↓ HTTP (dev: 5173, prod: 3000)
Vite dev server OR Express + dist/
  ↓ /api proxy (dev) OR Express router (prod)
Express
  ↓
Drizzle ORM
  ↓
Neon Postgres
```

Vite owns: HTML/CSS/TS transform, HMR, dev proxy, prod bundle.
Express owns: API routes, auth, DB access, static serving in prod.
Never cross the streams.
