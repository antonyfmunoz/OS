# Beast Projection Source Sync / Readiness Harness

**Packet:** WP-P4-BEAST-SOURCE-SYNC-001
**Probe:** `scripts/probe_beast_source_readiness.sh` (read-only, repeatable)
**State:** `data/umh/projection_reconciliation/projection_source_sync.json`
**Last probe:** 2026-07-05

---

## Why this exists

The real projection code lives on the Beast (Windows dev node) — the tier-2 source of truth
(`docs/PROJECTION_SOURCE_TRUTH.md`, #173). UMH cannot safely orchestrate projection build-out
if its view of that source goes stale. This harness makes the Beast a **governed source node**:
a repeatable read-only probe that records each projection's git state, backup status, secrets-protocol
status, and mirror fidelity, then classifies **source risk** so UMH can truthfully say which
projection source is current, dirty, backed up, secret-safe, and build-ready.

**It never writes to the Beast, never copies Beast code into UMH, and never prints secret values.**

## Running it

```bash
PROBE_AT=2026-07-05 bash scripts/probe_beast_source_readiness.sh \
  data/umh/projection_reconciliation/projection_source_sync.json
```

Reachability is a hard gate: if the Beast is unreachable the harness emits
`{"beast_status":"UNREACHABLE","projections":[]}` and exits non-zero — it never writes
false-current rows. Every emitted row carries `beast_verification: "VERIFIED"` because it was
produced by a live probe.

## What it records (per projection)

| Field | Meaning |
|---|---|
| `operating_branch`, `head` | current branch + short HEAD on the Beast |
| `dirty_count`, `staged_count`, `untracked_count` | working-tree state |
| `behind`, `ahead`, `unpushed_commits` | position vs `@{upstream}` |
| `local_backup_branches` | count of `backup/*` branches (from #175) |
| `env_op_tpl_present`, `env_gitignored`, `plaintext_env` | secrets-protocol install state |
| `has_client`/`has_server`/`has_package`/`has_schema` | app-body presence on the Beast |
| `runtime_ready` | `yes` iff `.env.op.tpl` present + `.env` gitignored + plaintext `.env` retired |
| `backed_up` | `yes` iff fully pushed (`ahead==0`) or a `backup/*` branch exists |
| `mirror_fidelity` | UMH-side `data/repos/<mirror>`: `full` / `schema_only` / `absent` |
| `app_body_present` | client+server both on the Beast |
| `source_risk` | classification below |

## Source-risk classification (fail-toward-risk)

| Class | Condition |
|---|---|
| `source_at_risk` | unpushed commits exist **and** no backup — work lives only on the Beast |
| `source_unpushed` | unpushed commits exist, but a backup branch protects them |
| `source_dirty` | uncommitted working-tree changes (recoverable only locally) |
| `source_current` | clean, fully pushed, backed up |

## Current Beast source state (2026-07-05)

| Projection | Branch@HEAD | dirty | ahead | runtime_ready | backed_up | mirror | risk |
|---|---|---|---|---|---|---|---|
| EntrepreneurOS | `feature/company-system`@`9c8725f` | 0 | 0 | yes | yes | full | **source_current** |
| CreatorOS | `main`@`139e2c9` | 1 | 0 | yes | yes | schema_only | **source_dirty** |
| LyfeOS | `main`@`6ce1ae3e` | 28 | 0 | yes | yes | schema_only | **source_dirty** |

**Read this before projection build-out:**
- All three are **runtime-ready** (1Password secret protocol installed + boot-verified, #177/#178)
  and **backed up** (ahead=0 → operating branch pushed to GitHub; LyfeOS also has a `backup/*` branch).
- **EntrepreneurOS** is the only `source_current` repo and the only `full` mirror — the safest
  first target for a Beast-backed import/build slice.
- **CreatorOS / LyfeOS** are `source_dirty` (CreatorOS 1 file = a local DB dump; LyfeOS 28 WIP
  source files) and only `schema_only` mirrors in `/opt/OS`. Their working-tree WIP is **not**
  on GitHub — build-out that depends on that WIP must probe the Beast first, not the mirror.

## Guardrails (enforced by `tests/test_projection_source_sync.py`)

- A dirty or unpushed repo can **never** be classified `source_current`.
- A repo without the op-run protocol can **never** be `runtime_ready`.
- A `schema_only`/`absent` mirror can **never** be `full`.
- `beast_status` other than `REACHABLE` yields **no** current rows.
- No secret values appear in the record.

## Related

- `docs/PROJECTION_SOURCE_TRUTH.md` (#173) — the four-tier source-truth law.
- `docs/PROJECTION_SECRET_RUNTIME_PROTOCOL.md` (#177) — the runtime contract behind `runtime_ready`.
- `docs/PROJECTION_SECRETS_RETIREMENT_2026-07-05.md` (#178) — plaintext `.env` retirement behind `plaintext_env`.
- `scripts/probe_beast_projection_source.sh` (#173) — the narrower source-truth probe this extends.
