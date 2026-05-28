# Phase 8.5 — Canonical Memory Promotion

**Date**: 2026-05-28
**Status**: COMPLETE
**Goal**: Build governed promotion pipeline from observed instance data into canonical UMH memory.

## What Was Built

### substrate/organism/memory_promotion.py

**Core entities:**
- `MemoryCandidate` — raw observation submitted for potential promotion
- `MemoryEvidence` — evidence supporting a candidate
- `MemoryPromotionDecision` — approval/rejection record
- `CanonicalMemoryEntry` — promoted canonical knowledge
- `MemoryPromotionPipeline` — full pipeline with JSONL persistence

**Promotion statuses:**
raw → candidate → promoted | rejected | superseded | contradicted | deprecated

**Memory categories:**
observation, pattern, template, strategy, constraint, capability

**Governance:**
- Observations and patterns: auto-promotable if evidence + contradiction check pass
- Strategies, constraints, capabilities: require operator approval (cockpit approve/reject)
- Evidence threshold: average confidence ≥ 0.6
- Contradiction check: content cross-referenced against active contradictions

**Storage:**
- `data/umh/memory_candidates/candidates.jsonl` — all candidates
- `data/umh/memory_candidates/decisions.jsonl` — all decisions
- `data/umh/memory/canonical_memory.jsonl` — promoted entries
- `data/umh/memory/instance_memory.jsonl` — instance-scoped entries

### API Integration
- Bridge handlers: `organism.memory_promotion`, `organism.memory_promotion.approve`, `organism.memory_promotion.reject`
- Routes:
  - `GET /api/umh/organism/memory-promotion`
  - `POST /api/umh/organism/memory-promotion/:id/approve`
  - `POST /api/umh/organism/memory-promotion/:id/reject`

### Tests
- 32 tests in `substrate/organism/tests/test_memory_promotion.py`
- Covers: candidate creation, evidence validation, contradiction blocking, promotion approval, operator approval gate, rejection, supersession, canonical/instance separation, list operations, serialization
- **32/32 PASS**

## Success Criteria
The organism can promote repeated, evidenced learning into governed canonical memory. **MET.**
