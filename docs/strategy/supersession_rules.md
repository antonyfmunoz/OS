# Supersession Rules

**Date**: 2026-05-03
**Status**: Current — governs all claim resolution and doctrine updates

---

## Purpose

When two sources say different things, these rules determine which source wins. This is critical for AI chat ingestion, strategy doc conflicts, and doctrine evolution.

---

## Rules (Ordered by Authority)

### 1. Explicit User Correction Beats Assistant Summary
If the user explicitly says "no, it's X" and an older assistant summary says "Y", the user correction wins regardless of age.

### 2. User Statement Beats Assistant Inference — Always
"The user said X" beats "Based on the conversation, it seems like the user thinks X." Direct user statements are always more authoritative than assistant interpretations.

### 3. Implementation Report Beats Plan/Spec for Describing Actual Code
If a phase report says "we built X with Y properties" and an older plan says "we will build X with Z properties", the report of what was actually built wins for describing current state.

### 4. Master Intention Lock Beats Older Strategic Docs
Until a newer Master Intention Lock is created, `docs/strategy/master_intention_lock.md` is the canonical strategic reference. All older strategy docs, handoff reports, and AI chat summaries are subordinate.

### 5. Explicit "Locked In" Decisions Beat Exploratory Ideas
If the user said "let's try X" in one chat and "X is locked in" in another, the locked decision wins. Exploration is not commitment.

### 6. Current Product Sequence Must Not Be Overridden by Old Sequence
Current rule: Initiate Arena first, Game of Lyfe second core product. Old chats may have different sequences (old pricing, old product order, old names). The current product map wins.

### 7. Direct Quote Beats Paraphrased Summary
A direct user quote ("I want X") beats a summary ("The user wants something like X").

### 8. Timestamped Source Beats Undated Source
A claim with a known date beats a claim without a date, all else equal.

### 9. Source with Provenance Beats Source Without
A claim that says "from ChatGPT conversation on 2026-03-15" beats "from somewhere in AI chats."

### 10. Single-Session Context Does Not Override Multi-Session Pattern
If the user said something once in one session but contradicts it across ten other sessions, the pattern wins unless the single statement is an explicit correction.

### 11. Code/System State Beats Documentation
If the code says one thing and a doc says another, the code is the current truth. The doc may describe intent, but the code describes reality.

### 12. Newer Lock Document Supersedes Older Lock Document
If a new `master_intention_lock.md` is created, it supersedes the old one entirely. The old one moves to ARCHIVED status.

---

## How to Apply

When resolving a conflict:

1. Identify both sources and their types (user statement, assistant inference, doc, code, chat summary)
2. Check timestamps if available
3. Apply rules in order — first matching rule wins
4. If no rule matches, flag for human review with both sources cited
5. Never auto-resolve ambiguous conflicts — flag them

---

## Temporal Awareness

The user's views evolve over time. A contradiction between a 2024 chat and a 2026 chat is not necessarily an error — it may be growth. Always note the temporal context when flagging conflicts.
