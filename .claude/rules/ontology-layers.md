# Ontology / Metamodel Layer Law

UMH separates knowledge into four layers. Substrate defines the **rules of
worlds**, never the **contents of one world**. Mixing these layers is what lets
one projection's domain contaminate the universal platform.

## The four layers

| Layer | Meaning | Home |
|---|---|---|
| **L1 — External Operational Reality Model** | The real world the org operates in: external entities, real-world state, observed truth. | `substrate/reality_model/` (canonical + instance); `substrate/organism/reality_graph.py` (graph view — reflects, never initiates) |
| **L2 — UMH Platform Metamodel / substrate primitives** | The universal type system every projection reuses: Signal, Operation, WorkPacket, RiskClass, PrimitiveType, the ontology laws. | `substrate/types.py`, `substrate/ontology/` |
| **L3 — Projection Domain Models** | Application-specific domain objects and vocabulary (EOS Venture/BIS, CreatorOS content, LyfeOS life-domains). | `projections/<name>/`; `substrate/understanding/domains/<name>.py` bridges |
| **L4 — Semantic Grounding / bridge / entity resolution** | Maps external reality ↔ projection domain ↔ metamodel. | `substrate/understanding/domains/contract.py` (`DomainBridge`, `DomainProjection`), `registry.py` (`BridgeRegistry`), `substrate/reality_model/canonical_reality_write.py` (`CanonicalRealityWritePath`) |

Dependency direction: **L3 depends on L2 and L4; L2 depends on nothing above it.**
L2 (`substrate/ontology/`, `substrate/types.py`) must never import L3 domain
state or projection modules.

## The core question — ask before adding any class

> **Before adding a class to `substrate/types.py` or `substrate/ontology/`, ask:
> would a different projection model this differently? If yes, it is L3 and
> belongs in `projections/` or a domain bridge, not L2.**

Field-level version of the same question: a field like `stage_name`, `venture`,
`offer`, `icp`, `monthly_revenue`, or `north_star` is L3 EOS vocabulary. An
abstract org primitive (`Company`, `Department`, `Portfolio`) *may* live in L2,
but its EOS-specific fields are L3 contamination and must be relocated to a
projection — never added to the L2 shape.

## What is L3 contamination in L2 (blocked)

- A new domain-object class in `substrate/types.py` / `substrate/ontology/` whose
  fields carry projection-specific vocabulary (ICP / offer / venture / revenue /
  brand-stage semantics).
- `substrate/ontology/` importing `substrate/state/business/` (BIS instance
  state) or any `projections/` module.
- Instance/brand literals (`empyrean_creative`, `lyfe_institute`, product names)
  embedded in L2 query templates or domain dicts instead of loaded at runtime.

## What is acceptable (a mention, not a definition)

- A registry/contract that *names* a projection as a data entry
  (`ProjectionContract`, projection alias maps, domain-bridge docstrings).
- Runtime lookup of instance values (BIS profile, `get_ai_name()`), never a literal.

## Enforcement

Pre-commit hook enforces this: `scripts/check_ontology_layers.py`
(plus the sub-layer import rule in `scripts/check_dependency_direction.py`:
`substrate/ontology/` must not import `substrate/state/business/` or
`projections/`). Existing contamination is frozen in the gate's shrink-only
`LEGACY_ONTOLOGY_LEAKS` ledger and may only shrink, never grow. Relocation of
frozen items happens in later, guarded packets — not by editing the ledger to
hide a new leak.
