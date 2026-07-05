# WP-P3 — Ontology-Home Consolidation

> **HISTORICAL — PR #158 packet document.** This describes the *boundary-gate*
> packet (`e8538890a`) that froze the ontology-home map. Its packet-local scope
> language below ("no file moves/deletes", "does not move
> Venture/BusinessInstance/…", the frozen-competitor ambiguities) was true **for
> #158 only**. Later P3 packets deliberately DID relocate files — #161 moved the
> business primitives to `substrate/state/business/primitives.py`, and #163 moved
> `primitive_decomposition_v1.py` to `substrate/understanding/perception/` and
> repointed its enums to `substrate.types`. The competitor table below is kept
> current (rows marked RESOLVED as each landed), but for the **current P3
> final-state truth** read `docs/audits/UMH_P3_ONTOLOGY_HOME_CLOSEOUT.md`, not the
> scope/non-goals sections here.

**Branch:** `fix/p3-ontology-home-consolidation`
**Base:** `85cf1206e` (main after WP-P3-001, WP-P3-004, read-side registry convergence)
**Risk class:** MEDIUM (adds a boundary gate + docs + a shrink-only ledger; **no domain-object relocation, no file moves/deletes, no code-behavior change** — *for #158; see the historical banner above*)

## Purpose

This is a **boundary-convergence** packet, not a "move everything" packet. It makes
the ontology / reality / domain / grounding / world-model **homes** unambiguous and
enforceable so future domain-object movement is safe. It does **not** move
`Venture`, `BusinessInstance`, `Company`, `Department`, or `Portfolio`, and it does
**not** resolve the directional dedup decisions it surfaces — those are reported for
an owner ruling and frozen in a shrink-only ledger.

The four ontology layers (see `.claude/rules/ontology-layers.md`):
- **L1** External Operational Reality Model
- **L2** UMH Platform Metamodel
- **L3** Projection Domain Models
- **L4** Semantic Grounding / Domain Bridge / Entity Resolution

## Canonical ontology-home table

| Concern | Layer | Canonical owner | Evidence |
|---|---|---|---|
| External / current reality (Canonical + Instance) | L1 | `substrate/reality_model/` | `__init__` "dual Canonical/Instance reality"; `canonical.py`, `instance.py`, `simulation.py`, `reality_intelligence.py` (read-only), `reality_query.py` |
| Cross-domain reality graph (reflects, never initiates) | L1 (read model) | `substrate/organism/reality_graph.py` | docstring "reflects mutations after they happen — never initiates" (`:10-12`) |
| Metamodel laws / primitives / relationships | L2 | `substrate/ontology/` | `laws.py` (`Law`, `LawRegistry`, 14 laws), `primitives.py`/`relationships.py` re-export `substrate.types` |
| Canonical type system | L2 | `substrate/types.py` | (existing L2 gate surface) |
| Governed reality write path | L4 (write) | `substrate/reality_model/canonical_reality_write.py` | "governed entry point for non-execution observations" (`:40` `CanonicalRealityWritePath`) |
| Reality mutation contracts | L4 (contract) | `substrate/reality_model/reality_mutation.py` | `RealityMutation`, `MutationSource` |
| Semantic grounding / domain bridges / entity resolution | L4 | `substrate/understanding/domains/` | `contract.py` (`DomainBridge`/`DomainProjection`), `registry.py` (`BridgeRegistry`), `business.py`/`creator.py`/`life.py` bridges |
| Projection domain objects | L3 | `projections/`, `understanding/domains/<name>.py` bridges | reference only — NOT edited here |
| EOS business instance state (BIS) | L3 (state) | `substrate/state/business/` (`business_instance.py`, `venture_knowledge.py`) | `BusinessInstance`, `Venture` — reference only; mutated only via their own managers |

## Distinct concerns — same-name, DO NOT MERGE

| Module | Importers | Concern | Why not a competitor |
|---|---|---|---|
| `substrate/organism/world_model.py` | 13 | organism **self-model** ("organism knowing ITSELF") | docstring explicitly "NOT the understanding/world_model"; different concern |
| `substrate/understanding/world_model/world_model.py` | 1 live (`context_builder`) | domain-knowledge world model (`WorldModelEntry`, `CanonicalWorldModel`) | different concern; low-use deprecation *candidate* (not dead — frozen) |
| `substrate/organism/domain_registry.py` | 5 | **execution-policy** registry (allowed actions / proofs / approval gates / risk per WorkPacket domain) | registers execution governance, NOT ontology/domain models |
| `substrate/understanding/domains/registry.py` (`BridgeRegistry`) | — | registers L4 **bridges** | registers bridges, not execution domains — the two just share the word "registry" |
| `substrate/ontology/domains/` | — | compat **re-export shim** (`# noqa: F401`) of the L4 home | alias, not a second L4 home |

## Frozen ontology-home competitors / leaks (shrink-only ledger)

These are real ambiguities that this packet **freezes but does not resolve**
(resolution = domain-object move / type dedup, out of scope). Enforced shrink-only
by `FROZEN_ONTOLOGY_COMPETITORS` in `scripts/check_ontology_homes.py` +
`tests/test_ontology_home_map.py`. Each has owner=developer.

| Module | Disposition | Rationale | Sunset / follow-on |
|---|---|---|---|
| ~~`substrate/understanding/ontology/primitives.py`~~ | **RESOLVED (WP-P3 primitives relocation)** | L3 business-rule logic (stage-aware business vocab: hiring/ICP/paid-ads/BIS-stage) that imported `substrate.state.context`. Resolved by **relocation, not disambiguation**: `git mv` whole to `substrate/state/business/primitives.py` — co-located with its `BusinessInstanceManager` dependency, downward-legal (substrate→substrate). The 6 lazy imports (5 consumers) + the `new-primitive` skill re-pointed; no shim. Removed from both ledgers (homes 27→26, competitors 2→1). | done |
| ~~`substrate/understanding/ontology/primitive_decomposition_v1.py`~~ | **RESOLVED (WP-P3 rehome)** | Was a parallel L2 metamodel (redefined `PrimitiveType`/`RelationshipType` instead of importing `substrate.types`) wrapping a perception/decomposition data model. Resolved by a **split**: the two duplicate enums were **repointed to `substrate.types`** (fork removed, `LEGACY_DUPLICATES` enum entries dropped), and the surviving perception dataclasses (`PrimitiveObservation` v1 / `PrimitiveRelationship` / `DecompositionResult` / `REQUIRED_PRIMITIVE_TYPES`) were **`git mv`'d intact** to `substrate/understanding/perception/primitive_decomposition_v1.py` — their honest perception home, co-located with the orchestrator that constructs them. 10 runtime + 7 test importers repointed; no shim; no class rename. Removed from both ledgers (homes 26→25, competitors 1→0). | done |
| ~~`substrate/understanding/world_model/world_model.py`~~ | **RESOLVED (WP-P3 world-model sunset)** | Not a competitor — a distinct concern (domain-knowledge world model vs organism self-model). Resolved by **disambiguation, not relocation**: both `world_model.py` modules now carry reciprocal docstrings; it stays a classified home (`understanding-world-model`). Deprecation rejected — `context_builder` is a live consumer. Removed from ledger (3 → 2). | done |

**Ledger status:** **0 remaining frozen competitors** (was 3). All three resolved:
the world-model name-collision (disambiguation), the primitives.py L3 leak
(relocation to `substrate/state/business/`), and the
`primitive_decomposition_v1.py` parallel-metamodel (split — enums repointed to
`substrate.types`, perception model rehomed to `substrate/understanding/perception/`).
`substrate/understanding/ontology/` now contains only `__init__.py` — no metamodel
fork remains in an ontology dir.

## Ambiguous cases — REPORTED, not silently decided

Per the packet constraint ("report any ambiguous cases instead of deciding silently"):

1. **`substrate/organism/domain_registry.py` layer.** Straddles L2 (carries type/law-adjacent metadata: allowed_actions, risk_class, proof) and L4 (routes `IntentClassifier` domains via `_CLASSIFIER_TO_REGISTRY`). Classified here as an execution-policy registry (distinct concern), but a single L# assignment needs an owner ruling.
2. **`primitive_decomposition_v1.py` canonical status.** It is the *more-used* metamodel (11 vs 3) yet duplicates `substrate.types`. Whether it should **absorb** `substrate/ontology` or be **collapsed onto** `substrate.types` is a directional call not derivable from importer counts alone. Frozen as parallel-L2; ruling deferred.
3. **`business_instance.py` / `venture_knowledge.py` mutability.** They are L3 instance **state** with real mutation methods (`save_bis`, `advance_stage`, `create_from_wizard`) and JSON persistence — writable via their own managers. "Reference point, not an edit target" holds only for *this* packet, not as an immutability claim.
4. **`understanding/world_model/world_model.py` deprecation.** Has 1 genuine runtime importer (`context_builder`); "deprecated" is a candidacy by importer-count, not dead code. Confirm the dependency can be repointed before removal.

## Enforcement

- **Existing** `check_ontology_layers.py` (Gate 11) already keeps L3 CONTENTS out of the L2 SURFACE (`substrate/types.py`, `substrate/ontology/`) — verified it fires on new L3 fields and projection/BIS imports added to `substrate/ontology/`.
- **New** `check_ontology_homes.py` (Gate 13) keeps the ontology-home SET unambiguous:
  1. no new unclassified `.py` under the guarded home dirs (frozen in `FROZEN_ONTOLOGY_HOMES`, shrink-only);
  2. no new competing ontology/domain-model registry (`OntologyRegistry` / `DomainModelRegistry` / `MetamodelRegistry` / a second `DomainRegistry`) outside `substrate/organism/domain_registry.py` — ordinary registries are not flagged.
- **New** `tests/test_ontology_home_map.py` proves L2-only ontology, L1-oriented reality_model, L4 domains, shrink-only ledgers, and the negative controls.
- `.claude/rules/ontology-layers.md` updated with the home table (not weakened).

## Non-goals (Scope OUT) — *for PR #158 only (see historical banner)*

No P4/P5, no projection/cockpit features, no domain-object relocation, no moving
Venture/BusinessInstance/Company/Department/Portfolio, no new registry/type
system/ontology framework, no new dependencies, no file moves/deletes,
`UMH_CANONICAL_RUNTIME_ROUTING` untouched, unrelated gate debt (node_modules noise)
left alone. — **These were #158's non-goals. Later P3 packets (#161, #163) did
relocate files by design; `Venture`/`BusinessInstance`/etc. remain unmoved.**

## Rollback

`git revert` the squash — additive gate + tests + doc + rule text; no code-behavior
change, no schema/data change. Revert fully restores prior state.
