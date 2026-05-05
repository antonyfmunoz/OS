# AI Chat Archive Ingestion Plan

**Date**: 2026-05-03
**Status**: Planning artifact — no ingestion performed

---

## Purpose

Build a coherent user profile and second brain from every AI chat/message the user has created across tools. AI chats are the highest-priority ingestion source because they contain years of strategic evolution, architecture decisions, doctrine, product planning, personal philosophy, and implementation history that exists nowhere else.

---

## Sources

| Source | Location | Export Method | Volume Estimate |
|--------|----------|---------------|-----------------|
| ChatGPT conversations | chat.openai.com | Settings → Data controls → Export data (ZIP) | Hundreds of conversations |
| Claude conversations | claude.ai | Download conversation / export | Dozens to hundreds |
| Claude Code terminal logs | ~/.claude/projects/ on VPS | Direct file read (JSONL format) | Hundreds of sessions |
| Cursor chats | Local Cursor data directory | File system read / export | Dozens |
| Replit Agent chats | replit.com | Manual export or copy | Dozens |
| Local chat exports | Various local directories | File system scan | Variable |
| Project-specific AI logs | /opt/OS/data/, .claude/ dirs | Direct file read | Hundreds of files |
| Previous handoff reports | Various locations | File system scan | Dozens |
| Prompts and outputs | Scattered across tools | Aggregate from above sources | Thousands |
| Screenshots of AI chats | Camera roll, screenshot folders | File system + OCR | Variable |

---

## Ingestion Tiers

### Tier 1 — Critical (Ingest First)

1. Current ChatGPT conversation summaries / handoff reports
2. UMH/EOS architecture chats (Claude, Claude Code, ChatGPT)
3. /opt/OS phase reports (docs/system/phase*.md)
4. Product/company strategy chats
5. Personal brand / Lyfe Institute / Empyrean strategy chats
6. master_intention_lock.md and related strategy docs (this phase's output)

### Tier 2 — High (Ingest Second)

1. Claude Code session logs (~/.claude/projects/)
2. Cursor/Replit implementation chats
3. Old product build conversations
4. Offer/funnel/sales strategy chats
5. Brand identity and voice discussions
6. Pricing/positioning conversations

### Tier 3 — Complete (Ingest for Full Second Brain)

1. All remaining historical AI chats
2. Screenshots of AI conversations
3. Miscellaneous AI conversations (one-off questions, explorations)
4. Old/discarded project conversations
5. Experimental/exploratory prompts

---

## Extraction Targets

Every AI chat ingestion must attempt to extract:

| Target | Description |
|--------|-------------|
| Decisions | Explicit choices made by the user |
| Current doctrine | Rules, principles, constraints currently in force |
| Old/superseded doctrine | Rules that were once current but have been replaced |
| Company definitions | What each entity is, does, owns |
| Product definitions | What each product is, who it serves, how it works |
| Architecture laws | UMH/EOS invariants, hard rules, design principles |
| Roadmap phases | Phase definitions, sequencing, dependencies |
| Prompts | Reusable prompts, system prompts, templates |
| Implementation reports | What was built, how, what worked |
| Preferences | User preferences for tools, workflows, communication style |
| Values | Core beliefs, non-negotiables, philosophical positions |
| Writing style | Voice, tone, vocabulary, brand language |
| Mental models | Frameworks the user thinks with |
| Business strategy | Go-to-market, pricing, positioning, competitive analysis |
| Personal goals | Life goals, milestones, timelines |
| Constraints | Budget, time, resource, legal, technical constraints |
| Contradictions | Places where different chats say different things |
| Unresolved questions | Open questions that were never answered |

---

## Memory Statuses

Every extracted claim moves through a lifecycle:

| Status | Meaning |
|--------|---------|
| RAW | Extracted from source, not yet parsed or validated |
| PARSED | Structured into a typed claim with metadata |
| CANDIDATE | Proposed for inclusion in user profile or knowledge base |
| NEEDS_REVIEW | Flagged for human review — contradiction, ambiguity, or sensitivity |
| APPROVED | Human-reviewed and confirmed as accurate |
| PROMOTED | Integrated into active user profile or knowledge base |
| SUPERSEDED | Replaced by a newer explicit statement |
| CONTRADICTED | Conflicts with a more authoritative source |
| ARCHIVED | Retained for historical record but not active |

---

## Supersession Rules

These rules determine which source wins when claims conflict:

1. **Newer explicit user correction** beats older assistant summary
2. **User statement** beats assistant inference — always
3. **Implementation report** beats plan/spec when describing actual code
4. **master_intention_lock.md** beats older strategic docs until explicitly superseded
5. **Explicit "locked in" decisions** beat exploratory ideas
6. **Old pricing/product sequence** must not override current product map
7. **Current rule**: Initiate Arena first, Game of Lyfe second core product — do not reverse
8. **Direct quote from user** beats paraphrased summary
9. **Timestamped source** beats undated source
10. **Source with provenance** beats source without provenance
11. **Single-session context** does not override multi-session pattern unless explicitly stated

---

## Provenance Discipline

Every extracted claim must preserve:

| Field | Required? | Description |
|-------|-----------|-------------|
| source | YES | Platform and conversation identifier |
| timestamp | If available | When the statement was made |
| platform | YES | ChatGPT, Claude, Claude Code, Cursor, Replit, etc. |
| confidence | YES | How certain the extraction is (HIGH, MEDIUM, LOW) |
| direct_quote | If available | Exact user words if extractable |
| sensitivity | YES | Public, private, sensitive |
| current_or_superseded | YES | Whether this is still the user's position |
| user_statement_or_inference | YES | Whether the user said it or an assistant inferred it |
| user_approved | NO (default false) | Whether the user has explicitly confirmed this claim |

---

## Safety Rules

1. Do NOT auto-ingest secrets, API keys, passwords, or credentials
2. Do NOT auto-promote sensitive private data without review
3. Do NOT treat assistant speculation as user fact
4. Do NOT flatten evolving ideas into contradictions without timestamp/context
5. Do NOT merge claims from different time periods without noting the temporal gap
6. Do NOT assume consistency — the user's views evolve over time
7. Do NOT ingest raw file contents that may contain credentials (scan for patterns first)
8. Preserve full provenance chain — never strip source metadata
9. Flag contradictions for human review rather than auto-resolving
10. Distinguish between "user explicitly said X" and "assistant summarized user as saying X"

---

## Future Module

This ingestion plan will be implemented by:

**Personal Context Ingestion Engine / Instance Assimilation Engine**

This is a future UMH module (not yet built) that will:
1. Accept exports from all source platforms
2. Parse conversations into structured claims
3. Apply extraction targets and supersession rules
4. Route claims through the memory status lifecycle
5. Present candidates for human review
6. Promote approved claims to active user profile
7. Maintain provenance and audit trail
8. Detect contradictions and flag for resolution
9. Build coherent user instance profile over time

This module does NOT exist yet. This document is its specification seed.

**Phase 87B Foundation**: The `umh/ingestion/` advisory layer (Phase 87B) provides
the typed contracts this future module will build on: SourceClass.AI_ASSISTANT,
PlatformType.CHATGPT / PlatformType.CLAUDE, OnboardingTier.TIER_1_LOCAL_ARCHIVES,
MemoryPromotionPolicy.SUPERSESSION_CHECK, and the full review/permission/routing
pipeline. The ingestion plan aligns with the Raw Before Memory doctrine — no
raw-to-memory shortcut.
