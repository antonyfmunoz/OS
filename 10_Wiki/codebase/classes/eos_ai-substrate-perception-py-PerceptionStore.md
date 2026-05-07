---
type: codebase-class
file: eos_ai/substrate/perception.py
line: 172
generated: 2026-05-07
---

# PerceptionStore

**File:** [[eos_ai-substrate-perception-py]] | **Line:** 172

Durable, thread-safe, singleton store for PerceptionRecord objects.

Dual-layer: in-memory dict + substrate.storage (Neon-backed, JSON fallback).
Best-effort persistence — flush failures log and the in-memory state
remains correct.
...

## Methods

- [[eos_ai-substrate-perception-py-PerceptionStore-__init__]]`() → None` — 
- [[eos_ai-substrate-perception-py-PerceptionStore-_load]]`() → None` — 
- [[eos_ai-substrate-perception-py-PerceptionStore-_flush]]`() → None` — 
- [[eos_ai-substrate-perception-py-PerceptionStore-_prune_if_needed]]`() → None` — Remove oldest INFO records first if store exceeds _MAX_RECORDS.
- [[eos_ai-substrate-perception-py-PerceptionStore-get]]`(record_id) → Optional[PerceptionRecord]` — Return a record by ID, or None.
- [[eos_ai-substrate-perception-py-PerceptionStore-put]]`(record) → None` — Insert or update a record. Flushes to storage.
- [[eos_ai-substrate-perception-py-PerceptionStore-all]]`() → list[PerceptionRecord]` — Return all records, sorted by observed_at descending (newest first).
- [[eos_ai-substrate-perception-py-PerceptionStore-by_source]]`(source) → list[PerceptionRecord]` — Return records from the given source, sorted by observed_at descending.
- [[eos_ai-substrate-perception-py-PerceptionStore-by_severity]]`(severity) → list[PerceptionRecord]` — Return records with the given severity, sorted by observed_at descending.
- [[eos_ai-substrate-perception-py-PerceptionStore-recent]]`(limit) → list[PerceptionRecord]` — Return the most recent N records, sorted by observed_at descending.
- [[eos_ai-substrate-perception-py-PerceptionStore-has_fingerprint]]`(fingerprint) → bool` — Check if a record with this fingerprint already exists (for dedup).
- [[eos_ai-substrate-perception-py-PerceptionStore-default]]`() → 'PerceptionStore'` — Return the process-level singleton, creating it on first call.
- [[eos_ai-substrate-perception-py-PerceptionStore-reset_default_for_tests]]`() → None` — Tear down the singleton so the next call to default() creates a fresh instance.
