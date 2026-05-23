# Phase 0 — TEXT_BLOB Inventory + Source Recovery

> Date: 2026-05-12

## TEXT_BLOB Entries (10 total)

All 10 entries originate from the same GWS document:
- **Document:** "Antony Munoz Email Sequence"
- **GWS doc ID:** 1aZiPZ0ijSvLQsL6
- **Content hash:** 0c320243f7199d2f...
- **Decomposition ID:** decomp-3fb25a245288537b
- **Original ingestion:** 2026-05-09T23:52:33 UTC (pre-pipeline upgrade)
- **Ingestion method:** FullLiveIngestionSpine (sentence-level extraction)

| # | memory_id | primitive_type | label (first 60 chars) | authority_tier |
|---|-----------|---------------|----------------------|----------------|
| 1 | mem-bf974e9f | resource | "I'd won the money game..." | NONE |
| 2 | mem-4bf4f64d | goal | "If you want to see the system I built to escape..." | NONE |
| 3 | mem-cef137dc | resource | "But because they found the cheat code to unlock..." | NONE |
| 4 | mem-f9511ef2 | constraint | "Preview: The same programming that got you here..." | NONE |
| 5 | mem-2f4f5ca8 | resource | "Body\nHave you ever played a video game..." | NONE |
| 6 | mem-7f088ccd | state | "(First name), there are only two types of people..." | NONE |
| 7 | mem-53dd62f7 | time | "I spent 2 years building this system after burning..." | NONE |
| 8 | mem-81e1243c | time | "I spent 2 years mapping these hidden levels..." | NONE |
| 9 | mem-54b6aab1 | time | "They walk the same path every day." | NONE |
| 10 | mem-0b33152e | time | "Here's what hit me at 22 after cashing in on crypto..." | NONE |

### Why these are TEXT_BLOBs

- Label = content (raw sentence text, not semantic abstraction)
- No semantic description beyond the raw text
- Primitive type assignments are dubious (marketing copy classified
  as "resource", "time", "constraint")
- No relationships between entries
- No authority_tier (pre-tier feature)

## Source Recovery

### Source 1: Email Sequence (GWS doc-1aZiPZ0ijSvLQsL6)

**Status: RECOVERABLE (local cache)**

Full text cached at:
  data/runtime/real_ingestion_bridge/doc-1aZiPZ0ijSvLQsL6_normalized.json
  Field: full_text (3,871 chars)

Content: Email #1 marketing copy — "Retire By Treating Life Like A
Video Game" — Initiate Arena onboarding email sequence.

**Proposed authority_tier:** T4_SUPPORTING (supporting docs /
working drafts — this is marketing copy, not canonical specs)

### Also re-ingestable (PARTIAL entries)

| # | memory_id | Source | Status | Proposed tier |
|---|-----------|--------|--------|---------------|
| 12 | mem-6301934988 | /opt/OS/docs/system/runtime_domain_architecture_plan.md | RECOVERABLE | T2_ACTIVE |
| 13 | mem-11bec8e5 | GWS doc 1R2SFSES... (leverage principle SKILL.md) | GWS | T3_REFERENCE |

Entry 11 (cloud_palace.md) is already STRUCTURED — no re-ingest needed.

## Aggregate

- Total TEXT_BLOB entries: 10
- All from single source: 1
- Source recoverable: YES (local cache)
- PARTIAL entries also re-ingestable: 2 (local file + GWS doc)
- Unrecoverable: 0

## Re-ingest plan

1. **Email Sequence** → write full_text to temp file → LocalFileSource(tier=T4_SUPPORTING)
2. **runtime_domain_architecture_plan.md** → LocalFileSource(tier=T2_ACTIVE)
3. **GWS leverage principle SKILL.md** → need GWSSource or local cache check

All 10 TEXT_BLOB entries come from source #1. Re-ingesting that
single source through the upgraded pipeline (LLM decomposer +
persist-all + domain-bridge + authority-tier) replaces 10 shallow
sentence extractions with N structured ontology observations.
