# W0-001 Stale Assumption & Contradiction Register

**Date**: 2026-05-04
**Source**: Google Drive document ingestion (28 docs, 22,474 words)

---

## Stale Assumptions

These are claims/plans found in the documents that appear to be outdated
based on other evidence (CLAUDE.md, current codebase state, or newer documents).

| # | Assumption | Found In | Why Stale | Confidence |
|---|-----------|----------|-----------|------------|
| S1 | "Game of Lyfe" as active product with email sales funnel | Email Sequence (jeremy.ness) | Predates Initiate Arena rebrand. Current strategy is Initiate Arena first, Game of Lyfe after $10K/mo. | HIGH |
| S2 | LYFEOS is in active development (LYFEOS.net/login?access=beta) | LYFEOS doc | Domain/app exists but development is paused per CLAUDE.md ("Side: Lyfe Spectrum, LYFEOS/CreatorOS"). No recent activity. | HIGH |
| S3 | "Semi-retired at 24" positioning in email copy | Email Sequence | Antony turned 25 in April 2026. Also pre-revenue makes "semi-retired" positioning potentially misleading for current use. | HIGH |
| S4 | GoHighLevel as CRM tool | AI Tools | No integration exists in EOS. Tool was bookmarked but not adopted. Current system uses Neon + Discord + manual tracking. | MEDIUM |
| S5 | "We only take 20 players per month" (Game of Lyfe) | Email Sequence | No cohort has launched yet. This was aspirational copy, not operational reality. | HIGH |
| S6 | WHOP + Discord as delivery stack | Life Coaching doc | Decision was documented but not implemented. No WHOP integration exists in EOS currently. | MEDIUM |
| S7 | Automations document (empty) | Automations | Title suggests planned content about business automations. Never written. The actual automations live in EOS codebase, not this doc. | LOW |
| S8 | "30 DMs/day" outreach system | Hormozi conversation | Manual DM outreach was active. "Automated outreach system" was being built but "not yet working." Current state of outreach pipeline unclear. | MEDIUM |

## Contradictions

These are direct conflicts between documents or between documents and current reality.

| # | Contradiction | Source A | Source B | Resolution |
|---|--------------|----------|----------|------------|
| C1 | **"Systems Inventory"** title vs actual content | Doc title | Doc content | The document is actually "The Universal Short-Form Virality Bible" — a content creation manual, NOT a systems inventory. Title is completely misleading. |
| C2 | **Email sequence sells Game of Lyfe** vs current strategy **sells Initiate Arena** | Email Sequence | Coaching Philosophy, CLAUDE.md | Initiate Arena is the current offer. Game of Lyfe email copy is obsolete. The email sequence should not be reused without major rewrite. |
| C3 | **Empyrean Studios = agency brand** (empty doc) vs **Empyrean Creative LLC = active agency** (legal entity with client) | Empyrean Studios doc | Service Contract | Empyrean Creative LLC is the legal entity. "Empyrean Studios" is the brand name for the same entity. The brand doc is empty while the LLC is operational. |
| C4 | **Personal Brand doc says "governance-grade personal development ecosystem"** vs **Hormozi conversation says "stop building Stage 5 before Stage 1 works"** | Personal Brand doc | Untitled (Hormozi) | Not a logical contradiction — both are true. The Personal Brand doc describes the full vision; the Hormozi conversation correctly identifies that execution must start simple. Both inform strategy but at different time horizons. |
| C5 | **"Copy of Script Storytelling Structures"** (owned by Antony) vs **"Script Storytelling Structures"** (owned by personalbrandlaunch) | Two docs | Same content | Duplicate content — Antony made a copy of a shared doc. Only one should be referenced. The original (personalbrandlaunch) is the canonical source. |
| C6 | **UMH doc defines formal architecture** vs **EOS codebase implements different structure** | UMH doc | /opt/OS codebase | The UMH doc describes the aspirational architecture. The actual EOS codebase has evolved differently (cognitive_loop, agent_runtime, substrate). Both are "UMH" but at different abstraction levels. The doc is a north-star spec, not current implementation. |

## Temporal Ordering

Documents span from 2025-02 to 2026-05. Key evolution:

```
2025-02: Hunter Hoffman contract (first agency work)
2025-08: Brand docs created (AI Agents, Life Coaching, Content, etc.)
2025-09: Email sequence + SEMAX (Game of Lyfe era)
2025-10: Storytelling structures shared
2025-11: Systems Inventory (virality bible) written
2026-01: Business Template, Personal Curriculum, Coaching Frameworks
2026-02: Conglomerate Brands, Personal Brand, LYFEOS, CreatorOS, Coaching Philosophy
2026-03: Content strategy, AI Tools, Claude plugins reference, Hormozi conversation
2026-04: EntrepreneurOS notes, EOS dev specs, Untitled docs
2026-05: UMH spec (most recent, aligns with current EOS work)
```

The pivot from "Game of Lyfe" to "Initiate Arena" happened ~Jan-Feb 2026.
The pivot from "build everything" to "one offer first" was explicit in the Hormozi conversation (~Mar 2026).
