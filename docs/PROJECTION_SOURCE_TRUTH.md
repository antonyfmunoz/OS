# Projection Source-Truth Law

**Law:** *Projection build-out cannot outrun projection source truth.*

Declared truth is not source truth. `docs/SYSTEM_ARCHITECTURE.md`, `data/repos/*`,
`data/umh/projection_registry.json`, and any VPS-local mirror path are
**declarations and mirrors** — statements *about* where the projection body lives,
and partial *copies* of it. They are not the body. The actual projection
application code (frontend, backend, product schema, product workflows) lives on
the **Beast** — the Windows development node (`beast` / `desktop-lvguiq9` /
`<beast-ip>`, repos root `C:\dev\dev\`).

Therefore:

> **Projection source truth is not established until UMH verifies the actual
> projection filesystem on the Beast/Windows node, or explicitly records that the
> Beast is unreachable/unverified. No projection may be treated as
> source-current while its Beast verification status is `UNVERIFIED`.**

## The four tiers of a projection

Every projection is FOUR distinct things. Conflating them is the lie this law
forbids.

| Tier | What it is | Where | Authority |
|---|---|---|---|
| 1. Canonical GitHub source | the shared hub of record | `github.com/<your-org>/<Repo>.git` | canonical, but a *push target* — can lag the Beast |
| 2. **Beast Windows working tree** | the **actual live source body** | `C:\dev\dev\<Repo>\` on the Beast | **the source of truth** — may hold unpushed/uncommitted work |
| 3. VPS `/opt/OS` mirror / snapshot | read-only reference copy | `data/repos/<repo>/` | mirror only — NEVER the app body; may be schema-only |
| 4. Deployed runtime / health surface | the running product | `public_url` + `health_url` in `projection_registry.json` | runtime truth, not source truth |

The UMH `projections/<name>/` directory is **none of these four** — it is a
substrate-side *integration/readiness/control-plane shell* (see
`.claude/rules/projection-read-surfaces.md`). EOS is a fuller shell (integration +
entity model + department agents + workflows + views); CreatorOS and LyfeOS are
bare integration shells (manifest + poller only). **No `projections/*` shell is the
product app.**

## Beast verification status (required state field)

Every projection source row MUST declare a `beast_verification` status:

- **`VERIFIED`** — UMH has directly probed the Beast filesystem and recorded the
  observed path, git remote, branch, HEAD, dirty count, and upstream state. Only a
  `VERIFIED` row may be considered source-current, and only as of its probe
  timestamp.
- **`UNVERIFIED`** — no successful Beast probe on record. The row's source
  currency is UNKNOWN. Downstream build-out MUST NOT proceed as if the local
  mirror or the docs are the source.
- **`UNREACHABLE`** — a probe was attempted and the Beast could not be reached
  (offline, SSH refused, tailscale down). Recorded with the attempt timestamp.
- **`NOT_APPLICABLE`** — the projection has no Beast working tree by design
  (e.g. UMH itself, which is canonical on the VPS).

`data/umh/projection_reconciliation/projection_source_truth.json` holds the map.
The machine-readable rows are the enforced artifact; this doc is the law.

## Observed source truth (probe of 2026-07-05)

The Beast was reachable and probed read-only (ping + SSH key auth + tailscale peer
active). Observed working trees at `C:\dev\dev\`:

| Projection | Beast path | git remote | branch | HEAD | dirty | upstream | client/server |
|---|---|---|---|---|---|---|---|
| EntrepreneurOS (EOS) | `C:\dev\dev\EntrepreneurOS` | `<your-org>/EntrepreneurOS.git` | `feature/company-system` | `17ceaab` | 0 (clean) | tracks `origin/feature/company-system` | both present |
| CreatorOS | `C:\dev\dev\CreatorOS` | `<your-org>/CreatorOS.git` | `main` | `ca4e161` | 1 | tracks `origin/main` | both present |
| LyfeOS | `C:\dev\dev\LyfeOS` | `<your-org>/LYFEOS.git` | `main` | `536b8888` | 29 | `origin/main` **[ahead 19]** | both present |

### Drift the probe exposed (declaration/mirror vs Beast truth)

1. **The Beast is ahead of everything for LyfeOS.** 19 unpushed commits + 29
   uncommitted files exist ONLY on the Beast — not on GitHub, not in the VPS
   mirror. A packet trusting docs/mirrors would have declared LyfeOS "dormant" and
   missed live source.
2. **`data/repos/creatoros` (14 files) and `data/repos/LYFEOS` (23 files) are
   schema-only snapshots**, but the Beast has full `client/` + `server/` for all
   three. The VPS mirror is NOT a faithful copy of the app body. The prior
   `SYSTEM_ARCHITECTURE.md` "read-only reference clone" label overstates
   CreatorOS/LyfeOS local presence — corrected here.
3. **EntrepreneurOS `feature/company-system` head is confirmed** by the Beast
   (matches `SYSTEM_ARCHITECTURE.md §2.2`), clean tree — the one fully consistent
   row.

## What UMH may do per projection (until a Windows sync harness exists)

- **READ (mirror)** — `data/repos/*` is readable, but is a snapshot, not the body.
- **READ (Beast, probe-only)** — read-only SSH filesystem probes (as done here) to
  record source-truth status. No content copy into UMH.
- **WRITE** — none. UMH does not write to the Beast working trees.
- **EXECUTE** — none. UMH does not build/deploy the Beast app bodies.

Anything beyond read-only probing requires the follow-on **Windows runtime-node /
filesystem-sync harness** (below).

## Prohibitions

- Do NOT claim projection source truth from `SYSTEM_ARCHITECTURE.md`,
  `data/repos/*`, `projection_registry.json`, or VPS paths alone.
- Do NOT copy Beast app code into `/opt/OS`.
- Do NOT infer Beast state from docs — only from a recorded probe.
- Do NOT treat `data/repos/*` as the app body unless a probe proves it is synced
  from the same source (it is not, today).
- Do NOT treat any projection as source-current while `beast_verification` is
  `UNVERIFIED`.

## Required follow-on (plan-only, not this packet)

1. **Windows filesystem-sync / runtime-node harness** — a governed, scheduled
   Beast probe that keeps `projection_source_truth.json` fresh and detects when the
   Beast diverges from GitHub (e.g. LyfeOS's 19 unpushed commits).
2. **Source-store unification (schema change — owner decision)** — the persistent
   `substrate/organism/projection_source_registry.py` (free-text `device`) and the
   non-persistent typed `ProjectionMachineType`/`ProjectionAvailability` enums in
   `substrate/organism/projection_integration_runtime.py` are two parallel,
   non-joined projection-truth stores. Unifying them and adding typed
   `machine_class` / `availability` / `build_status` / `blocked_until` fields to
   the persistent model, and splitting the `SharedTrinity` group into per-projection
   rows, is a schema change held for owner approval. NOT done here.
