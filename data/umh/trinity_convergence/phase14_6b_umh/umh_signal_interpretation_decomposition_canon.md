# UMH Signal Interpretation and Decomposition Canon

Phase: 14.6B-UMH (revised 14.6F)
Status: DRAFT
Revised in Phase 14.6F to align with 18 ratified P0 decisions (2026-06-04).

**Reality Model Input Layer (DEC-146C-001, RATIFIED 2026-06-04):** Signal interpretation and decomposition is the reality model's primary input layer. Signals are reality-model observations -- the mechanism through which the Universal Meta Harness (DEC-146B-UMH-001) perceives and updates its reality-isomorphic approximation of reality. Decomposition feeds the reality model, not just execution. Every signal, once interpreted and decomposed, enriches one or more of the 12 reality layers (physical, digital, cognitive, biological, social, economic, symbolic, operational, software, memory, source-truth, OS-level). Without this input layer, the reality model is static and blind.

**Indivisible Stage 1 (DEC-146C-003):** Signal processing is part of the Reality Model component of the indivisible Stage 1 organism. Signals that cannot update the reality model, or a reality model that cannot receive signals, violate the indivisibility constraint.

## Signal Intake

All signals enter UMH via `SignalEnvelope` (defined in `substrate/types.py`). Every input -- Discord messages, API calls, ingested files, scheduled events -- is wrapped in a SignalEnvelope before processing. Signals are the observation layer of the reality model. Through the unified execution path (DEC-146B-UMH-003, RATIFIED), all signals route: Substrate -> SignalRouter -> Spine.

The envelope carries:
- Source identifier and transport origin
- Raw content payload
- Timestamp and priority metadata
- Routing hints for the control plane

## Intent Classification

Intent is classified at two levels:

### Spine-Level (substrate/execution/spine.py)

7 regex patterns provide fast deterministic classification before any LLM call:
- Command patterns (explicit directives)
- Query patterns (information requests)
- Status patterns (state inquiries)
- Approval patterns (governance responses)
- Feedback patterns (quality signals)
- Scheduling patterns (temporal intents)
- Conversational patterns (general dialogue)

### Gateway-Level (substrate/control_plane/runtime/gateway.py)

12 intent categories for refined routing after initial classification:
- Strategic, operational, analytical, creative, administrative, technical, social, governance, learning, monitoring, emergency, unknown

The deterministic layer always produces a usable classification. LLM refinement improves accuracy when available but is never required.

## Decomposition (Reality Model Enrichment)

### Engine

`substrate/understanding/ontology/primitive_decomposition_v1.py`

Decomposition is the critical bridge between raw perception and reality-model enrichment. It extracts structured PrimitiveObservation objects from interpreted input -- converting raw signals into reality-model observations that update UMH's isomorphic approximation of reality across the 12 layers (DEC-146C-001). Each decomposed observation maps to at least one reality layer; unmappable observations indicate either a misclassified signal or a gap in the reality model's layer coverage. It uses LLM extraction as the primary path with heuristic fallback for when all providers are down.

### LLM Extraction Path

1. Constructs a prompt with the interpreted signal and ontology schema
2. Calls `model_router.call_with_fallback()` for extraction
3. Parses structured output into PrimitiveObservation objects
4. Validates against the ontology schema (primitive types, relationship types)

### Heuristic Fallback Path

When LLM extraction fails or is unavailable:
1. Regex-based entity extraction
2. Keyword-to-primitive-type mapping
3. Co-occurrence-based relationship inference
4. Produces valid but lower-fidelity PrimitiveObservation objects

### Output Schema

Each PrimitiveObservation contains:

| Field | Constraint |
|---|---|
| primitive_type | PrimitiveType enum (10 values) |
| label | Semantic name, max 80 chars, no markdown |
| description | Context beyond label, max 300 chars |
| evidence | Verbatim span from source |
| relationships | Typed edges using RelationshipType enum (10 values) |

See: `docs/system/decomposition_extraction_contract_v1.md`

## Canonical Ingestion Pipeline

The full pipeline from raw source to queryable knowledge:

```
perceive -> interpret -> decompose -> bridge -> map -> persist -> query_back
```

| Stage | Role | Reality Model Function |
|---|---|---|
| Perceive | Detect and ingest raw input from source | Observation intake |
| Interpret | Classify intent and extract structure | Signal classification |
| Decompose | Extract PrimitiveObservation objects | Reality model enrichment (DEC-146C-001) |
| Bridge | Map ontology primitives to domain-typed projections | Layer-specific projection |
| Map | Relate observations to existing knowledge graph | Reality model integration |
| Persist | Write to canonical memory store (Neon-backed) | Reality model persistence |
| Query Back | Verify round-trip integrity | Isomorphism verification |

Canonical path: `substrate.execution.ingestion`
Legacy compatibility: `runtime.ingestion`

## Ingestion Sources

| Source | Adapter | Input Type |
|---|---|---|
| Local files | `adapters/data_source_adapters/local_file_source.py` | Files on disk |
| Google Workspace | `adapters/data_source_adapters/gws_source.py` | Docs, Sheets, Drive |
| Conversation | Signal transport (Discord, API) | Live dialogue |
| GitHub | Webhook transport | Commits, PRs, issues |

Proofs of ingestion pipeline operation: `data/runtime/canonical_memory_store/proofs/`

## Materialization Principle Impact (DEC-146C-002)

Decomposition must also detect gap signals -- observations that indicate missing knowledge, resources, or capability. When a signal decomposes into a gap observation, the materialization principle activates: the gap is typed (unavailable, under-resourced, unproven, not-yet-acquired, time-bound, impossible, illegal, unsafe) and routed to the appropriate acquisition path rather than being treated as terminal failure. The decomposition layer is where UMH first distinguishes "I don't know this yet" from "this cannot be done."
