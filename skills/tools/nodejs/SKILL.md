---
name: nodejs
description: "Use when running, installing, or debugging Node.js runtime, choosing Node version, configuring package.json/tsconfig, using npm/pnpm/yarn, ESM vs CJS, native fetch, worker_threads, AbortController, debugging memory/CPU, or shipping Node services."
allowed-tools: "Read, Bash, Write, Edit"
version: 1.0
source_url: "https://nodejs.org/api"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "Node 22 LTS (Jod)"
sdk_version: "npm 10.x / pnpm 9.x"
speed_category: stable
---

# Tool: Node.js

## What This Tool Does

Node.js is a single-threaded, event-driven JavaScript runtime built on V8 and
libuv. Its entire personality is "one thread, one event loop, never block it."
Everything interesting is async; everything synchronous in a request path is a
bug waiting to happen. Node is an I/O orchestration runtime that happens to use
JavaScript — not a general-purpose language platform.

Core capabilities:

- **Event loop + libuv thread pool** — non-blocking I/O for file, network, DNS,
  crypto, zlib work across phases (timers → poll → check → close) with microtask
  draining between every callback
- **Standard kit shipping in core** — global `fetch` (undici), `node:test`,
  `--env-file`, `--watch`, `--experimental-strip-types`, `node:sqlite`, global
  `WebSocket`, `structuredClone`, `crypto.randomUUID`, Web Streams
- **ESM + CJS modules** — strict ESM resolution, conditional `exports`, stable
  `require(esm)` since Node 22.12
- **Worker threads, child_process, cluster** — concurrency primitives for CPU
  work, external binaries, and multi-process HTTP
- **Streams (Node + Web)** — backpressure-aware pipelines, interop with
  `Readable.toWeb()` / `.fromWeb()`
- **Built-in profiling** — `--inspect`, `--cpu-prof`, `--heap-prof`,
  `perf_hooks`, `monitorEventLoopDelay`, `process.report`

## EOS Integration

Node is the runtime for every EOS SaaS-layer product. The Python `eos_ai/`
intelligence layer orchestrates agents; the TypeScript `saas/` layer ships
user-facing product.

Where EOS uses Node:

- **saas/ frontends** — React 18 + Vite + Tailwind + shadcn/ui dev servers and
  builds, tested with **vitest**
- **Express / Hono APIs** — auth, webhooks, BFF endpoints in front of Neon
  Postgres via **Drizzle ORM**
- **Build pipeline** — `pnpm typecheck && pnpm test && pnpm build` in CI before
  every deploy
- **Agent-facing tools** — AI provider clients (Anthropic, Gemini, Ollama)
  written in TS use the canonical `AbortController` + timeout + chained signal
  pattern for every outbound call

Package manager choice: **pnpm preferred** for every SaaS repo. Content-
addressed store, fast monorepo installs, `--frozen-lockfile` in CI. Corepack
pins the exact version via `packageManager` in `package.json`. Never
`npm install` in CI — always `npm ci` or `pnpm install --frozen-lockfile`.

When to choose Node over Python in EOS:
- I/O orchestration, streaming, WebSocket fan-out, edge functions
- Anything user-facing (React lives in Node tooling)
- AI agent orchestration where the Vercel AI SDK is the right abstraction

When to stay in Python:
- Anything touching `eos_ai/` intelligence primitives
- ML inference, heavy data munging, long-running stateful loops

Canonical EOS Node stack:
**Hono + Drizzle + pino + OpenTelemetry + Vercel AI SDK**, systemd in front,
Node 22 LTS, pnpm, tsx in dev, `tsc --noEmit` in CI.

## Authentication

Node itself has no auth model. The surface that matters is **npm registry
authentication**:

```bash
# Personal access token for npmjs.org
npm login                              # interactive, writes to ~/.npmrc
npm config set //registry.npmjs.org/:_authToken "$NPM_TOKEN"

# Scoped package on a private registry
cat >> ~/.npmrc <<EOF
@eos:registry=https://npm.pkg.github.com
//npm.pkg.github.com/:_authToken=${GITHUB_TOKEN}
EOF
```

Never commit `.npmrc` with a token. Use env substitution in CI:
`//registry.npmjs.org/:_authToken=\${NPM_TOKEN}` and inject `NPM_TOKEN` from
the secret store. `pnpm` reads the same `.npmrc` format.

Node 20+ also ships an **experimental permission model** — a Deno-style
sandbox useful for CI scripts against untrusted input:

```bash
node --experimental-permission \
     --allow-fs-read=/etc --allow-fs-write=/tmp --allow-net script.js
```

## Quick Reference

### Version management (ranked)

```bash
# fnm — Rust, fast, reads .nvmrc with --use-on-cd
curl -fsSL https://fnm.vercel.app/install | bash
fnm install 22 && fnm use 22

# Volta — pins toolchain per project via package.json
volta install node@22 && volta pin node@22.11.0

# nvm — most common, slow shell startup
nvm install --lts=jod

# NodeSource apt (VPS / container baseline)
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
apt-get install -y nodejs
```

Pin per-project:

```bash
echo '22.11.0' > .nvmrc

# package.json
# "engines": { "node": ">=22.11.0 <23", "pnpm": ">=9" }
# "packageManager": "pnpm@9.12.0+sha512..."

corepack enable
corepack use pnpm@9.12.0
```

### CLI flags you will actually use

```bash
node --env-file=.env app.js                  # replaces dotenv (20.6+)
node --env-file-if-exists=.env.local app.js  # 22.7+
node --watch src/index.js                    # replaces nodemon
node --test                                  # run node:test suites
node --test --watch --test-reporter=spec
node --test --experimental-test-coverage     # 22+ built-in coverage
node --experimental-strip-types script.ts    # 22.6+ (default on in 24)
node --inspect=0.0.0.0:9229 app.js           # Chrome DevTools
node --inspect-brk app.js                    # break before user code
node --cpu-prof --cpu-prof-dir=./profiles app.js
node --heap-prof --heap-prof-dir=./profiles app.js
node --trace-sync-io app.js                  # warn on sync I/O after first tick
node --enable-source-maps app.js             # readable prod stack traces
NODE_OPTIONS="--max-old-space-size=3072" node app.js
```

### Package manager commands

```bash
# npm
npm ci                        # CI mode — clean install from lockfile
npm install pkg               # dev
npm audit && npm audit fix
npm outdated
npx some-tool                 # one-shot, no global install

# pnpm
pnpm install --frozen-lockfile
pnpm add pkg --filter web     # workspace-scoped
pnpm -r build                 # recursive across workspace
pnpm dlx some-tool            # npx equivalent
pnpm audit
```

### package.json scripts (canonical TS service)

```json
{
  "type": "module",
  "engines": { "node": ">=22.11.0 <23" },
  "packageManager": "pnpm@9.12.0",
  "scripts": {
    "dev": "tsx watch src/index.ts",
    "build": "tsc -p tsconfig.build.json",
    "typecheck": "tsc --noEmit",
    "test": "node --test --test-reporter=spec",
    "start": "node --enable-source-maps --env-file=.env dist/index.js"
  }
}
```

### Minimal zero-dep server

```js
// server.js — node --env-file=.env --watch server.js
import { createServer } from 'node:http';
const server = createServer(async (req, res) => {
  if (req.url === '/health') {
    res.writeHead(200, { 'content-type': 'application/json' });
    res.end(JSON.stringify({ ok: true }));
    return;
  }
  res.writeHead(404).end();
});
server.keepAliveTimeout = 65_000;  // > ALB idle timeout
server.headersTimeout   = 66_000;  // strictly greater
server.listen(process.env.PORT ?? 3000);
```

## Conceptual Model

**A Node app is a single JavaScript thread with an event loop.** The loop
dispatches I/O callbacks through six phases: timers → pending callbacks →
idle/prepare → poll → check → close. Between *every* callback the microtask
queue drains completely: `process.nextTick` first, then Promise jobs
(`then`/`catch`/`finally`, `queueMicrotask`).

Priority order:

```
process.nextTick  >  Promise microtasks  >  macrotask phase callbacks
```

libuv owns the async I/O abstraction and a **4-thread default pool** shared by
`fs`, `dns.lookup`, `crypto`, and `zlib`. Saturate it and you get mysterious
tail latency. `UV_THREADPOOL_SIZE=64` is a real knob.

CPU-bound JavaScript runs on the main thread. Anything > ~10ms either goes in
a `worker_threads` worker (shared memory via `SharedArrayBuffer`) or leaves
Node entirely (child process, separate Rust/Go service). `cluster` is legacy —
put N processes behind nginx/ALB instead.

ESM vs CJS:
- ESM triggered by `.mjs` or `"type": "module"`
- Strict: `import './foo.js'` (extension required), no `__dirname`, no
  `index.js` magic, top-level await allowed
- `require(esm)` stable in Node 22.12 for synchronous ESM graphs
- CJS escape hatch: `.cjs` extension, `createRequire(import.meta.url)`

**Web Standards win.** `fetch`, `Request`, `Response`, `ReadableStream`,
`URL`, `crypto.subtle` — code to these and your service ports to Bun, Deno,
Cloudflare Workers, and Vercel Edge with no changes. This is the core bet of
the modern Node stack.

## Gotchas

- **`keepAliveTimeout < LB idle timeout` → sporadic 502s.** The #1 Node-behind-
  ALB bug. Set `server.keepAliveTimeout = 65_000` AND `server.headersTimeout =
  66_000` (must be strictly greater). AWS ALB defaults to 60s idle.
- **Forgetting file extensions in ESM imports** → `ERR_MODULE_NOT_FOUND`. You
  must write `import './foo.js'` even in TypeScript source where the file is
  `.ts`. Hardest-hit migration pain point.
- **`unhandledRejection` crashes the process since Node 15.** This is correct
  behavior. Register a handler that logs to stderr THEN exits. Never try to
  "keep the server running" after `uncaughtException`.
- **libuv thread pool default 4.** `fs` + `dns.lookup` + `crypto` + `zlib`
  share four slots. Symptoms: random latency spikes. Fix: `UV_THREADPOOL_SIZE=64`
  or use `dns.resolve*` (truly async, no pool).
- **`fs.readFileSync` in a request handler** blocks the entire event loop for
  every concurrent request. `--trace-sync-io` catches these post-first-tick.
- **`.pipe()` chains swallow errors.** Use `stream.pipeline()` from
  `node:stream/promises`. `.pipe()` is banned in production code.
- **`Promise.all` over thousands of items** opens N concurrent operations and
  exhausts sockets/file handles. Use `p-limit` with a concrete concurrency cap.
- **`process.exit(0)` does NOT flush piped stdout.** You lose log lines under
  systemd-journal or `tee`. Set `process.exitCode = 0` and let the loop drain.
- **Distro Node is always 2-4 majors stale.** Ubuntu 22.04 ships Node 12.22,
  24.04 ships 18.19 (EOL April 2025). Always fnm / Volta / NodeSource.
- **`require(esm)` requires a fully synchronous ESM graph** — any top-level
  await in the graph throws `ERR_REQUIRE_ASYNC_MODULE`.
- **`--max-old-space-size` does not bound everything.** Native buffers, V8
  code space, stack, and worker isolates are separate. Container OOMs at ~1.5x
  the flag value are normal. Set the flag to ~75% of the cgroup limit.
- **No `__dirname` in ESM.** Use `import.meta.dirname` (Node 20.11+) or
  `fileURLToPath(import.meta.url)`.
- **JSON imports need an attribute:** `import pkg from './package.json' with
  { type: 'json' };`.
- **Container hangs 30s on SIGTERM then SIGKILL** → Node is PID 1 with no init
  forwarding signals AND no SIGTERM handler. Fix: `docker run --init` AND
  register a graceful shutdown handler.
- **Recursive `process.nextTick`** starves I/O forever. Use `setImmediate` for
  recursive deferral.
- **`exports` field ordering matters** — `types` MUST come first,
  `default` MUST come last. Order determines resolution.
- **`npm install` in CI** mutates the lockfile and breaks reproducibility.
  ALWAYS `npm ci` or `pnpm install --frozen-lockfile`.
- **Global `npm i -g`** pollutes the system, requires sudo, breaks under fnm
  version switches. Use devDependency + `npx` / `pnpm dlx`, or Volta.

See references/best_practices.md for the full 19-section creator-level knowledge base.
See references/examples.md for EOS-specific recipes.
See references/anti_patterns.md for the full failure catalog.
