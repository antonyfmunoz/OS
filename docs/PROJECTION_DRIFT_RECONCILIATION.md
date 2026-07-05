# Projection Drift Reconciliation — Beast ↔ GitHub ↔ /opt/OS Mirror

**Packet:** WP-P4-SOURCE-RECONCILIATION-001. **Non-mutating.** Enforces the
Projection Source-Truth Law (`docs/PROJECTION_SOURCE_TRUTH.md`, PR #173): the
Beast is the source of truth; GitHub can lag it; `data/repos/*` are mirrors.

**Method — three-way, read-only:**
1. **Beast** working tree via the merged read-only probe contract
   (`scripts/probe_beast_projection_source.sh`) — git branch/head/dirty/upstream +
   client/server presence. **No writes, no pull/push/commit/reset/clean/stash.**
2. **GitHub** canonical branch/head via `gh api` (read-only) — default branch,
   branch heads, and a `compare` to detect unpushed Beast commits.
3. **/opt/OS mirror** — `data/repos/*` file inventory (client/server/schema/build).

No Beast code was copied into `/opt/OS`. Machine-readable report:
`data/umh/projection_reconciliation/projection_drift_reconciliation.json`.

## Drift classification vocabulary

| Class | Meaning |
|---|---|
| `source_current` | Beast clean AND Beast head == GitHub head (fully reconciled) |
| `source_dirty` | Beast has uncommitted changes not on GitHub or the mirror |
| `source_unpushed` | Beast has committed changes ahead of GitHub (head absent from GitHub) |
| `source_stale` | Beast is BEHIND GitHub (GitHub has commits the Beast lacks) |
| `branch_diverged` | Beast tracks a non-default branch (current there, not on GitHub default main) |
| `mirror_full` | mirror has client + server + schema + build |
| `mirror_schema_only` | mirror has schema/config but NO client/server (not the app body) |

## Per-projection drift (probe 2026-07-05)

### EntrepreneurOS (EOS) — `source_current`, `branch_diverged`, `mirror_full`
| Axis | Value |
|---|---|
| Beast branch/head | `feature/company-system` @ `17ceaab` |
| Beast dirty | 0 (clean) |
| Beast ahead/behind | 0 / 0 (pushed) |
| GitHub | default `main` @ `86041f5`; `feature/company-system` @ `17ceaab` (present) |
| Beast head pushed? | **yes** (matches GitHub branch head) |
| Mirror | `data/repos/entrepreneuros` — 154 files, client+server+schema+build = **full** |
| Client/server/schema/build | all present (Beast + mirror) |

**Verdict:** The one fully source-current row — clean and pushed — but on a
**feature branch**, diverged from GitHub default `main` (`86041f5`). Active/clean,
branch-diverged from default main.

### CreatorOS — `source_dirty`, `mirror_schema_only` — **NOT dormant**
| Axis | Value |
|---|---|
| Beast branch/head | `main` @ `ca4e161` |
| Beast dirty | **1** (uncommitted) |
| Beast ahead/behind | 0 / 0 (committed head synced) |
| GitHub | default `main` @ `ca4e161` (**same as Beast head**) |
| Mirror | `data/repos/creatoros` — 14 files, **no client/server** = **schema-only** |
| Client/server | present on Beast; **absent** in mirror |

**Verdict:** Committed head is synced with GitHub, but the working tree has **1
uncommitted file** — active local work. The `SYSTEM_ARCHITECTURE.md` "dormant"
label is **refuted**. Mirror is schema-only, not the app body.

### LyfeOS — `source_unpushed`, `source_dirty`, `mirror_schema_only` — **absolutely NOT dormant (highest drift)**
| Axis | Value |
|---|---|
| Beast branch/head | `main` @ `536b8888` |
| Beast dirty | **29** (uncommitted) |
| Beast ahead/behind | **ahead 19** / 0 |
| GitHub | default `main` @ `afc3823`; Beast head `536b8888` → **404 (not on GitHub)** |
| Beast head pushed? | **no** — 19 commits exist only on the Beast |
| Mirror | `data/repos/LYFEOS` — 23 files, **no client/server** = **schema-only** |

**Verdict:** The highest-risk projection. **19 committed-but-unpushed commits + 29
uncommitted files exist ONLY on the Beast** — in neither GitHub nor the VPS mirror.
Losing the Beast working tree loses this work. The "dormant" label is emphatically
**refuted**.

## Summary

| Projection | Classification | Dormant claim | Source of truth location |
|---|---|---|---|
| EntrepreneurOS | source_current + branch_diverged + mirror_full | active/clean | Beast + GitHub (feature branch), full mirror |
| CreatorOS | source_dirty + mirror_schema_only | **refuted — active** | Beast (1 dirty); GitHub synced; mirror schema-only |
| LyfeOS | source_unpushed + source_dirty + mirror_schema_only | **refuted — active** | **Beast ONLY** (19 unpushed + 29 dirty) |

- **No projection is fully `source_current` on GitHub default main.** EOS is current
  only on its feature branch.
- **Two "dormant" labels refuted** (CreatorOS, LyfeOS) — both have live Beast work.
- **Two mirrors are schema-only** (CreatorOS, LyfeOS) and must not be treated as the
  app body.

## What this does NOT do (scope discipline)

- No Beast writes (no pull/push/commit/reset/clean/stash/edit).
- No projection code copied into `/opt/OS`.
- No schema change to the persistent source registry (the reconciliation report is a
  new read-only artifact alongside the #173 map; the two-store unification remains the
  plan-only owner decision from #173).
- No projection feature work; no EOS read-surface #2; no P5.

## Required follow-on (plan-only — owner ruling, not this packet)

1. **Push/backup the Beast-only work** — LyfeOS's 19 unpushed commits + 29 dirty
   files and CreatorOS's 1 dirty file are unbacked. A governed operator action
   (operator-initiated, on the Beast) should commit/push them. This packet only
   *reports* the drift; it does not mutate the Beast.
2. **Windows filesystem-sync / runtime-node harness** (from #173) — to keep this
   reconciliation report fresh automatically and alert on new divergence.
