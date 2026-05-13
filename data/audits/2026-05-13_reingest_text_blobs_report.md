# RE-INGEST-TEXT-BLOBS — Comparison Report

> Date: 2026-05-13
> Build: RE-INGEST-TEXT-BLOBS-V2
> Provider: cc_sdk (Opus 4.6 via Max subscription, $0 API cost)

## Source Re-Ingested

| Source | GWS ID | Text | Provider | Wall-clock | Result |
|--------|--------|------|----------|------------|--------|
| Email Sequence | doc-1aZiPZ0ijSvLQsL6 | 3,871 chars | cc_sdk | 86.0s | COMPLETE_CYCLE |

## Per-Source Before/After

### Email Sequence (doc-1aZiPZ0ijSvLQsL6)

**BEFORE** (FullLiveIngestionSpine, 2026-05-09, no LLM):

| # | Type | Label | Quality |
|---|------|-------|---------|
| 1 | resource | "I'd won the money game..." | TEXT_BLOB |
| 2 | goal | "If you want to see the system I built to escape..." | TEXT_BLOB |
| 3 | resource | "But because they found the cheat code to unlock..." | TEXT_BLOB |
| 4 | constraint | "Preview: The same programming that got you here..." | TEXT_BLOB |
| 5 | resource | "Body\nHave you ever played a video game..." | TEXT_BLOB |
| 6 | state | "(First name), there are only two types of people..." | TEXT_BLOB |
| 7 | time | "I spent 2 years building this system after burning..." | TEXT_BLOB |
| 8 | time | "I spent 2 years mapping these hidden levels..." | TEXT_BLOB |
| 9 | time | "They walk the same path every day." | TEXT_BLOB |
| 10 | time | "Here's what hit me at 22 after cashing in on crypto..." | TEXT_BLOB |

- 10 entries, all TEXT_BLOB
- Labels = raw sentences (no semantic extraction)
- 0 relationships, 0 projections, no authority_tier

**AFTER** (GenericIngestionOrchestrator + cc_sdk/Opus 4.6, 2026-05-13):

| # | Type | Label | Quality |
|---|------|-------|---------|
| 0 | state | NPC vs Player identity framework | STRUCTURED |
| 1 | signal | Post-success emptiness as buying trigger | STRUCTURED |
| 2 | resource | Game of Lyfe gamification system | STRUCTURED |
| 3 | constraint | 20 players per month capacity cap | STRUCTURED |
| 4 | action | Book a qualifying call CTA | STRUCTURED |
| 5 | state | Founder credibility through personal narrative | STRUCTURED |
| 6 | signal | Hidden levels progression framework in Email 2 | STRUCTURED |
| 7 | change | Shift from Email 1 identity disruption to Email 2 progression | STRUCTURED |
| 8 | goal | Escape the default life script | STRUCTURED |
| 9 | constraint | Qualification framing inverts sales dynamic | STRUCTURED |

Plus 3 business domain projections:
- [business:sales] Book a qualifying call CTA
- [business:sales] Escape the default life script
- [business:sales] Qualification framing inverts sales dynamic

- 13 entries (10 observations + 3 projections)
- 8 typed relationships (enables, produces, requires, constrains, follows, measures)
- 7 distinct primitive types
- Authority tier: T4_SUPPORTING
- All labels are semantic abstractions

## Aggregate Memory Store: Before vs After

| Metric | Before (2026-05-12 audit) | After (2026-05-13) |
|--------|--------------------------|-------------------|
| Total entries | 13 | 63 |
| STRUCTURED | 1 | 43 |
| PARTIAL | 2 | 2 |
| TEXT_BLOB | 10 | 10 (preserved) |
| Projections | 0 | 8 |
| Source documents | 3 | 6 |

Note: The 13→63 growth includes both this re-ingest (13 new entries)
and three canary runs from the cc_sdk fix phases (37 entries from
local-383cb7e6d4f9c847). The 10 original TEXT_BLOB entries are
preserved additively — no destructive removal.

## Provider Distribution

| Provider | Calls | Result |
|----------|-------|--------|
| cc_sdk (Opus 4.6) | 1 | STRUCTURED (86.0s, 8128 chars) |
| Fallthrough (non-cc_sdk) | 0 | — |

**Zero fallthrough.** cc_sdk served the entire batch.

## Quality Delta

| Dimension | Before (TEXT_BLOB) | After (STRUCTURED) |
|-----------|-------------------|-------------------|
| Label quality | Raw sentences | Semantic abstractions |
| Type accuracy | Dubious ("They walk..." = time) | Accurate ("20 players/month" = constraint) |
| Type diversity | 4 types (resource, goal, state, time) | 7 types (+signal, change, action) |
| Relationships | 0 | 8 (6 distinct types) |
| Domain projections | 0 | 3 (business:sales) |
| Evidence quality | None | Verbatim spans with source refs |
| Description quality | None (label = content) | Contextual explanations |
| Authority tier | None | T4_SUPPORTING |

## Legacy Entry Status

The 10 original TEXT_BLOB entries (mem-bf974e9f through mem-0b33152e)
are preserved in memories.jsonl. They coexist with the new STRUCTURED
entries. No destructive removal was performed per spec.

Future phase can mark originals as superseded via a metadata flag
without deleting them.
