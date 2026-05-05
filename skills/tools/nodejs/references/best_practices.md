# Node.js — Creator-Level Best Practices
Source: https://nodejs.org/api, nodeland.dev (Matteo Collina), Node TSC meeting notes, undici, V8 team blogs
API Version: Node 22 LTS ("Jod"), Node 24 current
SDK Version: npm 10.x, pnpm 9.x, Corepack bundled
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication

Node itself has no auth model. The authentication surface is the npm ecosystem.

**npm registry tokens.** `npm login` writes `//registry.npmjs.org/:_authToken=...`
to `~/.npmrc`. For CI, never commit a token — use env substitution:

```ini
# .npmrc (committed, safe)
@eos:registry=https://npm.pkg.github.com
//npm.pkg.github.com/:_authToken=${GITHUB_TOKEN}
//registry.npmjs.org/:_authToken=${NPM_TOKEN}
always-auth=true
engine-strict=true
```

npm expands `${VAR}` from the environment at install time. `pnpm` reads the
same file; `yarn` (classic) reads it; yarn berry uses `.yarnrc.yml` instead.

**Scoped packages** map a scope to a private registry:

```bash
npm config set @eos:registry https://npm.pkg.github.com
npm config set //npm.pkg.github.com/:_authToken "$GITHUB_TOKEN"
```

Only `@eos/*` packages hit the private registry; everything else goes to
npmjs.org.

**Token types on npmjs.org:**
- **Automation token** — bypasses 2FA, use in CI for publish + install
- **Publish token** — requires 2FA, use for interactive publish
- **Read-only token** — install-only, safe for dev machines

**GitHub Packages** requires a PAT with `read:packages` (install) or
`write:packages` (publish). Classic PAT only — fine-grained PATs do not yet
support the npm registry API reliably.

**Signed provenance (npm 9.5+):** `npm publish --provenance` attaches a
Sigstore attestation linking the tarball to its GitHub Actions workflow run.
Consumers verify with `npm audit signatures`.

**Node's own permission model (experimental):**

```bash
node --experimental-permission \
     --allow-fs-read=/etc --allow-fs-read=/opt/app \
     --allow-fs-write=/tmp \
     --allow-net \
     --allow-child-process \
     app.js
```

Deno-style sandbox retrofitted into Node. Useful for CI tools running
untrusted package scripts. Still experimental — not yet recommended for
production.

## Core Operations with Exact Signatures

### `node` CLI — the flags that matter

```bash
node [options] [script.js | -e "code" | -] [arguments]

# Execution
node script.js
node -e "console.log(process.version)"
node -                              # read script from stdin
node --eval "..." --print            # -p prints the expression value

# Environment
node --env-file=.env script.js
node --env-file=.env --env-file=.env.local script.js   # later wins
node --env-file-if-exists=.env.local script.js         # 22.7+

# Modules
node --input-type=module -e "import fs from 'node:fs'; ..."
node --experimental-strip-types src/index.ts           # 22.6+
node --experimental-transform-types src/index.ts       # 23+ (enums, namespaces)
node --import tsx src/index.ts                         # loader form
node --loader ts-node/esm src/index.ts                 # legacy loader

# Dev loop
node --watch src/index.js
node --watch-path=./src --watch-path=./config src/index.js
node --test
node --test --watch --test-reporter=spec
node --test --experimental-test-coverage

# Debugging
node --inspect=0.0.0.0:9229 app.js
node --inspect-brk app.js
node --enable-source-maps app.js
node --trace-sync-io app.js
node --trace-warnings app.js
node --trace-deprecation app.js

# Profiling
node --cpu-prof --cpu-prof-dir=./profiles app.js
node --heap-prof --heap-prof-dir=./profiles app.js
node --prof app.js
node --prof-process isolate-*.log > processed.txt

# Memory
node --max-old-space-size=4096 app.js                  # MB, old generation
node --max-semi-space-size=128 app.js                  # young generation
node --optimize-for-size app.js                        # serverless

# Diagnostic reports
node --report-on-fatalerror --report-on-signal --report-dir=/var/log/node app.js

# Unhandled rejection mode
node --unhandled-rejections=throw app.js               # default since 15 — crash
node --unhandled-rejections=warn app.js                # legacy
```

### `npm` — the commands that matter

```bash
npm init -y                          # package.json scaffold
npm install                          # install from package.json, may mutate lockfile
npm install pkg                      # add dependency
npm install pkg@1.2.3                # exact version
npm install -D pkg                   # devDependency
npm install -g pkg                   # global — avoid
npm ci                               # CI mode — clean install, fails on drift
npm ls                               # dependency tree
npm ls pkg                           # where is pkg installed, at which version
npm outdated                         # what's behind
npm update                           # bump within semver range
npm audit                            # vuln scan
npm audit fix                        # auto-patch where possible
npm audit signatures                 # verify Sigstore provenance
npm publish                          # publish to registry
npm publish --provenance             # with Sigstore attestation
npm dedupe                           # flatten duplicates
npm run <script>                     # run package.json script
npm exec pkg                         # equivalent to npx
npx pkg                              # run one-shot without installing globally
npm view pkg                         # registry metadata
npm view pkg versions --json         # all published versions
```

### `pnpm` — the commands that matter

```bash
pnpm install                         # install from lockfile
pnpm install --frozen-lockfile       # CI mode
pnpm add pkg                         # add dep
pnpm add -D pkg                      # dev dep
pnpm add -w pkg                      # add at workspace root
pnpm add pkg --filter web            # workspace-scoped
pnpm remove pkg
pnpm update
pnpm -r build                        # recursive across workspace
pnpm --filter web dev                # one package
pnpm dlx pkg                         # npx equivalent
pnpm audit
pnpm outdated -r                     # recursive
pnpm store prune                     # GC content-addressed store
pnpm why pkg                         # why is this installed
```

### package.json fields that matter

```json
{
  "name": "@eos/api",
  "version": "1.2.3",
  "type": "module",
  "main": "./dist/index.cjs",
  "module": "./dist/index.js",
  "types": "./dist/index.d.ts",
  "exports": {
    ".": {
      "types": "./dist/index.d.ts",
      "import": "./dist/index.js",
      "require": "./dist/index.cjs",
      "default": "./dist/index.js"
    },
    "./package.json": "./package.json"
  },
  "bin": { "eos-api": "./dist/cli.js" },
  "files": ["dist", "README.md"],
  "engines": { "node": ">=22.11.0 <23", "pnpm": ">=9" },
  "packageManager": "pnpm@9.12.0+sha512....",
  "scripts": {
    "dev": "tsx watch src/index.ts",
    "build": "tsc -p tsconfig.build.json",
    "typecheck": "tsc --noEmit",
    "test": "node --test --test-reporter=spec",
    "start": "node --enable-source-maps dist/index.js"
  },
  "dependencies": { "hono": "^4.6.0" },
  "devDependencies": { "typescript": "^5.6.0", "tsx": "^4.19.0" }
}
```

**`exports` field ordering is load-bearing.** `types` first, `default` last.
Bundlers and the Node resolver walk keys in order and return the first match.

## Pagination Patterns

Node itself has no inherent pagination concept — it is a runtime, not an API.
The npm registry exposes package metadata as single documents, not paged lists.

The only pagination surface in the Node ecosystem worth knowing:

- **`npm search --json --searchlimit=N`** — registry search results cap at
  250 by default, max 1000 via `--searchlimit`. No cursor; re-query with a
  narrower term.
- **GitHub Packages / npm registry audit APIs** use the same pagination as
  the GitHub REST API (`?per_page=100&page=N`, `Link` header with `rel="next"`).

For any paging *inside* your Node code — database cursors, S3 listings, API
responses — use async iterators:

```js
async function* allPages(fetchPage) {
  let cursor;
  do {
    const page = await fetchPage(cursor);
    yield* page.items;
    cursor = page.nextCursor;
  } while (cursor);
}

for await (const item of allPages(ctx => db.list({ after: ctx }))) {
  await process(item);
}
```

This is the canonical Node-2026 idiom for any paginated source.

## Rate Limits

### npm registry (registry.npmjs.org)

- Unauthenticated install reads: no hard rate limit, but aggressive IPs get
  throttled to ~5000 req/hour with 429s.
- Publish: 10 publishes per package per minute, 100 per user per hour.
- Search API: 1 req/sec per IP.
- Abuse → account suspension, not just throttling.

CI mitigation: enable the registry proxy in your cache (GitHub Actions
`setup-node` with `cache: 'pnpm'`, Vercel/Netlify build caches, or an in-org
Verdaccio proxy).

### GitHub Packages (npm.pkg.github.com)

- 5000 req/hour authenticated (shared with the general GitHub API quota per
  token).
- 60 req/hour unauthenticated (effectively unusable for CI).
- 429 responses include `X-RateLimit-Reset` — sleep until then.

### Node itself

No network rate limits. The limits that matter are resource limits:
- libuv thread pool: 4 threads default (`UV_THREADPOOL_SIZE`)
- File descriptors: `ulimit -n` (default 1024 on many distros, raise to 65535)
- V8 heap: see "Limits" section
- Max listeners per EventEmitter: 10 (warning, not error)

## Error Codes and Recovery

| Code | Meaning | Fix |
|---|---|---|
| `ERR_MODULE_NOT_FOUND` | ESM import missing `.js` extension OR file truly absent | Add extension; check `exports` field of the dep |
| `ERR_REQUIRE_ESM` | CJS `require()` of ESM module | Upgrade to Node 22.12+ for `require(esm)`, OR convert caller to ESM, OR use dynamic `import()` |
| `ERR_REQUIRE_ASYNC_MODULE` | `require(esm)` on a graph with top-level await | Remove TLA or import dynamically |
| `ERR_UNSUPPORTED_DIR_IMPORT` | ESM tried to import a directory | Specify the file (`./foo/index.js`) |
| `ERR_PACKAGE_PATH_NOT_EXPORTED` | Subpath not in `exports` field | Add to `exports` or import the entry point |
| `EADDRINUSE` | Port already bound | `ss -tlnp \| grep :3000`; kill old process; ensure graceful shutdown closed the listener |
| `EACCES` | Permission denied (often port <1024 for non-root, or file mode) | Use `>=1024`, `CAP_NET_BIND_SERVICE`, or reverse-proxy |
| `ECONNREFUSED` | Service not up / wrong host | Wait, retry with backoff, check DNS and firewall |
| `ECONNRESET` | Peer closed the socket mid-request | Usually the peer, not you — retry idempotent requests |
| `ENOTFOUND` | DNS failed | Check resolver; `dns.resolve*` vs `dns.lookup` |
| `EMFILE` / `ENFILE` | Too many open files | `ulimit -n 65535`; close streams; audit for leaks |
| `ENOSPC` on `fs.watch` | Inotify watcher limit | `sysctl fs.inotify.max_user_watches=524288` |
| `ERR_HTTP_HEADERS_SENT` | Called `res.writeHead`/`res.write` after response finalized | Return after `res.end()`; check for double-send in error paths |
| `ERR_STREAM_PREMATURE_CLOSE` | Pipeline aborted before finish | Check `AbortSignal` reason; inspect upstream error |
| `MaxListenersExceededWarning` | `emitter.on(...)` in hot loop without cleanup | Use `once`; call `off`/`removeListener`; or set limit explicitly |
| `UnhandledPromiseRejection` | Promise rejected with no `.catch` | Since Node 15 the process crashes — good. Fix the caller |

**Unhandled rejection handler (log + exit, never swallow):**

```js
process.on('uncaughtException', (err, origin) => {
  process.stderr.write(`FATAL ${origin}: ${err.stack}\n`);
  process.exit(1);
});
process.on('unhandledRejection', (reason) => {
  process.stderr.write(`UNHANDLED REJECTION: ${reason?.stack ?? reason}\n`);
  process.exit(1);
});
```

**`Error.cause` for chained errors:**

```js
try { await loadUser(id); }
catch (dbErr) {
  throw new Error(`failed to load user ${id}`, { cause: dbErr });
}
```

## SDK Idioms

### async/await over callbacks

```js
import { readFile } from 'node:fs/promises';
const content = await readFile('./config.json', 'utf8');
```

`fs/promises`, `dns/promises`, `stream/promises`, `timers/promises` — every
callback API has a promise twin. Use them exclusively. `util.promisify` wraps
legacy callback APIs on demand.

### AbortController everywhere

```js
const ac = new AbortController();
setTimeout(() => ac.abort(new Error('timeout')), 10_000);

const res = await fetch(url, { signal: ac.signal });
// or the shortcut:
const res2 = await fetch(url, { signal: AbortSignal.timeout(10_000) });
```

**Every outbound HTTP call has a timeout and a signal.** Always. No exceptions.
Chain signals when propagating from a caller:

```js
async function call(opts = {}) {
  const ac = new AbortController();
  opts.signal?.addEventListener('abort', () => ac.abort(opts.signal.reason),
    { once: true });
  const t = setTimeout(() => ac.abort(new Error('timeout')), 30_000);
  try { return await fetch(url, { signal: ac.signal }); }
  finally { clearTimeout(t); }
}
```

### Streams + pipeline

```js
import { pipeline } from 'node:stream/promises';
import { createReadStream, createWriteStream } from 'node:fs';
import { createGzip } from 'node:zlib';

await pipeline(
  createReadStream('archive.tar'),
  createGzip(),
  createWriteStream('archive.tar.gz'),
);
```

`.pipe()` is banned in production code — no error propagation, no cleanup on
failure.

### EventEmitter

```js
import { EventEmitter, once } from 'node:events';
const bus = new EventEmitter();
bus.on('ready', () => console.log('ready'));
// Promise-based wait for a single event
const [value] = await once(bus, 'ready');
```

Prefer `once(emitter, 'event')` over manual `on`/`off` dance when you want
exactly one occurrence.

### Buffer

```js
Buffer.alloc(1024);                  // zero-filled
Buffer.allocUnsafe(1024);             // fast, UNinitialized — audit before use
Buffer.from('hello', 'utf8');
Buffer.from([0x48, 0x69]);
buf.toString('hex');
```

Never use `new Buffer(n)` — deprecated since Node 6, deleted in some builds.

### Worker threads

```js
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';
if (isMainThread) {
  const w = new Worker(import.meta.filename, { workerData: { input: 'x' } });
  w.once('message', (r) => console.log(r));
} else {
  parentPort.postMessage(expensive(workerData.input));
}
```

Workers have their own V8 isolate, module graph, and event loop. Share memory
only via `SharedArrayBuffer` + `Atomics`. Spawn cost ~40ms — pool with
`piscina`.

### Native fetch (since 18, stable 21)

```js
const res = await fetch('https://api.example.com', {
  headers: { Authorization: `Bearer ${token}` },
  signal: AbortSignal.timeout(10_000),
});
if (!res.ok) throw new Error(`HTTP ${res.status}`);
const data = await res.json();
```

`Request`, `Response`, `Headers`, `FormData`, `Blob`, `File` are all global.
No `axios`, no `node-fetch`, no `got` for new code.

### Built-in test runner (since 20 stable)

```js
import { test, describe, it, mock } from 'node:test';
import assert from 'node:assert/strict';

describe('user service', () => {
  it('creates a user', async () => {
    const r = await createUser({ email: 'a@b.c' });
    assert.equal(r.email, 'a@b.c');
  });
  it('mocks a fn', () => {
    const fn = mock.fn(() => 42);
    assert.equal(fn(), 42);
    assert.equal(fn.mock.callCount(), 1);
  });
});
```

Run: `node --test`, `node --test --watch`, `node --test --experimental-test-coverage`.

## Anti-Patterns

1. **`require()` in new code.** Use ESM imports. Use `createRequire` only
   when forced by a CJS-only dep inside an ESM module.
2. **`fs.readFileSync` in a request handler.** Blocks the entire event loop
   for every concurrent request. Move to async. Use `--trace-sync-io` to hunt.
3. **`Promise.all` over thousands of items.** Opens N concurrent operations,
   exhausts sockets/FDs. Use `p-limit`:
   ```js
   import pLimit from 'p-limit';
   const limit = pLimit(10);
   await Promise.all(items.map(i => limit(() => process(i))));
   ```
4. **Catching `uncaughtException` to "keep the server running."** The process
   is in undefined state — leaked FDs, half-written transactions. Crash and
   let systemd/Docker/K8s restart.
5. **Swallowing errors in callbacks.** `.catch(() => {})`, empty `try/catch`.
   Log + handle, or rethrow with `Error.cause`.
6. **`console.log` in hot paths.** Synchronous to a TTY, slow to a pipe. Use
   pino with sampling.
7. **`npm i -g`.** Sudo, conflicts, breaks under version managers. Use a
   devDependency or `npx` / `pnpm dlx`, or Volta for true global tools.
8. **`axios` / `node-fetch` in new code.** Built-in `fetch` is faster,
   smaller, zero-dep.
9. **`.pipe()` chains.** No error propagation. Use `pipeline()`.
10. **`dotenv` package.** Use `--env-file` since Node 20.6. One less dep.
11. **Hardcoded secrets/ports.** Env vars validated with `zod` at startup.
12. **`new Buffer(n)`.** Deprecated. `Buffer.alloc(n)` / `Buffer.from(...)`.
13. **`process.exit(0)` immediately after writes.** Truncates piped stdout.
    Set `process.exitCode = 0` and let the loop drain.
14. **Distro-installed Node.** Always stale. fnm / Volta / NodeSource.
15. **`npm install` in CI.** Mutates the lockfile, breaks reproducibility.
    Always `npm ci` or `pnpm install --frozen-lockfile`.
16. **`cluster` for modern deploys.** Legacy. Run N processes behind
    nginx/Caddy/ALB.
17. **Catching all errors in an Express middleware and returning 500.**
    Express 5 is finally async-aware — let the framework route errors to
    your error handler instead.
18. **`setInterval` without `.unref()` for background work.** Keeps the
    process alive after the main work finishes.
19. **Attaching listeners inside a request handler without cleanup.** Slow
    memory leak, eventually `MaxListenersExceededWarning`.

## Data Model

### Module resolution

- **CJS:** `require('pkg')` walks `node_modules/` from caller upward. No file
  extension needed. Packages export via `module.exports`. Loads synchronously,
  caches by resolved path.
- **ESM:** `import from 'pkg'` consults the `exports` field of `pkg`'s
  `package.json`. Relative/absolute imports REQUIRE a file extension. Loads
  asynchronously (though the default loader makes it feel sync). Caches by
  URL.
- **`exports` conditions** (in priority order as declared): `node`, `import`,
  `require`, `browser`, `default`. `types` must be first (for bundlers),
  `default` must be last (catch-all).

### Packages and lockfiles

- **`package.json`** — source of truth for dependencies, scripts, engines,
  metadata.
- **`package-lock.json`** (npm) — exact resolved tree, integrity hashes.
  Committed. `npm ci` enforces.
- **`pnpm-lock.yaml`** (pnpm) — exact resolved tree + peer dependency
  resolution graph. Committed. `--frozen-lockfile` enforces.
- **`yarn.lock`** (yarn classic / berry) — exact resolved tree.

### node_modules layouts

- **npm 3+ flat** — packages hoisted to the top level. One copy when possible,
  nested when version conflicts. Lots of duplicates across versions.
- **pnpm symlink store** — every version of every package stored once in
  `~/.local/share/pnpm/store`, hardlinked into `node_modules/.pnpm/`, then
  symlinked into the project's `node_modules/`. Strict: a package cannot
  `require` something it did not declare.
- **yarn PnP** — no `node_modules` at all. A single `.pnp.cjs` file maps every
  import. Fastest, but breaks tools that `fs.stat` the tree.

### Monorepo workspaces

pnpm and npm both support workspaces. pnpm is dramatically better for large
monorepos because of the content-addressable store.

```yaml
# pnpm-workspace.yaml
packages:
  - 'apps/*'
  - 'packages/*'
```

```json
// package.json (npm workspaces)
{ "workspaces": ["apps/*", "packages/*"] }
```

## Webhooks and Events

Node has no external webhook concept — it is a runtime, not a service. The
in-process equivalent is `EventEmitter`, and it is pervasive:

```js
import { EventEmitter, once } from 'node:events';

class Job extends EventEmitter {}
const job = new Job();

job.on('progress', (pct) => log.info({ pct }, 'progress'));
job.once('done', () => log.info('done'));
job.on('error', (err) => log.error({ err }, 'failed'));

// Promise interop
const [result] = await once(job, 'done');
```

Every major Node API is an EventEmitter underneath: `http.Server`, streams,
`process`, `child_process`, `Worker`. Understand the contract:
- `error` events with no listener **throw**
- Listener limit default 10 — exceed it and you get a warning (often the
  first sign of a leak)
- `once(emitter, 'event', { signal })` — abortable one-shot wait

For actual HTTP webhook *handling* (Stripe, GitHub, Discord), use Hono or
Fastify with a raw-body parser and verify the signature BEFORE parsing JSON.

## Limits

### V8 heap

- **Default old-space limit:** ~1.7 GB on 64-bit, raised to ~4 GB on machines
  with ≥16 GB RAM in recent Node versions.
- **Override:**
  ```bash
  node --max-old-space-size=4096 app.js      # MB, old generation only
  node --max-semi-space-size=128 app.js      # MB, young generation
  ```
- **Container rule of thumb:** set `--max-old-space-size` to ~75% of the
  container memory limit. A 4 GB container → `--max-old-space-size=3072`.
  The flag does NOT bound native buffers, V8 code space, stack, or worker
  isolates — OOMs at 1.5x the flag are normal.

### libuv thread pool

- Default: **4 threads** shared by `fs`, `dns.lookup`, `crypto`, `zlib`.
- Override: `UV_THREADPOOL_SIZE=64` in env (must be set before the first libuv
  call — i.e., at process start).
- Max: 1024.
- Use `dns.resolve*` to bypass the pool entirely for DNS.

### File descriptors

- Linux default `ulimit -n` is often 1024. For any real service, raise it:
  ```ini
  # /etc/systemd/system/eos-api.service
  [Service]
  LimitNOFILE=65535
  ```
- Inotify watchers (for `fs.watch`) have their own kernel limit:
  `sysctl fs.inotify.max_user_watches=524288`.

### EventEmitter listeners

- Default warning at 10 listeners per event per emitter. `emitter.setMaxListeners(n)`
  to override — do this only after confirming the increase is intentional.
- `events.defaultMaxListeners` sets the process-wide default.

### HTTP

- `maxHeaderSize` default 16 KB. Override: `node --max-http-header-size=32768`.
- `http.globalAgent.maxSockets` default `Infinity` — usually fine, but cap
  it if you're hammering a single upstream.

## Cost Model

Node itself is free and open source. Cost dimensions that show up in practice:

- **Hosting** — Vercel/Netlify/Cloudflare charge per request and per GB-s of
  compute. A typical Node service runs for pennies at low scale, then cliffs
  at high scale where a long-lived VM is cheaper.
- **npm enterprise / GitHub Packages** — free for public, ~$7/user/month for
  private (GitHub Team+). Cloudsmith, JFrog, Sonatype are alternatives.
- **Observability SaaS** — Datadog, New Relic, Honeycomb all charge per host
  or per ingest volume. OpenTelemetry + self-hosted Tempo/Loki is the escape
  hatch.
- **Cold start cost** — on Lambda / Cloud Run, Node starts in 100-300ms for a
  zero-dep service, 800ms-2s for a dep-heavy one. Dependencies are the
  variable — prune them.

For EOS: the SaaS layer runs on a single VPS under systemd. Cost is ~$0
incremental per deploy. The cost to optimize is human time spent on
dependency bloat, not compute.

## Version Pinning

### LTS schedule

- Even-numbered releases become LTS in October of their release year.
- LTS cycle: **Current** (6 months) → **Active LTS** (12 months) → **Maintenance LTS** (18 months).
- Node 18: EOL April 2025 — do not deploy new code on it.
- Node 20: Maintenance LTS.
- **Node 22 ("Jod"): Active LTS through Oct 2025, Maintenance until April 2027.** Default for new services.
- Node 24: Current, will enter LTS October 2025.

### Pinning mechanisms

**`.nvmrc`** — single line, read by nvm, fnm, Volta, asdf:
```
22.11.0
```
or `lts/jod`.

**`package.json` engines** — advisory by default, enforced by pnpm and by npm
with `engine-strict=true` in `.npmrc`:
```json
{ "engines": { "node": ">=22.11.0 <23", "pnpm": ">=9" } }
```

**Corepack + `packageManager`** — pins the package manager version with an
integrity hash:
```bash
corepack enable
corepack use pnpm@9.12.0
```
Writes:
```json
{ "packageManager": "pnpm@9.12.0+sha512...." }
```
Corepack auto-downloads the exact version on any machine with Node installed.
Ships with Node 16+.

**Volta** — pins node + pm in `package.json`, auto-switches on `cd`:
```json
{ "volta": { "node": "22.11.0", "pnpm": "9.12.0" } }
```

### Node version differences that bite

| Feature | Added | Stable |
|---|---|---|
| Global `fetch` | 18.0 | 21 |
| `node --test` | 18 | 20 |
| `--watch` | 18.11 | 20 |
| `--env-file` | 20.6 | 22 |
| `--experimental-strip-types` | 22.6 | 24 (default) |
| `node:sqlite` | 22 | 23 |
| `require(esm)` | 22.0 (flag) | 22.12 (default) |
| Global `WebSocket` | 22 | 22 |
| `import.meta.dirname` | 20.11 | 20.11 |
| `Error.isError` | 22 | 22 |

Code targeting 22 LTS can assume all of the above EXCEPT `--experimental-strip-types`
default-on (that's 24).

---

# Tier 2 — Creator-Level Intelligence

## Design Intent and Tradeoffs

Ryan Dahl built Node.js in 2009 because Apache's thread-per-connection model
collapsed under C10K and because every existing async I/O library forced
callbacks awkwardly onto languages that wanted threads. JavaScript was the
only mainstream language where every function was already a closure and
where nobody had any preconceptions about blocking I/O — there was no
`fs.readFileSync` muscle memory to fight. V8 was the second half of the bet:
Google had just shipped a JIT'd, isolated, embeddable JS engine with
predictable GC. Dahl welded V8 to libuv (his cross-platform async I/O
abstraction) and shipped a runtime whose entire personality is "one thread,
one event loop, never block it."

Everything that is weird about Node descends from that bet:

- **CPU-bound work is awkward.** Worker threads only landed in Node 10.5
  (2018) and did not stabilize until 12. Before that, the answer was "spawn
  a child process or write a C++ addon." Node is an I/O machine. If your
  workload is matrix multiplication or model inference, you picked the wrong
  runtime.
- **No default TypeScript** until 22.6 (strip-only) and 23 (transform). For
  13 years the community ran ts-node, tsx, swc, esbuild, and tsc in five
  different configurations.
- **The CommonJS → ESM transition** has been the longest, most painful
  migration in modern JS. Node 12 added ESM behind a flag, Node 14 unflagged
  it, and we are still living with dual-publish hell in 2026.
- **`node_modules`** — flat in npm 3+, content-addressed in pnpm,
  hoisted-but-isolated in yarn — is still the largest object in the universe
  by file count.

In 2018 Dahl gave "10 Things I Regret About Node.js" at JSConf EU: no
Promises in core (he removed them in 0.2), the security model, the build
system (gyp), centralized npm, `node_modules` itself, `require()` without
extension, `index.js` magic, and the lack of a standard library. **Deno**
was his answer — secure-by-default, URL imports, native TS, web-standard
APIs. **Bun** is Jarred Sumner's answer — same web standards but obsessed
with raw speed via JavaScriptCore + Zig.

Node's response from 2022 onward has been to absorb the criticism: web
`fetch`, web Streams, web Crypto, `--env-file`, `--watch`, `--test`,
`--experimental-strip-types`, `--experimental-permission`, `node:sqlite`.
The pattern is unmistakable — **Node is becoming Deno from the inside**,
but without breaking 14 years of compatibility. That compatibility is the
moat. Bun and Deno are faster and cleaner; Node runs every package ever
written.

Governance is the OpenJS Foundation. The Technical Steering Committee
includes Matteo Collina (Fastify), James Snell (web standards), Anna
Henningsen (workers/internals), Michael Dawson (IBM), and Joyee Cheung
(startup snapshots). The TSC moves slow on purpose. That is a feature.

**What Node is NOT:** "JavaScript everywhere at scale without thinking." It
is an I/O orchestration runtime that happens to use JS. Treat it as such and
you win. Treat it as a general-purpose language runtime and you will write a
CPU-bound API server that falls over at 200 RPS.

## Problem-Solution Map and Hidden Capabilities

The single biggest thing most Node devs do not know is **how much of their
`package.json` is now obsolete**. Modern Node ships almost the entire
"standard kit." In 2026, a competent greenfield service has zero or
near-zero runtime dependencies.

| What devs install | What Node ships built-in | Since |
|---|---|---|
| `axios`, `node-fetch` | global `fetch` (undici) | 18 |
| `jest`, `mocha`, `vitest` | `node --test` + `node:test` + `node:assert` | 18, stable 20 |
| `dotenv` | `node --env-file=.env` | 20.6 |
| `nodemon` | `node --watch` | 18.11, stable 20 |
| `ts-node`, `tsx` (for stripping) | `node --experimental-strip-types` (default in 23) | 22.6 |
| `better-sqlite3` (simple cases) | `node:sqlite` | 22 (experimental) |
| `uuid` | `crypto.randomUUID()` | 14.17 |
| `lodash.clonedeep` | `structuredClone()` | 17 |
| `chalk` (some uses) | `util.styleText()` | 20.12 |
| `pkg`, `nexe` | Single Executable Applications (SEA) | 19.7, stable 20 |
| `async_hooks` userland | `AsyncLocalStorage` | 13.10 stable |
| `ws` for WebSocket client | global `WebSocket` | 22 |

Other hidden capabilities most devs never touch:

- **`node --inspect=0.0.0.0:9229`** — full Chrome DevTools on a running
  production process. CPU profiles, heap snapshots, source-mapped
  breakpoints. Combine with `kill -SIGUSR1 <pid>` to enable on a live process
  without restart.
- **`process.report.writeReport()`** — dumps a JSON crash diagnostic with V8
  heap stats, native stack, libuv handles, env. Enable via
  `--report-on-fatalerror --report-on-signal`. Free post-mortem.
- **`--experimental-permission`** — Deno-style sandbox. Great for CI scripts
  against untrusted input.
- **`perf_hooks`** — `performance.mark()` / `performance.measure()` +
  `PerformanceObserver`. Same User Timing API the browser exposes. Pipe to
  OpenTelemetry.
- **`AsyncLocalStorage`** — request-scoped context without passing `req`
  everywhere. The replacement for the deprecated `domain` module. Critical
  for tracing and structured logging in middleware-heavy stacks.
- **`queueMicrotask(fn)`** — schedules in the same microtask queue as
  resolved Promises, runs *before* the next macrotask. Use when you need
  "after this stack but before any I/O."
- **Web Streams** (`ReadableStream`, `TransformStream`) — interop with Node
  streams via `Readable.toWeb()` / `.fromWeb()`. The whole edge ecosystem
  speaks Web Streams.
- **`structuredClone(obj)`** — deep clone with cycles, Maps, Sets, Dates,
  typed arrays. The thing you wanted `JSON.parse(JSON.stringify(x))` to be.
- **`util.parseArgs()`** (18.3+) — built-in CLI arg parser. No more
  `commander` / `yargs` for simple CLIs.
- **`node:test` mocking** — `mock.fn()`, `mock.method()`,
  `mock.timers.enable()`. Throw out Sinon.

## Operational Behavior and Edge Cases

These are the things that bite production Node teams. Internalize them and
you skip a year of incidents.

- **`server.keepAliveTimeout` < load balancer idle timeout.** The single
  most common Node-behind-ALB bug. ALB holds the socket open for 60s. If
  Node closes at 5s, the LB tries to reuse a half-closed socket and the next
  request 502s. Fix: `server.keepAliveTimeout = 65_000` and
  `server.headersTimeout = 66_000` (must be greater).
- **`fs.readFile` blocks the event loop on cold cache.** It is "async" via
  the libuv thread pool, but the file open + first read can saturate the
  pool. For latency-sensitive paths, stream large files; never sync-read in
  a request handler.
- **DNS lookup is synchronous-ish via `dns.lookup`.** It uses
  `getaddrinfo(3)` on the libuv thread pool (4 threads default). Symptom:
  random tail latency spikes correlated with DNS. Fix:
  `UV_THREADPOOL_SIZE=64` or use `dns.resolve*`.
- **`MaxListenersExceededWarning (10)` looks harmless. It is not.** It
  almost always means you are attaching a listener inside a request handler
  without removing it — a slow leak.
- **`process.exit()` does NOT flush stdout/stderr on pipes.** You may lose
  log lines under systemd-journal or `tee`. Fix: let the loop drain, or
  `process.stdout.write("done\n", () => process.exit(0))`.
- **ESM is strict.** `import './foo'` does NOT work — must be
  `import './foo.js'`. No directory imports. No `index.js` magic. The single
  biggest source of "it works in CJS but breaks in ESM."
- **Top-level await blocks the module graph.** A `await fetch(...)` at the
  top of a module pauses every importer. One slow module → cascade.
- **`AbortSignal` is not automatic.** `fetch(url, { signal })` works, but
  you must thread the signal through every layer yourself. Forget once and
  you have a hung request and a leaked socket.
- **Worker threads have their own event loop, V8 isolate, and module
  graph.** They share memory only via `SharedArrayBuffer` + `Atomics`.
  Spawning a worker is ~40ms. Use a pool (`piscina`).
- **V8 heap snapshots are huge.** A 1 GB heap → ~2 GB snapshot file. Do
  not `writeHeapSnapshot()` in prod without a circuit breaker.
- **`--max-old-space-size=4096` does not bound everything.** Native
  buffers, V8 code space, stack, and worker isolates are all separate.
  Container OOMs at 1.5x the flag are normal.
- **`Date.parse("2026-04-06")` is implementation-defined** for non-ISO
  strings. Always pass full ISO 8601 with timezone. Or accept Unix epoch
  ints at API boundaries.
- **`unhandledRejection` crashes in Node 15+.** This is correct behavior.
  Wrap top-level async with `.catch(logAndExit)`.
- **`require('crypto').randomBytes(n)` uses the thread pool.** Big `n`
  saturates it. Use `randomFillSync` for small synchronous needs.
- **Signal handling under Docker.** If Node is PID 1 with no init, SIGTERM
  is *ignored by default*. Docker waits 10s then SIGKILLs. Fix:
  `docker run --init` AND register a SIGTERM handler.
- **`fs.watch` on Linux uses inotify.** Default kernel watch limit is
  ~8k — easily blown by a Vite dev server on a monorepo. Raise with
  `sysctl fs.inotify.max_user_watches=524288`.

## Ecosystem Position and Composition

**Node vs Deno vs Bun in 2026:**

- **Node** — ubiquity, every package, every cloud provider, every framework.
  LTS schedule rock solid (even releases get 30 months). Slow but moving.
  The boring correct choice for production.
- **Bun** — 3-5x faster cold start, faster HTTP, faster file I/O, built-in
  bundler/test/install. Native TS. Drop-in for many Node APIs but not all
  (gaps in `node:cluster`, some streams, some VM internals). Use for:
  greenfield APIs where speed matters and you control the deploy. Avoid
  for: anything with a C++ addon you did not compile yourself.
- **Deno** — cleanest design, secure by default, native TS, URL imports,
  built-in tooling. Deno 2 added npm compatibility. Use for: scripts, edge
  functions, trusted internal tools.

Honest 2026 answer: **Node for production services, Bun for scripts and
dev tooling, Deno for sandboxed/edge.** All three converge on Web Standard
APIs, so code that uses only those is portable.

**The modern Node stack (2026):**

- **HTTP framework:** Hono > Fastify > Express. Hono is web-standard
  (`Request`/`Response`), runs on Node + Bun + Deno + Cloudflare + Lambda
  unchanged, faster than Express, simpler. Fastify is right if you need
  plugins, schemas, and Matteo Collina's ecosystem. Express 5 is
  maintenance-mode.
- **DB layer:** Drizzle > Kysely > Prisma. Drizzle is type-safe SQL with
  zero runtime overhead. Kysely is a query builder. Prisma is heavier
  (separate engine binary, higher cold start) but schema/migration
  ergonomics still best-in-class.
- **TS pipeline:** `tsx` for dev, `tsc --noEmit` for type checking,
  `tsup`/`unbuild` for libraries, `esbuild`/`swc` for apps. ts-node is
  deprecated.
- **Process supervision:** **systemd**, not PM2. PM2 was useful in 2014.
  systemd is on every Linux box, gives you journald for free, handles
  restarts, dependencies, sockets.
- **Containers:** multi-stage Dockerfile, `node:22-alpine` or distroless
  base, non-root user, `--init` flag. Never run `npm start` as PID 1.
- **K8s:** liveness probe = "is the event loop responsive" (cheap HTTP),
  readiness probe = "are deps ready" (DB connect). Always handle SIGTERM
  with a drain.
- **Observability:** OpenTelemetry SDK with auto-instrumentation. Do not
  roll your own.

**Where Node is wrong:** ML inference at scale, long-running stateful
simulations, real-time control, high-throughput stream processing.

**Where Node is perfect:** API gateways, BFF layers, WebSocket fan-out,
glue services, **AI agent orchestration**, edge functions, build tools.

## Trajectory and Evolution

| Version | Year | Key additions |
|---|---|---|
| 18 LTS | 2022 | Global `fetch`, Web Streams, `node:test` experimental, `--watch` |
| 20 LTS | 2023 | `node:test` stable, SEA stable, `--experimental-permission` |
| 22 LTS | 2024 | `node:sqlite`, global `WebSocket`, `--watch` stable, `--experimental-strip-types`, glob in `fs`, stable `require(esm)` (22.12) |
| 23 | 2024 | TS strip enabled by default, more `require(esm)` coverage, stable `node:sqlite` path |
| 24 LTS | 2025 | Native TS transform (not just strip), AsyncLocalStorage perf rewrite, broader permission model |

The **direction is unmistakable**: absorb the standard kit. Test runner,
fetch, env, watch, TS, SQLite, WebSocket — every release closes one more
reason to install a dep. Five years out, a typical Node service will have
0-2 runtime deps and 2-5 dev deps.

**Active pressure shaping the roadmap:**

- **Bun + Deno** — Node moves faster now than at any time since 2015
  because Bun's benchmarks are embarrassing. Permission model, native TS,
  built-in test, undici fetch, `node:sqlite` — all accelerated by
  competitive pressure.
- **Corepack + pnpm** — npm is slow and wasteful. Corepack ships with Node
  and pins the package manager per project. pnpm's content-addressed store
  is the right design.
- **ESM fully wins.** CJS is in maintenance. New libraries should publish
  ESM-only. Node 22's `require(esm)` removes the last excuse.
- **WASI / WebAssembly** — Node has had WASI support since 12. Story
  matures slowly. The bet: heavy compute → Rust → WASM → call from Node.
- **Startup snapshots** — Joyee Cheung's work on user-land V8 snapshots
  makes cold start 2-5x faster. Critical for serverless.

**Bet for 2026-2028:** native TS by default, `require(esm)` the norm,
permission model stable, OpenTelemetry the only observability story, Hono
or Fastify as the HTTP layer, Drizzle as the DB layer, systemd for process
supervision.

## Conceptual Model and Solution Recipes

### Mental model

> A Node app is a single JavaScript thread with an event loop. The loop
> dispatches I/O callbacks. If you block the loop, the app dies. Everything
> interesting is async. Everything synchronous is a bug waiting to happen.

Primitives: event loop, Promises (microtasks), `setImmediate`/`setTimeout`
(macrotasks), Streams (Node + Web), Buffer, `process` (signals, env,
stdio), modules (ESM, CJS), `worker_threads`, `child_process`, `cluster`.

### Recipe: long-running Express service with graceful shutdown

```js
import express from 'express';
import pino from 'pino';
import { db } from './db.js';

const log = pino({ level: process.env.LOG_LEVEL ?? 'info' });
const app = express();

app.get('/healthz', (_, res) => res.status(200).send('ok'));
app.get('/readyz',  async (_, res) => {
  try { await db.query('select 1'); res.status(200).send('ok'); }
  catch { res.status(503).send('not ready'); }
});

const server = app.listen(process.env.PORT ?? 3000, () => log.info('up'));
server.keepAliveTimeout = 65_000;
server.headersTimeout   = 66_000;

const sockets = new Set();
server.on('connection', (s) => {
  sockets.add(s);
  s.on('close', () => sockets.delete(s));
});

let shuttingDown = false;
async function shutdown(signal) {
  if (shuttingDown) return;
  shuttingDown = true;
  log.info({ signal }, 'draining');
  server.close(() => log.info('server closed'));
  setTimeout(() => sockets.forEach((s) => s.destroy()), 10_000).unref();
  await db.end();
  process.exit(0);
}
process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT',  () => shutdown('SIGINT'));
process.on('uncaughtException', (err) => { log.fatal({ err }, 'uncaught'); process.exit(1); });
process.on('unhandledRejection', (err) => { log.fatal({ err }, 'unhandled'); process.exit(1); });
```

### Recipe: worker pool for CPU work

```js
import { Worker } from 'node:worker_threads';
import os from 'node:os';

class Pool {
  constructor(script, size = os.cpus().length) {
    this.workers = Array.from({ length: size }, () => new Worker(script));
    this.queue = [];
    this.idle = [...this.workers];
  }
  run(data) {
    return new Promise((resolve, reject) => {
      const task = { data, resolve, reject };
      if (this.idle.length) this.dispatch(this.idle.pop(), task);
      else this.queue.push(task);
    });
  }
  dispatch(worker, task) {
    worker.once('message', (r) => {
      task.resolve(r);
      if (this.queue.length) this.dispatch(worker, this.queue.shift());
      else this.idle.push(worker);
    });
    worker.once('error', task.reject);
    worker.postMessage(task.data);
  }
}
```

For anything beyond a toy: use `piscina`.

### Recipe: AbortController with chained signal and timeout

```ts
async function callLLM(prompt: string, opts: { timeoutMs?: number, signal?: AbortSignal } = {}) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(new Error('timeout')), opts.timeoutMs ?? 30_000);
  opts.signal?.addEventListener('abort', () => ctrl.abort(opts.signal!.reason), { once: true });

  try {
    const r = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      signal: ctrl.signal,
      headers: {
        'content-type': 'application/json',
        'x-api-key': process.env.ANTHROPIC_API_KEY!,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: 'claude-opus-4-6',
        max_tokens: 1024,
        messages: [{ role: 'user', content: prompt }],
      }),
    });
    if (!r.ok) throw new Error(`LLM ${r.status}: ${await r.text()}`);
    return await r.json();
  } finally {
    clearTimeout(t);
  }
}
```

**This is the canonical pattern for every outbound HTTP call from Node in
2026.** Always pass a signal. Always set a timeout. Always chain the
caller's signal.

### Recipe: streaming a large file with pipeline

```js
import { pipeline } from 'node:stream/promises';
import { createReadStream, createWriteStream } from 'node:fs';
import { createGzip } from 'node:zlib';

const ac = new AbortController();
setTimeout(() => ac.abort(), 60_000);

await pipeline(
  createReadStream('/var/log/big.log'),
  createGzip(),
  createWriteStream('/var/log/big.log.gz'),
  { signal: ac.signal },
);
```

### Recipe: request context with AsyncLocalStorage

```js
import { AsyncLocalStorage } from 'node:async_hooks';
export const ctx = new AsyncLocalStorage();

app.use((req, _res, next) => {
  ctx.run({ requestId: crypto.randomUUID(), userId: req.user?.id }, next);
});

// anywhere downstream
import { ctx } from './ctx.js';
log.info({ ...ctx.getStore() }, 'did a thing');
```

This is the replacement for the deprecated `domain` module and is the
foundation of every serious tracing setup.

## Industry Expert and Cutting-Edge Usage

**Voices to track:**

- **Matteo Collina** (Fastify creator, Node TSC, undici co-author) — his
  blog at nodeland.dev and his conference talks are the single best source
  on what is coming and why. He drove undici, v22 perf work, and the "Node
  should ship a stdlib" thinking.
- **James Snell** — web standards in Node (fetch, Streams, WebCrypto). The
  reason Node code is portable to Cloudflare Workers.
- **Anna Henningsen** — workers, internals, ESM. The deepest Node internals
  expert in public.
- **Joyee Cheung** — V8 startup snapshots, the work making serverless cold
  starts viable.
- **Jarred Sumner (Bun)** and **Ryan Dahl (Deno)** — read what they are
  shipping. It is where Node will be in two years.

**The "Node or Bun?" decision framework (2026):**

1. On AWS Lambda / GCP Cloud Run / a managed PaaS? **Node.**
2. Depend on a native addon (`better-sqlite3`, `sharp`)? **Node.**
3. CLI tool, build script, or dev server? **Bun.**
4. Greenfield, owning your deploy, latency-sensitive, no native deps?
   **Either**, lean Bun if perf matters.
5. Code going to Cloudflare Worker / Vercel Edge? **Hono + Web Standard
   APIs**, runtime is fungible.

**AI agent orchestration in Node (relevant to EOS):**

The **Vercel AI SDK** is the de facto standard. It handles streaming, tool
calls, structured outputs, and provider abstraction across Anthropic,
OpenAI, Google, Mistral, local models. **Mastra** is the new "agent
framework" built on top — typed workflows, durable state, evals.
LangChain.js exists but is heavier and more Python-flavored than it should
be for a Node-first agent system.

**Production profiling toolkit:**

- **`clinic.js`** — `npx clinic doctor -- node app.js` diagnoses what is
  wrong, `clinic flame` for flamegraph, `clinic bubbleprof` for async ops.
- **`0x`** — `npx 0x -- node app.js` generates interactive flamegraph HTML.
- **`node --prof`** + `--prof-process` for V8 tick profiles.
- **`monitorEventLoopDelay`** from `perf_hooks` for continuous event loop
  lag metrics. Essential for alerting:
  ```js
  import { monitorEventLoopDelay } from 'node:perf_hooks';
  const h = monitorEventLoopDelay({ resolution: 20 });
  h.enable();
  setInterval(() => log.info({ p99_ms: h.percentile(99) / 1e6 }, 'loop lag'), 5000);
  ```

**Production tuning knobs that actually matter:**

- `UV_THREADPOOL_SIZE=64` (or higher for DNS/crypto-heavy workloads)
- `--max-old-space-size` set to ~75% of container memory limit
- `--max-semi-space-size=64` for high-allocation services (reduces GC
  pauses)
- `--optimize-for-size` for serverless (smaller heap, slower throughput)
- `NODE_ENV=production` — Express, React SSR, and many libs branch on this
- `node --enable-source-maps` so production stack traces are useful

**Production patterns from scale shops:** Netflix runs Node for the API
tier (BFF). LinkedIn moved their mobile backend from Rails to Node and
dropped server count 10x. Uber runs Node for marketplace orchestration.
PayPal has been a Node shop for a decade. The pattern is identical:
**Node sits where I/O orchestration happens.** It is the connective tissue.
CPU work is in Java, Go, C++, Python — and Node calls them.

**The "minimal dependencies" movement** is the most important cultural
shift in Node since async/await. Hono has zero dependencies. Drizzle is
small. Pino is lean. The Vercel AI SDK is purposefully thin. Every modern
serious library now treats `npm install` count as a code smell.

## EOS Usage Patterns

EOS is a two-language system: Python for the intelligence layer
(`eos_ai/`), TypeScript on Node for everything user-facing (`saas/`).

**Canonical SaaS stack:**

- **Frontend:** React 18 + Vite + Tailwind + shadcn/ui, tested with vitest,
  typed with TypeScript 5.6+. Built with `pnpm build`.
- **API:** Hono on Node 22 LTS, served by `@hono/node-server`, fronted by
  Caddy/nginx on the VPS.
- **DB:** Neon Postgres via Drizzle ORM. Migrations run with
  `drizzle-kit push` in deploy scripts.
- **Auth:** BetterAuth or lucia — session cookies, not JWTs.
- **Logging:** pino to stdout, collected by systemd journald.
- **AI calls:** Vercel AI SDK wrapping Anthropic, Gemini, Ollama providers.
  Every call has `AbortSignal.timeout(30_000)` at minimum.

**Package manager:** pnpm everywhere. `packageManager` field pinned via
Corepack. `.nvmrc` pins Node 22.11.0. CI uses `pnpm install --frozen-lockfile`.

**Dev loop:**
```bash
pnpm dev          # tsx watch + vite dev server
pnpm typecheck    # tsc --noEmit
pnpm test         # vitest run
pnpm build        # tsc + vite build
```

**Prod deploy (VPS under systemd):**
```ini
[Service]
Type=simple
User=eos
WorkingDirectory=/opt/OS/saas/api
ExecStart=/usr/bin/node --enable-source-maps --env-file=/opt/OS/saas/api/.env dist/index.js
Restart=always
RestartSec=2
KillSignal=SIGTERM
TimeoutStopSec=15
LimitNOFILE=65535
Environment=NODE_ENV=production
```

**When to choose Node in EOS:** user-facing SaaS, BFF endpoints, webhook
receivers, streaming LLM responses, the Vercel AI SDK path, React/Vite
tooling.

**When to stay in Python:** `eos_ai/` primitives, agent runtime, Neon
admin, ML inference, anything touching the cognitive loop.

**Vitest over node:test in EOS** — vitest because it plays better with
Vite-config sharing, TS-first, snapshot tests for React components. Pure
backend services can use `node:test` directly. Either way, never add Jest
to a new EOS package.

**The AI agent call pattern** (used in every EOS SaaS integration with an
LLM provider):

```ts
import { generateText } from 'ai';
import { anthropic } from '@ai-sdk/anthropic';

export async function callAgent(prompt: string, signal?: AbortSignal) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(new Error('timeout')), 30_000);
  signal?.addEventListener('abort', () => ctrl.abort(signal.reason), { once: true });
  try {
    const { text } = await generateText({
      model: anthropic('claude-opus-4-6'),
      prompt,
      abortSignal: ctrl.signal,
    });
    return text;
  } finally {
    clearTimeout(t);
  }
}
```

Timeouts and signal chaining are non-negotiable.

## Gotchas

- **`keepAliveTimeout < LB idle timeout` → sporadic 502s** behind AWS ALB
  or Caddy. Set to 65s and `headersTimeout` to 66s.
- **ESM imports without file extension** → `ERR_MODULE_NOT_FOUND`. Even
  from TypeScript source where the file is `.ts`.
- **`unhandledRejection` crashes since Node 15.** Correct behavior. Log
  then exit.
- **libuv thread pool default 4** — `fs`, `dns.lookup`, `crypto`, `zlib`
  share it. `UV_THREADPOOL_SIZE=64` for heavy workloads.
- **`fs.readFileSync` in request handlers** blocks the loop for every
  concurrent request. `--trace-sync-io`.
- **`.pipe()` swallows errors.** Use `pipeline()`.
- **`Promise.all` over thousands of items** exhausts sockets. `p-limit`.
- **`process.exit(0)` does not flush piped stdout.** Let the loop drain.
- **Distro Node is always 2-4 majors stale.** fnm / Volta / NodeSource.
- **`require(esm)` needs a fully synchronous graph.** Any top-level await
  → `ERR_REQUIRE_ASYNC_MODULE`.
- **`--max-old-space-size` does not bound native buffers, code space, or
  worker isolates.** Container OOMs at 1.5x the flag are normal. Set to
  75% of cgroup.
- **No `__dirname` in ESM.** `import.meta.dirname` (20.11+) or
  `fileURLToPath(import.meta.url)`.
- **JSON imports need an attribute:** `import pkg from './p.json' with { type: 'json' }`.
- **Container hangs 30s on SIGTERM then SIGKILL** — Node is PID 1 with no
  init. `docker run --init` + SIGTERM handler.
- **Recursive `process.nextTick`** starves I/O forever. Use
  `setImmediate`.
- **`exports` field ordering:** `types` first, `default` last.
- **`npm install` in CI** mutates the lockfile. Always `npm ci` /
  `--frozen-lockfile`.
- **Global `npm i -g`** pollutes the system and breaks under version
  managers. Use devDependency + `npx` / `pnpm dlx`.
- **`AbortSignal` is not automatic.** Every layer of your code must thread
  it explicitly. Forget once → hung request + leaked socket.
- **`setInterval` without `.unref()`** keeps the process alive after the
  main work finishes.
- **`fs.watch` on Linux blows through the inotify limit** with big
  monorepos. `sysctl fs.inotify.max_user_watches=524288`.
- **`Date.parse` on non-ISO strings is implementation-defined.** Accept
  ISO 8601 with timezone, or Unix epoch ints.
- **Workers are expensive to spawn (~40ms)** — pool with `piscina`, do
  not create per-request.
- **`MaxListenersExceededWarning`** almost always means a listener leak
  inside a hot path. Treat it as an error, not a warning.

---

End of Node.js creator-level best practices.
