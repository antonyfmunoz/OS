# Phase 0 — TEXT_BLOB Inventory + Source Recovery

> Date: 2026-05-13

## TEXT_BLOB Entries (10 total)

All 10 entries originate from the same GWS document:
- **Document:** "Antony Munoz Email Sequence"
- **GWS doc ID:** 1aZiPZ0ijSvLQsL6
- **Content hash:** 0c320243f7199d2f...
- **Decomposition ID:** decomp-3fb25a245288537b
- **Original ingestion:** 2026-05-09T23:52:33 UTC (via FullLiveIngestionSpine)
- **Source text length:** 3,871 chars
- **Re-ingest method:** LocalFileSource (cached at data/runtime/real_ingestion_bridge/doc-1aZiPZ0ijSvLQsL6_normalized.json)

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
- Primitive type assignments are dubious (marketing copy = "resource", "time")
- No relationships between entries
- No authority_tier (pre-tier feature)

## Source Recovery

### Source: Email Sequence (GWS doc-1aZiPZ0ijSvLQsL6)

**Status: RECOVERABLE (local cache)**

Full text cached at:
  data/runtime/real_ingestion_bridge/doc-1aZiPZ0ijSvLQsL6_normalized.json
  Field: full_text (3,871 chars)

Content: Email #1 marketing copy — "Retire By Treating Life Like A
Video Game" — Initiate Arena onboarding email sequence.

**Proposed authority_tier:** T4_SUPPORTING (working drafts /
marketing copy — not canonical specs)

### Re-ingest approach

Extract full_text from normalized JSON → write to temp file →
ingest via LocalFileSource(tier=T4_SUPPORTING) through
GenericIngestionOrchestrator.

The single source (3,871 chars) is well within the 120s cc_sdk
timeout — canary on similar-length fixture completed in 73.1s.
No CC_SDK_TIMEOUT_SECONDS override needed.

## Aggregate

- Total TEXT_BLOB entries: 10
- All from single source: 1 (GWS doc-1aZiPZ0ijSvLQsL6)
- Source recoverable: YES (local cache)
- Unrecoverable: 0
- Sources that might exceed 120s: 0 (3,871 chars, well under threshold)
