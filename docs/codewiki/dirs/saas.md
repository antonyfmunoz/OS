---
type: codewiki-dir
dir: saas
---

# `saas/` — DELETED code (orphaned artifacts only)

**0 inventoried files · 0 bytes · [Full file inventory](../inventory/saas.md)**

## Verdict

**`saas/` is dead.** The source was deleted from git on **2026-06-01** in commit
`400f00036 feat(14.2): delete saas/ — Beast EntrepreneurOS is canonical EOS
source`. What remains on disk under `saas/` is **not tracked by git** and is not
inventoried by the census (manifest reports `saas: 0 files, 0 bytes`). It is pure
leftover filesystem detritus:

- **`saas/bridge/__pycache__/organism_bridge.cpython-312.pyc`** — a single stale
  compiled-Python bytecode file. Its **source (`organism_bridge.py`) is gone** —
  only the `.pyc` survived the deletion. It cannot be imported meaningfully (no
  source, and it is a Python 3.12 build while UMH containers run Python 3.11).
- **`saas/node_modules/`** — an orphaned Node dependency tree (Hono, Drizzle
  ORM, `@neondatabase/serverless`, `pg-protocol`, TypeScript, tsx, zod, esbuild,
  dotenv). These are the runtime deps of the deleted TypeScript SaaS/edge
  bridge. The census **excludes** `node_modules/` (counted under the manifest's
  excluded category), which is why `saas/` shows 0 inventoried files despite
  thousands of vendored files still sitting on disk.

`git ls-files saas/` returns nothing — the entire directory is untracked. This
is orphaned build output, not live code.

## What it used to be

Before deletion, `saas/` was a **TypeScript SaaS / edge bridge**: a Hono HTTP
app backed by Drizzle ORM against Neon Postgres. The deletion commit records the
operator decision and the reason it was cut:

> saas/ deleted (not worth converging — severe schema drift, no frontend,
> different auth system). Beast EntrepreneurOS (603 files, Clerk, full-stack) is
> canonical EOS. UMH API entrypoint already exists at
> transports/api/http/server.ts.

The commit removed **30 tracked files** (12 routes, 14 table definitions, 9
migrations, a broken journal, and instance-specific seed data), with **zero
impact on the UMH platform API** — `transports/api/http/` is self-contained and
was already the canonical HTTP surface. The last substantive touches before
deletion were `540ed185d` (runtime config store) and `943358fa5` (phase 9.2
SaaS-layer separation).

## How it fits

It **doesn't** — that is the point. `saas/` is no longer part of any
architecture layer. Its former role (an application projection's web/API bridge)
is now split between two live homes:

- **`transports/api/http/`** — the self-contained UMH platform HTTP API
  (auth, platform DB schema, substrate route handlers). See
  [`transports/`](transports.md).
- **Beast EntrepreneurOS** — the canonical, full-stack EOS application (Clerk
  auth) that lives on the Windows Beast node, not in `/opt/OS`. The
  `projections/eos/` tree here is a **mirror** of a slice of it. See
  [`projections/`](projections.md).

## Recommended classification: DELETE

Per the dormant-classification discipline (PROMOTE / MERGE / ISOLATE / ARCHIVE /
DELETE — memory: `feedback_dormant_classification`), `saas/` is a clean
**DELETE** candidate:

- **Not PROMOTE / MERGE** — the source is already gone and the operator
  explicitly rejected convergence (schema drift, wrong auth system).
- **Not ISOLATE** — nothing imports it; it is already isolated to the point of
  being untracked.
- **DELETE over ARCHIVE** — there is nothing meaningful to archive. The `.pyc`
  has no source, and `node_modules/` is regenerable vendored dependencies. The
  git history (commit `400f00036` and its ancestors) is the archive.

**Action for health-findings:** remove the on-disk `saas/` directory entirely
(`rm -rf saas/`) to reclaim the orphaned `node_modules/` tree and the stale
`.pyc`, consistent with the Node Role Discipline rule that the VPS must not
carry `node_modules` for inactive frontends or old ingestion intermediaries. No
running service references `saas/`. **Flagged for
[health-findings](../health-findings.md).**

## Gotchas

- **Do not resurrect from the `.pyc`.** `organism_bridge.cpython-312.pyc` has no
  matching source and is a wrong-Python-version build. If organism-bridge
  behavior is needed, it lives in the live substrate/organism layer — see
  [`substrate/organism/`](substrate-organism.md), not here.
- **The 0-file manifest count is real, not an error.** It reflects that
  everything remaining is either untracked (`.pyc`) or an excluded category
  (`node_modules/`). Do not "fix" the count by inventorying `node_modules/`.

## See also

- [`projections/`](projections.md) — where EOS lives now (a Beast mirror)
- [`transports/`](transports.md) — the canonical UMH HTTP API that replaced the SaaS bridge
- [`substrate/organism/`](substrate-organism.md) — the live home of organism-bridge behavior
- [Health findings](../health-findings.md)
- [Architecture overview](../architecture.md)
