# Delta: Orchestrator E2E vs Ingestion Proof 1

> Date: 2026-05-12

---

## Contract-Shape Equivalence

| Artifact | Proof-1 Fields | Orchestrator Fields | Match? |
|----------|---------------|---------------------|--------|
| 01_perceive_signal | signal_id, source_path, content_sha256, content_length, timestamp_utc, perceive_duration_ms, entry_point_invoked | signal_id, source_path, **source_type** (new), content_sha256, content_length, timestamp_utc, perceive_duration_ms, entry_point_invoked | YES + 1 added field |
| 02_interpretation | signal_id, inferred_document_type, inferred_domains, confidence, structural_features, intent_candidates, interpret_duration_ms, entry_point_invoked | IDENTICAL | YES |
| 03_decomposition | decomposition_id, source_content_hash, observations, relationships, decomposition_confidence, unsupported_assumptions, missing_information, explicit_unknowns, primitive_type_coverage, decompose_duration_ms, signal_id, counts, entry_point_invoked | IDENTICAL | YES |
| 04_world_update | signal_id, entities_added, entities_updated, facts_written, conflicts_with_existing_state, map_duration_ms, entry_point_invoked | IDENTICAL | YES |
| 05_memory_write | signal_id, new_canonical_memory_entry_id, governance_decision, governance_scope, provenance_chain, confidence_score, timestamp_utc, persist_duration_ms, memories_jsonl_before, memories_jsonl_after | IDENTICAL | YES |
| 05_promotion_receipt | receipt_id, candidate_id, decision, reason, confidence, promoter, timestamp, rollback_reference | IDENTICAL | YES |
| 06_query_proof | signal_id, query_string, query_derivation, retrieval_method, retrieved_entries, new_entry_appears_in_results, new_entry_rank, total_entries_searched, query_duration_ms | IDENTICAL | YES |

**Verdict**: Contract shapes are equivalent. The orchestrator adds one field
(`source_type` in Signal) that proof-1 did not produce — this is additive,
not breaking. All other fields match 1:1 in name, type, and structure.

## Cycle Duration

| Metric | Proof-1 | Orchestrator | Delta |
|--------|---------|-------------|-------|
| Total cycle | 110.04ms | 6.98ms | -93.7% |
| Perceive | 0.37ms | ~0.1ms | Equivalent |
| Interpret | 0.15ms | ~0.1ms | Equivalent |
| Decompose | 16.51ms | ~1ms | Orchestrator's heuristic is lighter (no manual 6-observation construction) |
| Persist | 88.65ms | ~2ms | Proof-1 overhead was inline script import cost, not I/O |
| Query | 0.23ms | ~0.2ms | Equivalent |

The 15x improvement is infrastructure overhead reduction, not algorithmic.
Both paths hit the same contracts.

## What the Orchestrator Caught That Direct-Invocation Missed

1. **Automatic proof writing**: The orchestrator writes all 7 proof JSONs
   automatically via `_write_proofs()`. Proof-1 had to manually construct
   each JSON inline.

2. **Consistent error handling**: Any stage failure produces a structured
   `IngestionResult` with `verdict`, `failed_stage`, and `error_trace`.
   Proof-1 would have crashed with an unstructured traceback.

3. **Source abstraction**: The orchestrator never touches `Path.read_text()`
   directly — `LocalFileSource.read()` handles that. This means swapping
   to `GWSSource` later changes zero orchestrator code.

## Hidden Source-Specific Coupling Found

**None.** The contract classes (`PrimitiveObservation`, `DecompositionResult`,
`MemoryScopeAssignment`, etc.) have no hidden GWS dependencies. They are
pure data structures. The GWS coupling in `FullLiveIngestionSpine` is
entirely in its constructor and adapter wiring, not in the contracts it uses.

This confirms the substrate's universality claim for the contract layer.
The orchestrator layer (`FullLiveIngestionSpine`) was the bottleneck.

## memories.jsonl

| State | Count |
|-------|-------|
| Before proof-1 | 10 |
| After proof-1 | 11 |
| After orchestrator-e2e | 12 |
