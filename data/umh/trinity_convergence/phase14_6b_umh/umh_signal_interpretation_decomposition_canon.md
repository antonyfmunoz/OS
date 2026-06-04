# UMH Signal Interpretation and Decomposition Canon

Phase: 14.6B-UMH
Status: DRAFT

## Signal Intake

All signals enter UMH via `SignalEnvelope` (defined in `substrate/types.py`). Every input -- Discord messages, API calls, ingested files, scheduled events -- is wrapped in a SignalEnvelope before processing.

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

## Decomposition

### Engine

`substrate/understanding/ontology/primitive_decomposition_v1.py`

Decomposition extracts structured PrimitiveObservation objects from interpreted input. It uses LLM extraction as the primary path with heuristic fallback for when all providers are down.

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

| Stage | Role |
|---|---|
| Perceive | Detect and ingest raw input from source |
| Interpret | Classify intent and extract structure |
| Decompose | Extract PrimitiveObservation objects |
| Bridge | Map ontology primitives to domain-typed projections |
| Map | Relate observations to existing knowledge graph |
| Persist | Write to canonical memory store (Neon-backed) |
| Query Back | Verify round-trip integrity |

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
