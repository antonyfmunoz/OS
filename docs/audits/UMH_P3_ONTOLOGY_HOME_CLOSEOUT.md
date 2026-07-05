# WP-P3 — Ontology-Home Convergence Closeout / Handoff

**Status:** COMPLETE. Anchored to main `522c52aa7` (after #163).
**Scope:** the P3 projection/metamodel/ontology-home boundary convergence — from
defining the layer contract to evicting the last contaminated file. This is a
handoff report, not a plan. It states what P3 enforced, what moved, what is
intentionally unmoved, and what is still known debt. **No P4/P5 here.**

## 1. What P3 set out to do

Make the ontology / reality / domain / grounding / world-model **homes**
unambiguous and enforceable, then evict the files that sat in the wrong layer —
**without** pretending divergent models are equivalent to the canonical platform
types, and without starting projection build-out. The permanent P3 order was:

1. Define & enforce the layer law ✅
2. Converge the projection registration port ✅
3. Converge the registry read paths ✅
4. Converge the ontology homes ✅
5. Evict contaminated files in small, owner-ruled packets ✅ (this is now done)
6. → P4 projection build-out (NOT started — next phase)

## 2. Packet ledger (all merged to main)

| PR | Commit | What it did |
|---|---|---|
| #155 | `bbd31239f` | **Define & enforce** the ontology/metamodel layer contract (Gate 11 `check_ontology_layers.py`) |
| #156 | `f3568f279` | Converge to **one canonical projection registration port** (`substrate/sockets/projection_port.py`) |
| #157 | `85cf1206e` | Converge **read-side projection-registry consumers** onto the canonical port (Gate 12 `check_projection_registry_reads.py`, AST-based) |
| #158 | `e8538890a` | **Consolidate ontology homes** into an enforceable layer map (Gate 13 `check_ontology_homes.py` + `FROZEN_ONTOLOGY_HOMES`/`FROZEN_ONTOLOGY_COMPETITORS` shrink-only ledgers) |
| #159 | `3e1dbe736` | Sunset the `understanding/world_model` name-collision by **disambiguation** (reciprocal docstrings; not a competitor) → competitors 3→2 |
| #160 | `2675a486c` | Relocation **SPEC** (plan-only) for `understanding/ontology/primitives.py` (owner ruling baked in) |
| #161 | `705a3e205` | **Relocate** the L3 business-rule primitives → `substrate/state/business/primitives.py` (no shim, whole) → homes 27→26, competitors 2→1 |
| #162 | (open, plan) | Recon **micro-plan** for the last competitor `primitive_decomposition_v1.py` |
| #163 | `522c52aa7` | **Rehome + enum split** of `primitive_decomposition_v1.py` → `substrate/understanding/perception/` (enums repointed to `substrate.types`) → homes 26→25, **competitors 1→0** |

## 3. What P3 enforced (the gates that now hold the line)

Three pre-commit gates (all in `scripts/pre-commit` + `scripts/install_hooks.sh`),
each with a non-growth test:

| Gate | Script | Invariant |
|---|---|---|
| **11** | `check_ontology_layers.py` | L3 CONTENTS stay out of the L2 SURFACE (`substrate/types.py`, `substrate/ontology/`) — no projection/BIS vocab or imports in L2 |
| **12** | `check_projection_registry_reads.py` | only `substrate/sockets/projection_port.py` reads `data/umh/projection_registry.json` (AST-verified) — no fork of the registration surface |
| **13** | `check_ontology_homes.py` | the SET of ontology/reality/domain/world-model homes is frozen shrink-only (`FROZEN_ONTOLOGY_HOMES`), and no competing ontology/domain-model registry may appear (`FROZEN_ONTOLOGY_COMPETITORS`) |

**Final ledger state on main:** `FROZEN_ONTOLOGY_HOMES = 25`,
`FROZEN_ONTOLOGY_COMPETITORS = 0`. Every P3 gate is green on `522c52aa7` with no
`UMH_ROOT` workaround (main is internally consistent).

## 4. What moved (and why)

| File | From | To | Resolution |
|---|---|---|---|
| business primitives (`KnowledgePrimitive`, `PRIMITIVE_LIBRARY`, `PrimitiveRegistry`, `ContextualReasoningEngine`) | `substrate/understanding/ontology/primitives.py` | `substrate/state/business/primitives.py` | **relocation** — L3 business-rule logic → its L3 state home, co-located with `BusinessInstanceManager`. No shim, whole file. (#161) |
| perception decomposition model (`PrimitiveObservation` v1, `PrimitiveRelationship`, `DecompositionResult`, `REQUIRED_PRIMITIVE_TYPES`) | `substrate/understanding/ontology/primitive_decomposition_v1.py` | `substrate/understanding/perception/primitive_decomposition_v1.py` | **split + rehome** — the duplicate `PrimitiveType`/`RelationshipType` enum fork was removed (now imported from `substrate.types`); the perception dataclasses moved intact to their perception home. No shim, no class rename. (#163) |

Result: **`substrate/understanding/ontology/` now contains only `__init__.py`.** No
metamodel fork remains in an ontology dir.

## 5. What is intentionally UNMOVED (by owner ruling — not debt)

- **The v1 perception dataclasses were NOT collapsed onto `substrate.types`.**
  `PrimitiveObservation` v1 (str `observation_id`, `is_inferred`, `.to_dict()`,
  separate `PrimitiveRelationship`/`DecompositionResult` envelope) is a genuine
  perception model, not the canonical Pydantic `substrate.types.PrimitiveObservation`
  (UUID id, embedded relationships). Collapsing would break 7 of 10 importers +
  the L4 domain-bridge contract + 7 test files. It is deliberately kept distinct.
- **No class rename.** `PrimitiveObservation` → `PerceptionPrimitiveObservation`
  was explicitly deferred to a later naming-cleanup packet to avoid adding a
  refactor axis to the rehome.
- **`substrate/state/business/` mixes "state" and "rules."** Accepted in #161
  because an existing business-state home already owned the closest dependency;
  splitting rules from state is not warranted for a first relocation.
- **`Venture` / `BusinessInstance` / `Company` / `Department` / `Portfolio`
  were never moved.** P3 was boundary/home convergence, not domain-object
  migration.

## 6. Known remaining debt (out of P3 scope — for later, owner-ruled packets)

- **`LEGACY_DUPLICATES_META` still holds 14 modules** with sunset dates (mostly
  `2026-12-31`). P3 removed the two `primitive_decomposition_v1` enum entries and
  re-anchored its `PrimitiveObservation` entry; the rest (worker/execution
  contracts `_v1`, memory-store `_v1`, sockets envelopes, candidate-gen
  `MemoryType`, etc.) are pre-P3 type-centralization debt, each owner/sunset-tracked.
  These are the natural targets of a future **type-dedup** phase, not P3.
- **The v1 perception-model naming-cleanup** (`PrimitiveObservation` →
  `PerceptionPrimitiveObservation`) remains as a candidate packet; it would retire
  the last `primitive_decomposition_v1` `LEGACY_DUPLICATES` entry.
- **Cross-worktree `sys.path` hazard.** Several test files hardcode
  `sys.path.insert(0, os.environ.get("UMH_ROOT") or "/opt/OS")`. When run from a
  worktree nested under `/opt/OS` with `UMH_ROOT` unset, namespace-package
  resolution can pick up the main checkout's (stale) files — a test-harness
  hazard, not a runtime defect. It resolves once changes land on main. A future
  hygiene packet could make these path inserts worktree-relative.
- **`data/` generated audit snapshots** (`graphify_overlay.json`,
  `2026-06-23_*` inventories) still reference the old ontology paths. Non-runtime;
  regenerated by `scripts/update-graph`. Left untouched per packet discipline.

## 7. Verification (on merged main `522c52aa7`, no workaround)

- All 13 pre-commit gates green.
- `check_ontology_homes.py --all` → 25 homes, **0 frozen competitors**.
- `check_type_divergence.py --registry-audit` → truthful (1047 entries, 0 dup
  keys, 16 exemptions all resolve + carry metadata).
- `check_dependency_direction.py --all` → clean over 1303 files, zero new
  `substrate_imports_projections`.
- pytest collection clean (15,362).
- Regression + v1 pack: 193 passed, 24 skipped. The only 5 failures
  (`test_decomposer_depth.py`) are LLM-extraction-quality tests (offline LLM path,
  `assert None is not None`), reproduced identically on clean origin/main —
  pre-existing, not P3 regressions.
- Behavior equivalence: the moved perception model exposes the same public
  surface; its `PrimitiveType`/`RelationshipType` are the exact canonical
  `substrate.types` objects (identity); old import paths raise `ModuleNotFoundError`
  (no shim).

## 8. Housekeeping recommended at closeout

- **Close #162** (the recon plan for `primitive_decomposition_v1.py`) — superseded
  by the merged #163 execution. Its content is preserved in this closeout + the
  consolidation audit.
- **Triage #154** (older "P3 micro-plan: projection/metamodel separation,
  planning only") — confirm whether its scope is fully subsumed by #155–#163 and
  close, or carve out any genuinely-remaining item into a tracked follow-on.

## 9. Handoff — what comes next (NOT started)

P3 ontology-home convergence is complete. The next phase is **P4 projection
build-out** (`projections/eos`, `creatoros`, `lyfeos` are present as integration
shells; EOS is the fullest). That is a separate phase with its own plan and owner
rulings — it is **not** started here. The type-dedup of the remaining 14
`LEGACY_DUPLICATES` modules is a parallel candidate, also not started.

No P4/P5 work has begun. This report is the clean stopping point.
