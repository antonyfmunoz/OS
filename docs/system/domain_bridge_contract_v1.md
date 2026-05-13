# Domain Bridge Contract v1

> Canonical contract for the ontology-to-domain projection layer.
> Date: 2026-05-12

## Architecture

UMH operates at the ontology layer (domain-agnostic substrate).
Domain bridges are plug-ins that produce projections from ontology
observations so domain consumers can query in their own primitive
vocabulary.

Pipeline position:
  perceive → interpret → decompose → **bridge** → map → persist → query_back

## DomainBridge protocol

```python
class DomainBridge(Protocol):
    @property
    def domain_id(self) -> str: ...
    def bridge(observation: PrimitiveObservation) -> DomainProjection | None: ...
    def describes() -> str: ...
```

- `domain_id`: unique string identifying the domain (e.g., "business")
- `bridge()`: returns None if the observation has no mapping in this domain
- `describes()`: human-readable description

## DomainProjection dataclass

Each projection is a separate memory entry, additive to the ontology
observation.

| Field | Type | Description |
|-------|------|-------------|
| `projection_id` | str | `proj-{uuid_hex[:12]}` |
| `domain_id` | str | Bridge's domain identifier |
| `domain_primitive_type` | str | Domain-specific type (e.g., business primitive ID) |
| `label` | str | `[{domain}:{subdomain}] {observation.label}` (≤80 chars) |
| `description` | str | Carried from observation |
| `properties` | dict | Domain-specific metadata |
| `ontology_observation_ref` | str | Back-reference to source observation_id |
| `confidence` | float | Carried from observation, bridge may modulate |
| `evidence` | str | Carried from observation |

## BridgeRegistry

```python
registry = BridgeRegistry()
registry.register(bridge)        # register a domain bridge
registry.get_all()               # list all registered bridges
registry.get_by_id("business")   # get specific bridge
```

Global instance: `runtime.domain_bridge.registry.default_registry`

## Registered domains

| Domain | Module | Mapping type | Status |
|--------|--------|-------------|--------|
| business | `runtime.domain_bridge.business` | Structural (keyword) | V1 active |
| creator | — | — | Future (CreatorOS) |
| life | — | — | Future (LYFEOS) |

## Business bridge V1 rules

V1 uses structural keyword matching only (no LLM dependency).

Mapping algorithm:
1. Check observation `primitive_type` is in bridgeable set
   (constraint, action, goal, state, resource)
2. Lowercase `label + description`
3. Match against keyword sets per business domain/primitive
4. Highest-scoring match wins
5. Confidence = min(observation.confidence, 0.70 + score * 0.05)

Bridgeable ontology types: constraint, action, goal, state, resource
Non-bridgeable (V1): change, signal, outcome, feedback, time

## Persist behavior

The persist stage writes:
- All ontology observations (N-of-N, from persist-all)
- All domain projections as separate memory entries
- Each projection tagged with `memory_type: "domain_projection"`
  and `domain_id` + `ontology_observation_ref`

## Quality rules

- Projection MUST back-reference a valid observation from the same
  ingestion (resolvable `ontology_observation_ref`)
- Projection label MUST be prefixed with `[domain:subdomain]`
- Projection confidence MUST NOT exceed source observation confidence
- Bridge MUST return None for non-matching observations (no forced maps)
