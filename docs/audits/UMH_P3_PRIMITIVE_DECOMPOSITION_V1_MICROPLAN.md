# WP-P3 — `primitive_decomposition_v1.py` Convergence Micro-Plan (PLAN ONLY)

**Branch:** `docs/p3-primitive-decomposition-v1-microplan`
**Base:** `705a3e205` (main after #161 — primitives relocation)
**Status:** RECON + BOUNDED MICRO-PLAN — **no code moved, no imports changed, no
ledger/gate change, no runtime behavior change.** Doc-only. This is the planning
artifact for a separate, owner-approved execution packet. Nothing is repointed,
renamed, split, or deleted here.

## 0. Why this file is the last P3 ontology-home target

After #161, the Gate-13 ledgers are `FROZEN_ONTOLOGY_HOMES = 26` /
`FROZEN_ONTOLOGY_COMPETITORS = 1`. The **one** remaining frozen competitor is
`substrate/understanding/ontology/primitive_decomposition_v1.py`
(disposition `parallel-L2-metamodel`, sunset `P3 metamodel dedup packet`).

Unlike the business primitives file (#161, a clean relocation), this one is
**semantically load-bearing in the perception → interpretation → decomposition →
domain-bridge pipeline** and has more importer gravity. It must NOT be treated as
a relocation. The purpose of this recon is to prove **what it actually is** before
any code moves — is it (a) redundant metamodel, (b) perception-specific metamodel,
or (c) an adapter over the canonical metamodel? The answer determines whether the
next packet is a safe repoint, a rename, a split, or a deeper convergence.

## 1. Exact symbol map (the file — 127 lines)

| Symbol | Kind | Canonical equivalent in `substrate.types`? | Verdict |
|---|---|---|---|
| `PrimitiveType` | `str, Enum` — 10 values (STATE…TIME) | **YES — byte-identical** (`substrate/types.py:693`, same 10 values, same order) | Pure duplicate |
| `RelationshipType` | `str, Enum` — 10 values (CAUSES…CONFLICTS_WITH) | **YES — byte-identical** (`substrate/types.py:717`, same 10 values) | Pure duplicate |
| `REQUIRED_PRIMITIVE_TYPES` | `frozenset[PrimitiveType]` constant | **NO** (no such constant in `substrate.types`) | v1-only helper |
| `PrimitiveObservation` | `@dataclass` | **DIVERGES** — see §2 | v1-specific perception model |
| `PrimitiveRelationship` | `@dataclass` | **NO** (no `PrimitiveRelationship` in `substrate.types`) | v1-only perception model |
| `DecompositionResult` | `@dataclass` | **NO** (no `DecompositionResult` in `substrate.types`) | v1-only perception model |

## 2. The critical divergence — `PrimitiveObservation` v1 ≠ canonical

The two enums are identical, but the observation model is a **different type with
a different contract**. This is the crux of the whole packet.

| Aspect | v1 `@dataclass` (`primitive_decomposition_v1.py:46`) | canonical Pydantic (`substrate/types.py:745`) |
|---|---|---|
| Base | `@dataclass` (no validation) | `BaseModel` (Pydantic, validated) |
| Identity | `observation_id: str` | `id: UUID` (default `uuid4`) |
| Extra fields | `source_reference`, `evidence`, `is_inferred` | `category`, `source_document_id`, `source_decomposition_id` |
| Relationships | **separate** `PrimitiveRelationship` dataclass + `DecompositionResult` envelope | **embedded** `relationships: list[tuple[RelationshipType, UUID]]` |
| Constraints | none | `label` max_length=80, `description` max_length=300, `confidence` 0–1, `authority_tier` 1–9 |
| Serialization | explicit `.to_dict()` method | Pydantic `.model_dump()` |

A naive swap of v1 → canonical `PrimitiveObservation` would **break every
construction and consumption site** (no `observation_id`, no `is_inferred`, no
`source_reference`, no `.to_dict()`, no separate relationship/result envelope).

## 3. Importer map (11 runtime + 7 test; `canonical_types.py` = registration)

Scope: real tree only (`.claude/worktrees/*` sibling checkouts excluded — they are
other branches, not importers of the live file).

### 3a. Runtime importers (11)

All 10 runtime imports are **module-level** (top-of-file import blocks — none lazy).

| # | File:line | Symbols | Constructs? | Coupling class |
|---|---|---|---|---|
| 1 | `substrate/understanding/domains/business.py:13` | `PrimitiveObservation` | No (type hint) | **(a)** reads `.observation_id` (`:237`), `.evidence`, `.authority_tier`; `bridge(obs)` contract type (`:199`) |
| 2 | `substrate/understanding/domains/creator.py:11` | `PrimitiveObservation` | No (type hint) | **(a)** reads `.observation_id` (`:507`), `.evidence`, `.authority_tier` |
| 3 | `substrate/understanding/domains/life.py:11` | `PrimitiveObservation` | No (type hint) | **(a)** reads `.observation_id` (`:560`), `.evidence`, `.authority_tier` |
| 4 | `substrate/understanding/domains/contract.py:14` | `PrimitiveObservation` | No | **(c) NON-breaking** — type hint only on `DomainBridge.bridge(observation)` (`:26`); no v1-field access |
| 5 | `substrate/understanding/perception/orchestrator.py:20` | `DecompositionResult`, `PrimitiveObservation`, `PrimitiveRelationship`, `PrimitiveType`, `RelationshipType` | **YES all 3** | **(a) deepest** — constructs `PrimitiveObservation(observation_id=…, source_reference=…, is_inferred=…)` (`:605,676,690,708,722,737`) + `PrimitiveRelationship` (`:641,752`) + `DecompositionResult` (`:650,761`); `.compute_coverage()` (`:514`), `.to_dict()` (`:1134`) |
| 6 | `substrate/understanding/interpretation/interpretation_engine_v1.py:23` | multi (all 3 + enums) | **YES all 3** | **(a)** constructs `PrimitiveObservation(observation_id=…)` (`:358,371,385,398`); `PrimitiveRelationship` (`:425,439`); `DecompositionResult` (`:457`); `.compute_coverage()` (`:478`); compares `o.primitive_type == PrimitiveType.GOAL/.CONSTRAINT` (`:490,506`) |
| 7 | `substrate/execution/understanding_bridge.py:33` | `DecompositionResult` only | No | **(c) NON-breaking** — bare type annotation `decomposition: DecompositionResult \| None` (`:66`); never touches `PrimitiveObservation` |
| 8 | `substrate/execution/ingestion/__init__.py:22` | multi | No | **(c) NON-breaking** — pure re-export passthrough into `__all__` (`:40-43`) |
| 9 | `adapters/adapter_engine/substrate_candidate_gen_v1.py:20` | `DecompositionResult`, `PrimitiveObservation`, `PrimitiveType` | No (consumes) | **(a)** reads `.decomposition_id`/`.observations`/`.source_content_hash`; per-obs `.observation_id` (`:189`), `.source_reference` (`:204`), `.is_inferred` (`:206`); `PrimitiveType.*` classification set (`:121-140`) |
| 10 | `adapters/adapter_engine/substrate_decomposer_v1.py:19` | multi (all 3 + enums) | **YES all 3** (primary producer) | **(a)** constructs `PrimitiveObservation(observation_id=…, source_reference=…, is_inferred=…)` (`:213`), `PrimitiveRelationship` (`:231,247`), `DecompositionResult` (`:256`); `.compute_coverage()` (`:262`) |
| 11 | `substrate/canonical_types.py:1370` | — (registration) | n/a | **LEGACY_DUPLICATES entry**, not a code consumer (see §4) |

**Break/no-break on a naive `PrimitiveObservation` swap to canonical Pydantic:**
7 sites **break** (1,2,3,5,6,9,10 — construct with `observation_id=`/`source_reference=`/
`is_inferred=` kwargs the canonical model lacks, or read those attributes, or call
`.to_dict()`, or depend on the separate `PrimitiveRelationship`/`DecompositionResult`
envelope). 3 sites **do not break** (4 `contract.py` type-hint-only, 7
`understanding_bridge.py` `DecompositionResult`-annotation-only, 8
`ingestion/__init__.py` re-export passthrough). Full break-site list corroborated by
an independent recon pass.

**Enum-identity coupling:** none. Grep for `isinstance(..., PrimitiveType)` /
`isinstance(..., RelationshipType)` across `substrate/` + `adapters/` → **zero
hits**. Enum consumers (class **(b)**: the `PrimitiveType.*` / `RelationshipType.*`
member comparisons in decomposer `:159-284`, candidate_gen `:121-140`, orchestrator,
interpretation_engine) use the enums **by value** and would work against
`substrate.types` enums unchanged — repoint is identity-safe.

### 3b. Test importers (7) — v1 shape is covered behavior

`test_interpretation_engine_v1.py` (asserts `o.observation_id` — `:101`),
`test_decomposer_depth.py`, `test_authority_tier.py`, `test_domain_bridge.py`,
`test_domain_bridge_life_creator.py` (`observation_id=` construction — `:30`),
`test_gws_to_canonical_ingestion_v1.py`, and `test_ontology_home_map.py` (ledger
comment only). Multiple assert on v1-only fields (`observation_id`, `is_inferred`,
`.to_dict()`) — the v1 perception shape is **behaviorally load-bearing and tested**,
not incidental.

## 4. Canonical-registry status — already a tracked, sunset-dated duplicate

`substrate/canonical_types.py:1370` registers this module in `LEGACY_DUPLICATES`:

```
"substrate.understanding.ontology.primitive_decomposition_v1": {
    "PrimitiveType":        { owner: "understanding-ontology", sunset: "2026-12-31", rationale: "ontology v1 primitive types predate centralization" },
    "RelationshipType":     { owner: "understanding-ontology", sunset: "2026-12-31", ... },
    "PrimitiveObservation": { owner: "understanding-ontology", sunset: "2026-12-31", ... },
}
```

Two consequences:
1. This is a **known, owner-owned, sunset-dated** duplicate — not a surprise leak.
   Convergence is expected before `2026-12-31`.
2. The registry lists the **3 name-homonyms only** (`PrimitiveType`,
   `RelationshipType`, `PrimitiveObservation`). `PrimitiveRelationship`,
   `DecompositionResult`, and `REQUIRED_PRIMITIVE_TYPES` are **not** registered as
   duplicates because they have **no canonical counterpart** — confirming they are
   v1-perception-original, not clones.

Note also: `substrate/ontology/primitives.py` is a **pure re-export shim** of the
canonical `substrate.types` symbols (`PrimitiveType`, `RelationshipType`,
`PrimitiveObservation`, …). The canonical L2 home already exists and is thin; the
v1 file is the divergent sibling.

## 5. Canonical-equivalence table (roll-up)

| v1 symbol | Canonical home | Equivalence | Convergence action (execution packet) |
|---|---|---|---|
| `PrimitiveType` | `substrate.types.PrimitiveType` | **identical** | **repoint** importers to `substrate.types`; drop the v1 redefinition |
| `RelationshipType` | `substrate.types.RelationshipType` | **identical** | **repoint**; drop the v1 redefinition |
| `PrimitiveObservation` (v1) | `substrate.types.PrimitiveObservation` | **NOT equivalent** (str-id dataclass vs UUID Pydantic; different fields/shape) | **KEEP** as a perception model; do **not** collapse |
| `PrimitiveRelationship` | none | — | **KEEP** (perception-original) |
| `DecompositionResult` | none | — | **KEEP** (perception-original) |
| `REQUIRED_PRIMITIVE_TYPES` | none | — | **KEEP** (perception-original helper) |

## 6. Behavioral risk analysis

- **Enum repoint (low risk):** values byte-identical, no `isinstance` identity
  coupling, `str`-Enum so equality is by value. Repointing the 11 importers'
  enum imports to `substrate.types` is behavior-preserving. Risk: a stray site
  that imports the enum *from* the v1 module for re-export — must grep and update.
- **Observation/Relationship/Result collapse (HIGH risk — REJECTED):** every
  construction site uses v1-only kwargs (`observation_id`, `source_reference`,
  `is_inferred`) and the separate `PrimitiveRelationship`/`DecompositionResult`
  envelope; domain bridges type their `bridge()` contract on the v1 dataclass;
  tests assert the v1 shape. Swapping to the canonical Pydantic model would break
  the perception pipeline, the L4 bridge contract, and the test suite. This is not
  a dedup — it's a different model serving a different concern (raw perception
  decomposition vs the validated platform observation).
- **Home ambiguity (the actual P3 problem):** the file sits in
  `substrate/understanding/ontology/` — an *ontology* dir — while it is really a
  **perception/decomposition data model**, not metamodel law. That location is
  what makes it read as a "parallel L2 metamodel." The convergence is about
  **naming + home + enum-source**, not about collapsing the model.

## 7. Recommended disposition — **D (split), with a C outcome for the survivors**

**Recommendation (for owner approval — not executed here):**

1. **Enums → canonical (disposition A, for the two enums only).** Repoint all
   importers' `PrimitiveType` / `RelationshipType` usage to `substrate.types`;
   remove the two redefinitions from the v1 file. This burns the "parallel L2
   metamodel" characterization — the metamodel enums stop being forked.

2. **Dataclasses → a clearly-named perception model (disposition C).** The
   surviving `PrimitiveObservation` (v1), `PrimitiveRelationship`,
   `DecompositionResult`, `REQUIRED_PRIMITIVE_TYPES` are a
   **perception/decomposition adapter model** with no canonical equivalent. Give
   them an honest home + name that says "perception decomposition," not "ontology
   metamodel" — e.g. under `substrate/understanding/perception/` or
   `substrate/understanding/decomposition/` — so the file no longer masquerades as
   an L2 ontology home. This is the split that resolves the Gate-13 competitor:
   after it, no file in `substrate/understanding/ontology/` redefines the metamodel.

**Why this is the correct shape:** the file is **not** redundant metamodel (only
its two enums are), and it is **not** a naive collapse candidate (its data model is
perception-specific and load-bearing). It is a *metamodel-enum duplication* wrapped
around a *legitimate perception model that lives in the wrong dir*. Splitting those
two facts apart is the only disposition the evidence supports.

## 8. Rejected dispositions (and why)

- **A applied whole (collapse everything onto `substrate.types`):** REJECTED —
  breaks all construction sites, the L4 bridge contract, and the tests (§6). The
  observation model is not equivalent to the canonical one.
- **B (absorb/replace the canonical `substrate/ontology` primitives with v1):**
  REJECTED — inverts the dependency; the canonical home is `substrate.types` and
  `substrate/ontology/primitives.py` already re-exports it. Promoting the divergent
  v1 dataclass to canonical would regress P2 type-coherence.
- **C applied whole (keep the file intact, just rename/move it):** REJECTED as
  incomplete — it would carry the two duplicate enums into the new home, leaving
  the metamodel still forked (Gate-11/type-coherence debt persists). The enums
  must repoint; only then is C right for the remainder.
- **Do nothing / keep frozen:** REJECTED — it is the last competitor and carries a
  `2026-12-31` sunset in `canonical_types.py`; convergence is already owed.

## 9. Owner rulings required (do not decide silently)

1. **Split vs keep-whole.** Confirm disposition **D** (repoint enums + rehome the
   perception dataclasses) vs C-whole (rename/move intact, leave the enum
   duplication). Recon supports **D**; owner confirms.
2. **New home for the perception model.** Choose the destination dir/name for the
   surviving dataclasses:
   - (i) `substrate/understanding/perception/decomposition_model.py`
   - (ii) `substrate/understanding/decomposition/primitive_decomposition.py` (new pkg)
   - (iii) keep the filename, move it out of `ontology/` into `perception/`
   Recon leans (i) or (iii) — co-locate with the orchestrator that constructs it.
   Owner rules the exact path/name.
3. **`_v1` suffix.** Decide whether the rehomed model keeps `_v1` (there is a
   parallel `interpretation_engine_v1`, `substrate_decomposer_v1`, `_gen_v1`
   naming family) or drops it. Naming-family consistency vs cleanliness — owner call.
4. **`canonical_types.py` LEGACY_DUPLICATES.** On execution, the `PrimitiveType` /
   `RelationshipType` entries for this module are removed (they stop existing);
   the `PrimitiveObservation` entry either moves to the new module path or is
   dropped if the v1 observation is renamed so it no longer homonym-clashes with
   the canonical one. Owner confirms the registry edit shape in the execution PR.

## 10. Proposed execution packet steps (SEPARATE PR — not started here)

Contingent on the §9 rulings. Sketch only:

1. In the new home (per ruling 2), define the perception model:
   `PrimitiveObservation`-perception (possibly renamed to avoid the homonym, per
   ruling 3), `PrimitiveRelationship`, `DecompositionResult`,
   `REQUIRED_PRIMITIVE_TYPES` — moved intact, behavior identical.
2. In that new module, import `PrimitiveType` / `RelationshipType` **from
   `substrate.types`** instead of redefining them.
3. Repoint the **10 runtime code importers** (importer #11 is a `canonical_types.py`
   registration entry, not a code import) + 7 test files to the new module path
   (enums now resolve from `substrate.types`; dataclasses from the new home).
4. Delete `substrate/understanding/ontology/primitive_decomposition_v1.py`
   (its only unique content — the dataclasses — has moved; its enums were dupes).
   No shim (consistent with #161).
5. Shrink Gate-13 `FROZEN_ONTOLOGY_COMPETITORS` **1 → 0** and remove the
   `FROZEN_ONTOLOGY_HOMES` entry for the old path; ratchet non-growth caps to 0.
   `substrate/understanding/ontology/` then contains only `__init__.py`
   (package-marker) — no metamodel fork remains.
6. Update `canonical_types.py` LEGACY_DUPLICATES per ruling 4.
7. Refresh `docs/audits/UMH_P3_ONTOLOGY_HOME_CONSOLIDATION.md` (mark the last
   competitor RESOLVED) and `.claude/rules/ontology-layers.md`.

## 11. Test / gate proof requirements (for the execution packet)

- All 13 pre-commit gates green.
- `check_type_divergence.py --registry-audit` green; the two enum homonyms **gone**
  from `LEGACY_DUPLICATES` (a real shrink, not a hidden move).
- `check_dependency_direction.py` clean — the new home must not import upward
  (perception model may depend on `substrate.types`, never on adapters/transports).
- `check_ontology_homes.py --all` green with `FROZEN_ONTOLOGY_COMPETITORS = 0`.
- pytest collection clean; the 7 v1 test files pass unchanged against the new path
  (v1 shape preserved — `observation_id`, `is_inferred`, `.to_dict()` intact).
- Behavior-equivalence proof: the perception model exposes the **same fields,
  same `.to_dict()` output, same `DecompositionResult.compute_coverage()`**; the
  enums resolve to the *canonical* `substrate.types` members (value-identical).
- Domain-bridge contract proof: `DomainBridge.bridge(observation)` still accepts
  the (moved) perception observation type.

## 12. Rollback

This plan PR: `git revert` the squash — it is a single doc file, zero code impact.
The eventual execution PR: `git revert` restores the v1 file, the 17 import sites
(10 runtime + 7 test), and the ledger entry; relocation/repoint only, no
schema/data change.

## 13. No-go list (permanent for both this plan and its execution packet)

- No new type system. No new ontology framework. No broad rewrite.
- No file moves / import changes / ledger changes / gate changes **in this plan PR**.
- Do **not** delete `primitive_decomposition_v1.py` in this PR.
- Do **not** collapse the observation/relationship/result dataclasses onto
  `substrate.types` — they are perception-specific and load-bearing.
- Do **not** promote the v1 dataclass to canonical (would regress P2 coherence).
- Preserve P0 fail-closed, P1 runtime/approval authority, P2 registry/risk
  vocabulary, P3 ontology-home gates.
- No P4/P5 work. `UMH_CANONICAL_RUNTIME_ROUTING` untouched.
- Do not start the execution packet after this plan — hold for owner approval on §9.

## Scope guard

This PR is **plan/doc only** — one new file
(`docs/audits/UMH_P3_PRIMITIVE_DECOMPOSITION_V1_MICROPLAN.md`). No `git mv`, no
import edits, no ledger change, no gate change, no behavior change. The separate
execution packet proceeds only after the §9 owner rulings.
