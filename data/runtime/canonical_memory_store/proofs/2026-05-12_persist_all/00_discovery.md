# Phase 0 Discovery — Persist All Observations

> Date: 2026-05-12

## Current persist behavior

**Type: 1-of-N funnel.** The decomposer produces N observations per
document, but `_persist()` writes only the single highest-confidence
observation.

Gate location: `orchestrator.py:794`
```python
best_obs = max(decomp.observations, key=lambda o: o.confidence)
```

Everything after this line operates on `best_obs` only:
- One `memory_entry` dict (L796-830)
- One `memories.jsonl` append (L835)
- One `promotion_receipt` (L840-860)
- One `index.json` entry (L870)
- One `promotion_summary.json` write (L880)

## Capture rate

Typical decomposition produces 4-6 observations per document.
Only 1 is persisted → **~17-25% capture rate.**

The 13 entries in `memories.jsonl` represent 13 single-best picks
from their respective ingestions. The observations that didn't win
the confidence race are silently discarded.

## Downstream consumer analysis

### MemoryWrite dataclass (L117-144)
- `new_canonical_memory_entry_id: str` — singular, assumes one entry
- `memories_jsonl_before: int` / `memories_jsonl_after: int` — line counts
- **Needs:** `memory_ids_written: list[str]`, `entries_written: int`

### _query_back() (L900+)
- Uses `mem_write.new_canonical_memory_entry_id` to locate the new entry
- Reads `memories.jsonl`, finds the entry, computes rank
- **Needs:** update to handle multiple entries (report on all or first)

### index.json
- `entries` dict already supports multiple entries per source document
- `by_document` already maps doc IDs to lists of entry IDs
- **No structural change needed**

### memories.jsonl
- JSONL format, one entry per line, no unique-per-doc constraint
- **No structural change needed**

### test_generic_ingestion_orchestrator.py
- L126: `assert result.memory_write.memories_jsonl_after == 2`
  Currently expects exactly 1 new entry (before=1, after=2)
- **Needs:** update to `memories_jsonl_after >= memories_jsonl_before + 1`

## What changes

1. `MemoryWrite` — add `memory_ids_written: list[str]` and `entries_written: int`
2. `_persist()` — loop over ALL `decomp.observations`, write N entries
3. `_query_back()` — adapt to multiple entry IDs
4. Existing test assertions — relax count expectations

## What does NOT change

- Decomposer logic (Phase B, already shipped)
- Observation schema (PrimitiveObservation unchanged)
- index.json structure (already multi-entry capable)
- memories.jsonl format (already JSONL, no constraint)
- Promotion receipt schema (one receipt per entry, same shape)

## Risk class

**MEDIUM** — modifying existing persist method, changing dataclass shape.
No schema migration. No external service dependency. Fully reversible
by reverting the commit.
