# Phase 96.8BL — GWS to Canonical Substrate Ingestion

> Generated: 2026-05-09
> Executor: Developer Agent (Claude Code)
> Baseline commit: 10b441ed702837b16d52971161faa9a3a82d6f95

---

## Executive Summary

First validated end-to-end GWS-to-canonical-substrate ingestion with a focused
test suite proving every pipeline stage against real data.

One real Google Workspace document processed through the complete pipeline:
scan → bridge → decomposition → candidate generation → canonical/instance classification →
memory persistence → query validation → replay validation.

**18/18 tests pass. All real data. No fabricated evidence. No simulated outputs.**

---

## Source Document

| Field | Value |
|-------|-------|
| Title | Antony Munoz Email Sequence |
| File ID | 1aZiPZ0ijSvLQsL6SpVzwbug52khV5XN0kYBFnNXvKuY |
| Document ID | doc-1aZiPZ0ijSvLQsL6 |
| Words | 676 |
| Characters | 3,837 |
| Tabs | 2 (Email #1, Email #2) |
| Content Hash | 0c320243f7199d2f05cb42d6a08b8e395fa04319769741afc0f590f92f1953e9 |
| Canonical Record | data/canonical_source_records/w0_001/Antony_Munoz_Email_Sequence_1aZiPZ0i.json |
| Raw Extraction | data/drive_doc_ingestion_tab_aware/Antony_Munoz_Email_Sequence_1aZiPZ0i.json |

---

## Pipeline Modules

| Module | Path | Status |
|--------|------|--------|
| Scanner Bridge | `core/adapters/gws_scanner_bridge_v1.py` | WORKING (compiles, tested) |
| Decomposer | `core/adapters/substrate_decomposer_v1.py` | WORKING (compiles, tested) |
| Candidate Generator | `core/adapters/substrate_candidate_gen_v1.py` | WORKING (compiles, tested) |
| Memory Store | `core/memory/canonical_memory_store_v1.py` | WORKING (compiles, tested) |
| Ontology | `core/ontology/primitive_decomposition_v1.py` | WORKING (compiles, tested) |

---

## Pipeline Results

### Decomposition
| Metric | Value |
|--------|-------|
| Decomposition ID | decomp-3fb25a245288537b |
| Observations | 45 |
| Relationships | 29 |
| Primitive types covered | 9 of 10 |
| Overall confidence | 0.693 |

### Candidate Generation
| Metric | Value |
|--------|-------|
| Candidate Set ID | candset-9912eaa32809624f |
| Canonical candidates | 21 |
| Instance candidates | 24 |
| Skipped (low confidence) | 0 |
| Classified | 45 |

### Memory Store
| Metric | Value |
|--------|-------|
| Promoted canonical | 5 |
| Promoted instance | 5 |
| Total memories | 10 |
| All have governance receipts | YES |
| All have rollback references | YES |

### Query Validation
| Test | Result |
|------|--------|
| Exact memory lookup | PASS |
| Document lookup (10 memories) | PASS |
| Type lookup (canonical + instance) | PASS |

### Replay Validation
| Check | Result |
|-------|--------|
| Content hash stable | PASS |
| Decomposition ID stable | PASS |
| Observation count stable | PASS |
| Relationship count stable | PASS |
| Candidate set ID stable | PASS |
| Canonical count stable | PASS |
| Instance count stable | PASS |
| Observation IDs stable | PASS |
| Candidate IDs stable | PASS |

---

## Test Suite

**File:** `tests/test_gws_to_canonical_ingestion_v1.py`

| Test Class | Tests | Result |
|-----------|-------|--------|
| TestBridge | 4 | 4/4 PASS |
| TestDecomposition | 5 | 5/5 PASS |
| TestCandidateGeneration | 3 | 3/3 PASS |
| TestMemoryStore | 4 | 4/4 PASS |
| TestReplay | 1 | 1/1 PASS |
| TestNoFabricatedProof | 1 | 1/1 PASS |
| **Total** | **18** | **18/18 PASS** |

### What Tests Prove
- Bridge reads **real** scanner artifacts (not example data)
- IDs are deterministic (content-hash derived)
- Decomposition produces observations with confidence scores
- Candidate split produces both canonical and instance candidates
- Memory store supports append, query by ID/document/type
- Replay produces identical results (same IDs, hashes, counts)
- Runtime artifacts are generated, not hand-written

---

## Runtime Artifacts

| Artifact | Path |
|----------|------|
| Normalized document | `data/runtime/real_ingestion_bridge/doc-1aZiPZ0ijSvLQsL6_normalized.json` |
| Decomposition | `data/runtime/real_primitive_decomposition/doc-1aZiPZ0ijSvLQsL6_decomposition.json` |
| Candidates | `data/runtime/real_ingestion_candidates/doc-1aZiPZ0ijSvLQsL6_candidates.json` |
| Memories (JSONL) | `data/runtime/canonical_memory_store/memories.jsonl` |
| Promotion receipts (JSONL) | `data/runtime/canonical_memory_store/promotion_receipts.jsonl` |
| Memory index | `data/runtime/canonical_memory_store/index.json` |
| Promotion summary | `data/runtime/canonical_memory_store/promotion_summary.json` |
| Query validation proof | `data/runtime/real_memory_query_proofs/query_validation_proof.json` |
| Replay validation proof | `data/runtime/real_ingestion_replay_proofs/replay_validation_proof.json` |

---

## !ingest-real-doc Command

**Status: DEFERRED**

The pipeline is stable and deterministic. Bot command wiring was deferred because:
1. Batch ingestion (all 22+ docs) is the next priority, not single-doc commands
2. The pipeline runs as a Python script, not yet as a handler function
3. Wiring a command before batch support would create a one-doc-at-a-time bottleneck

Command wiring will happen in 96.8BM alongside batch ingestion.

---

## What Became Real

| Component | Before 96.8BL | After 96.8BL |
|-----------|--------------|-------------|
| Ingestion bridge | Working (prior session) | **Tested** (18/18 pass) |
| Decomposition | Working (prior session) | **Tested** (5 tests) |
| Candidate generation | Working (prior session) | **Tested** (3 tests) |
| Memory store | Working (prior session) | **Tested** (4 tests) |
| Replay determinism | Proven (prior session) | **Tested** (1 test) |
| Anti-fabrication check | — | **Tested** (1 test) |

## What Remains Partial

| Component | Gap |
|-----------|-----|
| Batch ingestion | Only 1 of 22+ docs processed |
| Bot command integration | Pipeline not wired to !commands |
| Neon memory migration | JSONL only, no Neon yet |

## What Remains Simulated

Nothing. All proofs come from real scanner output, real decomposition,
real candidate generation, real memory promotion.

---

## Next Phase

**96.8BM — CANONICAL_MEMORY_STORE_AND_RECONCILIATION_ENGINE**

1. Batch process all 22+ real documents
2. Migrate JSONL → Neon
3. Wire !ingest-real-doc and !query-memory commands
4. Memory reconciliation for re-ingested documents
