# UMH Universal Primitive Ontology

Phase: 14.6B-UMH
Status: DRAFT

## Overview

UMH operates at the ontology layer -- a domain-agnostic substrate that decomposes any input into universal primitives and typed relationships. Domain bridges produce domain-typed projections from these ontology observations.

## 10 Primitive Types

Defined in `substrate/types.py` as `PrimitiveType` enum:

| Primitive | Semantics |
|---|---|
| STATE | A snapshot of current conditions or values |
| CHANGE | A transition from one state to another |
| CONSTRAINT | A limitation, rule, or boundary on behavior |
| RESOURCE | An asset, capability, or input available for use |
| SIGNAL | An incoming stimulus requiring interpretation |
| ACTION | A deliberate step taken to achieve a goal |
| OUTCOME | The result of an action or process |
| FEEDBACK | Evaluative information about an outcome or process |
| GOAL | A desired end-state or target condition |
| TIME | A temporal marker, duration, deadline, or schedule |

## 10 Relationship Types

Defined in `substrate/types.py` as `RelationshipType` enum:

| Relationship | Semantics |
|---|---|
| CAUSES | X produces Y as a direct effect |
| CONSTRAINS | X limits or restricts Y |
| ENABLES | X makes Y possible |
| REQUIRES | X depends on Y existing |
| PRECEDES | X comes before Y in time |
| FOLLOWS | X comes after Y in time |
| PRODUCES | X generates Y as output |
| CONSUMES | X uses up Y as input |
| MEASURES | X quantifies or evaluates Y |
| CONFLICTS_WITH | X and Y are mutually incompatible |

## 8 Ontological Categories

Defined in `substrate/understanding/ontology/` for classifying observations at a higher abstraction:

| Category | Semantics |
|---|---|
| ENTITY | A distinct thing with identity |
| RELATION | A connection between entities |
| EVENT | A bounded occurrence in time |
| PROPERTY | An attribute of an entity |
| PROCESS | An ongoing series of actions |
| STATE | A condition at a point in time |
| CONSTRAINT | A rule governing behavior |
| BOUNDARY | A limit or edge of a domain |

## 14 Governance Laws

Defined in `substrate/ontology/laws.py`. These are the axiomatic rules governing how the substrate processes observations, enforces boundaries, and maintains coherence. They encode the non-negotiable architectural constraints (type coherence, instance context, projection boundary, architecture layers, deterministic-first, etc.) as machine-readable governance primitives.

## Decomposition Output

The decomposition stage extracts `PrimitiveObservation` objects from raw input. Each observation contains:

| Field | Type | Description |
|---|---|---|
| primitive_type | PrimitiveType | One of the 10 primitive types |
| label | str | Semantic name, max 80 chars, no markdown |
| description | str | Context beyond label, max 300 chars |
| evidence | str | Verbatim span from source material |
| relationships | list[TypedEdge] | Typed edges using RelationshipType enum |

## Domain Bridge Contract

Domain bridges transform ontology-level PrimitiveObservations into domain-typed projections. The substrate works regardless of which domains are registered. Each bridge:

1. Accepts PrimitiveObservation inputs
2. Maps primitives to domain-specific types
3. Produces domain-typed output for the projection layer
4. Registers at runtime via the bridge registry

See: `docs/system/domain_bridge_contract_v1.md`
