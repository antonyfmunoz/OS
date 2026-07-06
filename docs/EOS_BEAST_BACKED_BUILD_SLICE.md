# EOS Beast-Backed Build Slice #1 — Source-to-Substrate Mapping

**Packet:** WP-P4-EOS-BEAST-BACKED-BUILD-001
**Slice:** tie the EOS projection readiness surface to VERIFIED Beast source truth
**Gated by:** the #179 source-readiness harness (EntrepreneurOS `source_current` + `full` mirror + `runtime_ready`)

---

## The premise (ground truth, not assumption)

The real EOS app body lives on the **Beast** (`C:\dev\dev\EntrepreneurOS`, tier-2 source of
truth — `docs/PROJECTION_SOURCE_TRUTH.md`). `/opt/OS/projections/eos/*` is a substrate
**integration shell**, and `data/repos/entrepreneuros/*` is a **mirror**, not the source. This
slice does not pretend otherwise: it makes the EOS shell's readiness surface *report* the
verified Beast source state instead of assuming the mirror is current.

This is the smallest useful Beast-backed slice — a **read-only** integration, no blind code
copy, no schema change, no Beast writes.

## Why EOS is the first (and only) safe target

Per the #179 harness (live, VERIFIED 2026-07-05):

| Projection | source_risk | runtime_ready | mirror | → first-target? |
|---|---|---|---|---|
| **EntrepreneurOS** | `source_current` | yes | **full** | **yes** |
| CreatorOS | `source_dirty` | yes | schema_only | no |
| LyfeOS | `source_dirty` | yes | schema_only | no |

EOS is the only row that is simultaneously `source_current` **and** `full` mirror **and**
`runtime_ready` — the only build-safe first target. CreatorOS/LyfeOS remain backed-up and
runtime-ready but dirty/schema-only, so they are explicitly **not** used here.

## The mapping (Beast source → substrate shell)

```
  Beast source state                     canonical substrate port                EOS shell accessor
  (probe_beast_source_readiness.sh)      (substrate/sockets/projection_port)     (projections/eos/…/readiness.py)
  ─────────────────────────────────      ───────────────────────────────────    ──────────────────────────────
  projection_source_sync.json       ──▶  load_beast_source_sync()           ──▶  eos_readiness()
    projections[eos] {                    _read_beast_source_sync_file()          composes get_beast_source_row("eos")
      source_risk, runtime_ready,         (the ONE reader — never opened by        → flat beast_* keys +
      backed_up, mirror_fidelity,          the projection accessor)                  source_build_safe
      beast_verification, head, … }       get_beast_source_row(id) →               (never raises; {} → None fields)
                                            VERIFIED+REACHABLE rows only
```

### What was added

1. **`substrate/sockets/projection_port.py`** — a canonical reader, mirroring the WP-P3
   `load_umh_projection_seed` convergence:
   - `_read_beast_source_sync_file()` — **the ONE reader** of
     `data/umh/projection_reconciliation/projection_source_sync.json`; returns a safe empty
     envelope (`beast_status: "UNKNOWN"`) on missing/malformed. Never raises.
   - `load_beast_source_sync()` — port-backed public read of the whole document.
   - `get_beast_source_row(projection_id)` — returns a projection's row **only** when the probe
     was `REACHABLE` and the row is `beast_verification == "VERIFIED"`; otherwise `{}`. This is
     what prevents a stale/UNREACHABLE/unverified record from surfacing as current.

2. **`projections/eos/integration/readiness.py`** — `eos_readiness()` now composes
   `get_beast_source_row("eos")` and surfaces the verified source state as **flat `beast_*` keys**
   (`beast_source_risk`, `beast_runtime_ready`, `beast_backed_up`, `beast_mirror_fidelity`,
   `beast_operating_branch`, `beast_head`, `beast_verification`, `beast_probe_at`) plus a derived
   **`source_build_safe`** boolean (True iff `source_current` + `runtime_ready` + `backed_up` +
   `full` + `VERIFIED`). Flattened (not a nested dict) to honor the read-surface flat-shape
   invariant, which sanctions only the single `seed` summary dict.

### Read-surface discipline honored

- The accessor **never opens** the reconciliation file — it composes the canonical port
  (`.claude/rules/projection-read-surfaces.md` invariant #6; enforced by a new test that greps
  the accessor source).
- Downward imports only (projection → substrate); dependency-direction gate clean.
- Never raises; env-disabled/record-absent → `beast_*` all `None`, `source_build_safe` `False`.

## What this slice deliberately is NOT

- **Not** a code import — no EOS app body was copied from the Beast into `/opt/OS`.
- **Not** a schema change — no new tables, no migration.
- **Not** a mutation — read-only; no Beast writes; no runtime side effects.
- **Not** CreatorOS/LyfeOS work; **not** P5.

## Reversibility

Fully reversible: the slice adds one port reader + flat readiness keys + tests. Removing the
`beast_*` keys and the port functions restores the prior readiness shape with no data or schema
consequences.

## Current live output (VERIFIED, EOS)

```
beast_source_risk      = source_current
beast_runtime_ready    = yes
beast_backed_up        = yes
beast_mirror_fidelity  = full
beast_operating_branch = feature/company-system
beast_head             = 9c8725f
beast_verification     = VERIFIED
beast_probe_at         = 2026-07-05
source_build_safe      = True
```

## Next (separate, held)

With EOS readiness now tied to verified Beast source truth, the next Beast-backed slice can begin
the actual EOS app-module → substrate mapping (still read-first, still gated on
`source_build_safe`). CreatorOS/LyfeOS become eligible once their harness rows reach
`source_current` (WIP committed/pushed) and a fuller mirror exists.

## Related

- `docs/PROJECTION_BEAST_SOURCE_SYNC.md` (#179) — the harness this slice consumes.
- `docs/PROJECTION_SOURCE_TRUTH.md` (#173) — the four-tier source-truth law.
- `.claude/rules/projection-read-surfaces.md` (#172) — the read-surface discipline.
- `projections/eos/integration/readiness.py` — the extended accessor (originally PR #171).
