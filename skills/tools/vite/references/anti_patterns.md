# Vite — Anti-Patterns and Real Failure Modes

Every item here is a real failure seen in production React+TS+Vite apps. Exact wrong code, exact correct code, exact error message where possible.

---

## 1. `process.env` in browser code

**Wrong:**
```ts
const url = process.env.REACT_APP_API_URL; // undefined at runtime
```

**Error (runtime):**
```
Uncaught ReferenceError: process is not defined
```

**Correct:**
```ts
const url = import.meta.env.VITE_API_URL;
```

Vite only replaces `import.meta.env.VITE_*` at build time. `process.env` doesn't exist in the browser. If a dep references `process.env.NODE_ENV`, Vite rewrites it automatically — but it doesn't do so for your code.

---

## 2. Secret behind `VITE_*`

**Wrong:**
```dotenv
VITE_STRIPE_SECRET_KEY=sk_live_xxxxxxxxxxxx   # SHIPS TO BROWSER
```

**Correct:**
```dotenv
# Server-only (no VITE_ prefix), read by Express, never bundled
STRIPE_SECRET_KEY=sk_live_xxxxxxxxxxxx
# Public (Stripe publishable key is safe in the browser)
VITE_STRIPE_PUBLISHABLE_KEY=pk_live_xxxxxxxxxxxx
```

Anything prefixed `VITE_` gets inlined as a string literal into the bundle. Search the built `dist/` for the variable name — if you see it, it's public.

---

## 3. `tsconfig.paths` without `resolve.alias`

**Wrong (tsconfig only):**
```json
{ "paths": { "@/*": ["./src/*"] } }
```

**Error (build):**
```
[vite] Rollup failed to resolve import "@/lib/utils" from "src/App.tsx".
```

**Correct:** either mirror in vite.config.ts:
```ts
resolve: { alias: { "@": path.resolve(__dirname, "./src") } }
```

OR use `vite-tsconfig-paths` as a single source of truth:
```ts
import tsconfigPaths from "vite-tsconfig-paths";
export default defineConfig({ plugins: [react(), tsconfigPaths()] });
```

TypeScript `paths` only affect the type checker. Vite/Rollup don't read tsconfig for resolution.

---

## 4. Mixed exports break React Fast Refresh

**Wrong:**
```tsx
// Header.tsx
export const HEADER_HEIGHT = 64;
export default function Header() { ... }
```

**Symptom:** every edit to `Header.tsx` triggers a full page reload instead of HMR. Console shows: `[vite] hmr invalidate /src/Header.tsx Could not Fast Refresh ("HEADER_HEIGHT" export is incompatible)`.

**Correct:** split non-component exports into a sibling file.
```tsx
// Header.constants.ts
export const HEADER_HEIGHT = 64;

// Header.tsx — only component exports
export default function Header() { ... }
```

React Fast Refresh requires files to export ONLY React components (or nothing).

---

## 5. Unquoted `define` values

**Wrong:**
```ts
define: {
  __APP_VERSION__: "1.0.0", // NO — becomes: const x = 1.0.0 → SyntaxError
}
```

**Error:**
```
Unexpected number
```

**Correct:**
```ts
define: {
  __APP_VERSION__: JSON.stringify("1.0.0"),
}
```

`define` is textual substitution. Always `JSON.stringify()` string values, including booleans and objects.

---

## 6. CJS-only dep with deep imports

**Wrong:** importing a CJS-only package with deep paths:
```ts
import debounce from "lodash/debounce"; // CJS
```

**Error (dev):**
```
[vite] Pre-transform error: Failed to resolve entry for package "lodash".
```

**Correct:** use the ESM variant OR force pre-bundling:
```ts
// Option A — use lodash-es (ESM)
import { debounce } from "lodash-es";

// Option B — force optimize
// vite.config.ts
optimizeDeps: { include: ["lodash/debounce"] }
```

---

## 7. Leaving `optimizeDeps.force: true`

**Wrong:**
```ts
optimizeDeps: { force: true } // re-bundles node_modules on EVERY boot
```

**Correct:**
```ts
optimizeDeps: { } // let Vite invalidate the cache automatically
```

Use `vite --force` as a one-off CLI flag when debugging, never in config.

---

## 8. `build.sourcemap: true` in production

**Wrong:**
```ts
build: { sourcemap: true } // .map files served publicly alongside JS
```

**Correct (for error tracking):**
```ts
build: { sourcemap: "hidden" } // generated but NOT referenced in output
```

Then upload `.map` files to Sentry/Datadog at deploy time and delete them from the public `dist/`.

---

## 9. SPA fallback missing in Express production serve

**Wrong:**
```ts
app.use(express.static("dist"));
// No catch-all — /dashboard returns 404
```

**Correct:**
```ts
app.use(express.static("dist"));
app.get("*", (_req, res) => res.sendFile(path.resolve("dist/index.html")));
```

Vite SPAs rely on client-side routing. Every non-API path must serve `index.html`.

---

## 10. Importing files outside project root without `server.fs.allow`

**Wrong (monorepo):**
```ts
import foo from "../../../shared/foo"; // outside project root
```

**Error (dev):**
```
The request url "/Users/.../shared/foo.ts" is outside of Vite serving allow list.
```

**Correct:**
```ts
server: { fs: { allow: [".."] } }
```

Or restructure to use pnpm workspaces + package imports.

---

## 11. SSR bundling a server-only package into the client

**Wrong:** importing Drizzle ORM from a client component.
```tsx
// src/pages/Dashboard.tsx
import { db } from "@/server/db"; // drags drizzle + pg into the bundle
```

**Symptom:** bundle size explodes, browser errors about `node:fs` or `node:crypto`.

**Correct:** server code is reached ONLY via the Express API.
```tsx
const { data } = useQuery({
  queryKey: ["leads"],
  queryFn: () => fetch("/api/leads").then(r => r.json()),
});
```

Keep `server/` and `src/` as separate dependency islands.

---

## 12. `useLayoutEffect` warning in SSR

**Wrong:**
```tsx
import { useLayoutEffect } from "react";
useLayoutEffect(() => { ... }, []);
```

**Warning (SSR):**
```
useLayoutEffect does nothing on the server
```

**Correct:** use `useEffect` or an isomorphic layout effect shim. Only relevant if you're SSR'ing — pure SPAs are fine.

---

## 13. Pre-bundle cache wedge after dep swap

**Wrong:** changing a dep version and expecting dev to recover automatically.

**Symptom:**
```
[vite] The file does not exist at "node_modules/.vite/deps/chunk-XXX.js"
```

**Fix:**
```bash
rm -rf node_modules/.vite
pnpm dev
```

Vite usually invalidates the cache on lockfile changes but not always.

---

## 14. `public/` file imported as a module

**Wrong:**
```ts
import logo from "/public/logo.png"; // 404 in build
```

**Correct:**
```tsx
// Reference public files by absolute path at runtime
<img src="/logo.png" alt="" />

// OR import from src/ for fingerprinting
import logo from "@/assets/logo.png";
<img src={logo} />
```

Files in `public/` are copied verbatim and referenced absolutely. Files in `src/` are hashed and referenced via `import`.

---

## 15. Running `vite dev` in production

**Wrong:** deploying with `vite` or `vite dev` as the start command.

**Correct:** `vite build` → serve `dist/` via Express/nginx/Caddy. `vite preview` is for LOCAL verification of the prod build, never for production serving.

---

## 16. Top-level await without target bump

**Wrong:**
```ts
// Default target is es2020, no top-level await
const data = await fetch("/config.json").then(r => r.json());
```

**Error:**
```
Top-level await is not available in the configured target environment
```

**Correct:**
```ts
build: { target: "es2022" }
```

---

## 17. Running TypeScript checks through Vite

**Wrong:** assuming `vite build` type-checks the code.

**Reality:** Vite uses esbuild which transpiles but does NOT type-check. Runtime errors from broken types slip through.

**Correct:** run `tsc --noEmit` in CI AND in the build script:
```json
"build": "tsc --noEmit && vite build"
```
