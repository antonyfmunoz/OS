# Vite — Realistic EOS Examples

All examples target Vite 5.x + React 18 + TypeScript strict + Tailwind + shadcn/ui + Express backend, matching the EOS SaaS stack.

---

## 1. Full EOS SaaS vite.config.ts

```ts
// /opt/OS/saas/my-app/vite.config.ts
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tsconfigPaths from "vite-tsconfig-paths";
import path from "node:path";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "VITE_");

  return {
    plugins: [
      react({
        // Use the automatic JSX runtime
        jsxRuntime: "automatic",
        // Enable babel plugins only if needed (adds overhead)
        babel: { plugins: [] },
      }),
      tsconfigPaths(), // derives resolve.alias from tsconfig paths
    ],

    resolve: {
      // Redundant safety net in case tsconfigPaths misses something
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
      // Force a single copy of React across the module graph
      dedupe: ["react", "react-dom"],
    },

    server: {
      host: "localhost",
      port: 5173,
      strictPort: true,
      proxy: {
        "/api": {
          target: env.VITE_API_URL ?? "http://localhost:3000",
          changeOrigin: true,
          secure: false,
          // If Express routes are NOT under /api, rewrite:
          // rewrite: (p) => p.replace(/^\/api/, ""),
        },
        // WebSocket proxy example
        "/ws": {
          target: "ws://localhost:3000",
          ws: true,
        },
      },
      fs: {
        strict: true,
        allow: [".."], // allow imports from monorepo root
      },
    },

    build: {
      outDir: "dist",
      target: "es2022",
      sourcemap: "hidden", // generated for Sentry, not served
      minify: "esbuild",
      cssCodeSplit: true,
      reportCompressedSize: false, // faster CI
      chunkSizeWarningLimit: 600,
      rollupOptions: {
        output: {
          manualChunks: {
            "react-vendor": ["react", "react-dom"],
            "query": ["@tanstack/react-query"],
            "radix": [
              "@radix-ui/react-dialog",
              "@radix-ui/react-dropdown-menu",
              "@radix-ui/react-popover",
              "@radix-ui/react-tooltip",
            ],
            "forms": ["react-hook-form", "@hookform/resolvers", "zod"],
          },
          assetFileNames: "assets/[name]-[hash][extname]",
          chunkFileNames: "assets/[name]-[hash].js",
          entryFileNames: "assets/[name]-[hash].js",
        },
      },
    },

    preview: {
      port: 4173,
      strictPort: true,
    },

    optimizeDeps: {
      include: [
        "react",
        "react-dom",
        "react-dom/client",
        "@tanstack/react-query",
      ],
      exclude: [
        // Deps that should NOT be pre-bundled (usually ESM-native)
      ],
    },
  };
});
```

---

## 2. `tsconfig.json` aligned with Vite

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,

    "moduleResolution": "bundler",
    "allowImportingTsExtensions": false,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",

    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,

    "baseUrl": ".",
    "paths": { "@/*": ["./src/*"] },
    "types": ["vite/client", "vitest/globals"]
  },
  "include": ["src", "vite.config.ts"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

---

## 3. `index.html` entry (the real entry point)

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <title>Initiate Arena</title>
  </head>
  <body class="bg-background text-foreground">
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

---

## 4. `src/vite-env.d.ts`

```ts
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string;
  readonly VITE_POSTHOG_KEY: string;
  readonly VITE_POSTHOG_HOST: string;
  readonly VITE_SENTRY_DSN: string;
  readonly VITE_APP_ENV: "development" | "staging" | "production";
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
```

---

## 5. Env files

```dotenv
# .env (committed, safe defaults)
VITE_API_URL=http://localhost:3000
VITE_APP_ENV=development

# .env.local (gitignored, per-dev overrides)
VITE_POSTHOG_KEY=phc_local_dev_key

# .env.production (committed, production build values)
VITE_API_URL=https://api.initiate-arena.com
VITE_APP_ENV=production
```

---

## 6. Tailwind + PostCSS setup

```js
// postcss.config.js
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

```js
// tailwind.config.js
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
```

---

## 7. Vitest setup (shared config)

```ts
/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tsconfigPaths from "vite-tsconfig-paths";

export default defineConfig({
  plugins: [react(), tsconfigPaths()],
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: true,
    coverage: {
      provider: "v8",
      reporter: ["text", "html", "lcov"],
      exclude: ["node_modules/", "src/test/", "**/*.d.ts"],
    },
  },
});
```

```ts
// src/test/setup.ts
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => cleanup());
```

---

## 8. `package.json` scripts

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc --noEmit && vite build",
    "preview": "vite preview",
    "test": "vitest",
    "test:ui": "vitest --ui",
    "lint": "eslint . --ext ts,tsx"
  },
  "dependencies": {
    "react": "18.3.1",
    "react-dom": "18.3.1",
    "@tanstack/react-query": "5.56.0",
    "react-hook-form": "7.53.0",
    "@hookform/resolvers": "3.9.0",
    "zod": "3.23.8"
  },
  "devDependencies": {
    "vite": "5.4.10",
    "@vitejs/plugin-react": "4.3.3",
    "vite-tsconfig-paths": "5.0.1",
    "vitest": "2.1.3",
    "typescript": "5.6.3",
    "@types/react": "18.3.12",
    "@types/react-dom": "18.3.1",
    "tailwindcss": "3.4.14",
    "postcss": "8.4.47",
    "autoprefixer": "10.4.20"
  }
}
```

---

## 9. Dynamic content loading with `import.meta.glob`

```ts
// Load all markdown files in /src/posts at build time
const posts = import.meta.glob("./posts/*.md", {
  eager: true,
  query: "?raw",
  import: "default",
});

// posts is Record<string, string>
for (const [path, content] of Object.entries(posts)) {
  console.log(path, content);
}
```

---

## 10. Worker bundle

```ts
// src/workers/crunch.worker.ts
self.addEventListener("message", (e) => {
  const result = heavyComputation(e.data);
  self.postMessage(result);
});
```

```ts
// src/components/Crunch.tsx
import CrunchWorker from "@/workers/crunch.worker.ts?worker";

const worker = new CrunchWorker();
worker.postMessage({ data: 42 });
worker.onmessage = (e) => console.log(e.data);
```

---

## 11. Production serving from Express

```ts
// server/index.ts — Express serves dist/ in production
import express from "express";
import path from "node:path";

const app = express();

// API routes first
app.use("/api", apiRouter);

// Static SPA dist in production
if (process.env.NODE_ENV === "production") {
  const distDir = path.resolve(__dirname, "../dist");
  app.use(express.static(distDir));
  // SPA fallback — every non-API route returns index.html
  app.get("*", (_req, res) => res.sendFile(path.join(distDir, "index.html")));
}

app.listen(3000);
```
