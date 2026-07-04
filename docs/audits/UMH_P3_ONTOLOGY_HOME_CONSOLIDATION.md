# WP-P3 — Ontology-Home Consolidation

**Branch:** `fix/p3-ontology-home-consolidation`
**Base:** `85cf1206e` (main after WP-P3-001, WP-P3-004, read-side registry convergence)
**Risk class:** MEDIUM (adds a boundary gate + docs + a shrink-only ledger; **no domain-object relocation, no file moves/deletes, no code-behavior change**)

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
| `substrate/understanding/ontology/primitives.py` | L3 business-rule logic in an ontology dir | imports `substrate.state.context` (`:36`); stage-aware business vocab (hiring/ICP/paid-ads/BIS-stage); 5 live importers | **P3 domain-object eviction packet** → relocate to an L3 home |
| `substrate/understanding/ontology/primitive_decomposition_v1.py` | parallel L2 metamodel | redefines `PrimitiveType`/`RelationshipType`/`PrimitiveObservation` (`:17,:33,:47`) instead of importing `substrate.types`; 11 importers (perception pipeline) vs `substrate.ontology`'s 3 | **P3 metamodel dedup packet** → re-point to `substrate.types` |
| ~~`substrate/understanding/world_model/world_model.py`~~ | **RESOLVED (WP-P3 world-model sunset)** | Not a competitor — a distinct concern (domain-knowledge world model vs organism self-model). Resolved by **disambiguation, not relocation**: both `world_model.py` modules now carry reciprocal docstrings; it stays a classified home (`understanding-world-model`). Deprecation rejected — `context_builder` is a live consumer. Removed from ledger (3 → 2). | done |

**Ledger status:** 2 remaining frozen competitors (was 3). The world-model name-collision
was the first sunset — resolved by disambiguation because it was never a true
competitor and has a live consumer.

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

## Non-goals (Scope OUT)

No P4/P5, no projection/cockpit features, no domain-object relocation, no moving
Venture/BusinessInstance/Company/Department/Portfolio, no new registry/type
system/ontology framework, no new dependencies, no file moves/deletes,
`UMH_CANONICAL_RUNTIME_ROUTING` untouched, unrelated gate debt (node_modules noise)
left alone.

## Rollback

`git revert` the squash — additive gate + tests + doc + rule text; no code-behavior
change, no schema/data change. Revert fully restores prior state.
