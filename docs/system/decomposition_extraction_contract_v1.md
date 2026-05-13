# Decomposition Extraction Contract v1

> Canonical schema for decomposer output observations.
> Date: 2026-05-12

## Context

The `GenericIngestionOrchestrator._decompose()` stage transforms raw
document content into typed `PrimitiveObservation` and
`PrimitiveRelationship` instances (from
`core.ontology.primitive_decomposition_v1`).

This contract defines the quality bar each observation must meet.

## Observation schema

Each `PrimitiveObservation` must satisfy:

| Field | Contract | Example |
|-------|----------|---------|
| `observation_id` | `obs-{uuid_hex[:8]}` | `obs-0e040854` |
| `primitive_type` | Valid `PrimitiveType` enum value | `constraint` |
| `label` | Semantic name (≤80 chars). Human-readable summary of what was observed. NOT raw text. No markdown formatting. | `AI must translate questions to concerns before navigating rooms` |
| `description` | Semantic explanation (≤300 chars). Adds context beyond label. NOT a copy of label. | `AI agents must first translate user questions into concerns, then navigate to matching rooms, verify ownership via purpose line, and only then access core loci files.` |
| `confidence` | 0.0–1.0. Direct extraction: 0.85–0.95. Inferred: 0.70–0.85. | `0.90` |
| `source_reference` | `{source_path}:{locator}` — locator is line range, section name, or paragraph index | `cloud_palace.md:lines 39-48` |
| `evidence` | Verbatim span from source that supports this observation (≤300 chars). Quoted, not paraphrased. | `"1. Translate the user's question into a concern. 2. Open the matching room page."` |
| `is_inferred` | `true` if the observation was synthesized from multiple signals, `false` if directly stated | `false` |

### Label quality rules

- MUST be a semantic claim, not a raw text line
- MUST NOT include markdown formatting (`#`, `**`, backticks)
- MUST NOT be truncated mid-word
- MUST be self-contained (readable without the source document)
- SHOULD start with the subject of the observation

### Description quality rules

- MUST add information beyond the label (context, scope, mechanism)
- MUST NOT be a copy of the label
- MUST NOT be raw text from the document
- If the observation is a constraint: describe what it constrains and
  why
- If the observation is an action: describe the sequence and trigger

## Relationship schema

Each `PrimitiveRelationship` must satisfy:

| Field | Contract |
|-------|----------|
| `from_observation_id` | Valid observation_id from this decomposition |
| `to_observation_id` | Valid observation_id from this decomposition |
| `relationship_type` | Valid `RelationshipType` enum value |
| `confidence` | 0.0–1.0 |
| `description` | Why this relationship exists (≤200 chars) |

### Relationship quality rules

- MUST have a semantic basis (not hardcoded positional)
- `relationship_type` MUST reflect the actual semantic relationship
- The set of relationships SHOULD cover the main structural
  connections in the document (not just obs[0]→obs[1])
- Minimum: 1 relationship per 3 observations (when observations are
  conceptually related)

## Coverage expectations

- A document with 5+ sections SHOULD produce 4+ observations
- Observations SHOULD span at least 3 distinct `PrimitiveType` values
- Prescriptive content (must/never/always) SHOULD produce `constraint`
  observations
- Procedural content (steps, sequences) SHOULD produce `action`
  observations
- Declarative state (X is Y, X has Z) SHOULD produce `state`
  observations

## Graceful degradation

If LLM extraction fails, the decomposer falls back to heuristic
extraction. Heuristic output may not meet all quality rules above but
MUST still produce valid typed observations.
