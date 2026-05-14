# SALIENCE-AUDIT — Audit Report

> Date: 2026-05-13
> Trigger: PROVEN-IN-NAME-ONLY finding from migration test suite
> Mode: READ-ONLY static inspection + git history
> Classification: **RELOCATED** (code exists in scripts/, not runtime/)

---

## Executive Summary

The salience pipeline exists, is substantial (~2,100 LOC across 5 files),
runs nightly via cron, has produced 150 summaries with salience scores,
and has promoted 55 wiki pages. The migration test suite looked only in
`runtime/` — the code lives in `scripts/`. **§34 is materially correct**
but overclaims on two sub-components: episodic logging (enum exists, no
writes) and consolidation (runs nightly but crashed today due to a None
guard bug).

---

## §34 Claim (Verbatim)

> Salience pipeline for EOS memory (episodic logging, salience scoring,
> consolidation, promotion thresholds, Neon metadata)

Source: `/opt/OS/docs/canonical/umh_synthesis.md` line 1596

### §35 Related Claim

> Cross-session salience (logged but not yet consolidated nightly)

Source: line 1610. **This is stale** — cross-session salience IS
implemented (`scripts/salience.py:496 score_cross_session()`), has been
running nightly, and 150 summaries carry `cross_session_salience_score`.

### §36 Related Claim

> Nightly consolidation cron for memory promotion

Source: line 1619. **This is also stale** — the cron runs nightly at 3am,
has logged successful runs from 2026-04-24 through 2026-05-12.

---

## Phase 1: Codebase Search

### Files Found

| File | LOC | Location | Purpose |
|------|-----|----------|---------|
| `scripts/salience.py` | 597 | scripts/ | Heuristic scoring engine: per-session + cross-session |
| `scripts/nightly_consolidation.py` | 325 | scripts/ | Orchestrates summarize → promote pipeline |
| `scripts/summarize_conversations.py` | 508 | scripts/ | Conversation → summary with salience scoring |
| `scripts/promote_to_wiki.py` | 438 | scripts/ | Summary → wiki promotion with salience gating |
| `scripts/memory_neon.py` | 565 | scripts/ | Neon metadata persistence (salience-aware) |
| `scripts/scheduled/nightly_consolidation.sh` | 67 | scripts/scheduled/ | Cron wrapper with flock + ritual integration |
| `scripts/scheduled/nightly_consolidation_cp.py` | ~80 | scripts/scheduled/ | Control Plane wrapper for orchestrator routing |
| `umh/protocols/common.py:99` | 1 line | umh/ | `MemoryType.EPISODIC = "episodic"` enum value |
| **Total** | **~2,100** | | |

### Term Search Results

| Term | Hits (excl. archive) | Key locations |
|------|---------------------|---------------|
| `salience` | 68 | scripts/salience.py, scripts/nightly_consolidation.py, scripts/summarize_conversations.py, scripts/promote_to_wiki.py, scripts/memory_neon.py |
| `consolidation` | 14 | scripts/nightly_consolidation.py, core/orchestrator/workflows.py, core/persistent_agents.py |
| `promote_to_wiki` | 5 | scripts/promote_to_wiki.py, scripts/nightly_consolidation.py |
| `episodic` | 1 (prod) | umh/protocols/common.py (enum value only) |
| `promotion_threshold` | 0 | Not used as a named concept; thresholds are in `should_promote()` logic |

### Runtime references (in runtime/)

**Zero.** No file in `runtime/` imports or references salience, consolidation,
or the nightly pipeline. The pipeline is entirely in `scripts/` — operator
tooling, not core runtime. This is architecturally correct: salience scoring
is a batch/scheduled concern, not a request-path concern.

---

## Phase 2: Git History

### Introduction Commit

```
f845218e 2026-04-06 feat: wiki system, memory pipeline, 22 tool skills, neon skill expansion
```

All salience pipeline files were introduced in a single commit. No prior
versions. No removals. No feature branches.

### Recent Modifications

| Commit | Date | What changed |
|--------|------|-------------|
| `8a0db076` | 2026-05-10 | root-migration-r3: path canonicalization (UMH_ROOT) |
| `b6b0fb4a` | 2026-05-11 | root-migration-r8e: import migration to canonical namespace |
| `99eb74cc` | 2026-05-11 | root-migration-r8g: operational infrastructure convergence |

All modifications were namespace/path migrations — no functional changes
since the original `f845218e` commit.

### No Removals

No salience-related code was ever removed from the repo. The files in
`archive/tools_duplicate/` are pre-migration copies, not deletions.

---

## Phase 3: Inventory

### scripts/salience.py
**Status:** EXISTS_IN_HEAD
**LOC:** 597
**Last commit:** 8a0db076 (2026-05-10, path canonicalization)
**What it does:** Deterministic heuristic salience scoring. Weights 10
signal types (decisions, constraints, architecture entities, wiki
candidates, open loops, entities, topics, bug fixes, user corrections,
provider changes). Produces SalienceResult (score, label, reasons,
promotion_recommendation, consolidation_recommendation). Cross-session
scoring detects repeated themes across 30-day window.
**Wired into production:** YES — called by `scripts/summarize_conversations.py`
which is called by `scripts/nightly_consolidation.py` which runs via cron
nightly at 3am.
**Gap:** Active bug — `_find_repeated()` line 472 crashes when `current_items`
is `None` (missing None guard). Crashed on 2026-05-13 03:00 run.

### scripts/nightly_consolidation.py
**Status:** EXISTS_IN_HEAD
**LOC:** 325
**Last commit:** 8a0db076 (2026-05-10)
**What it does:** Three-phase pipeline: (1) summarize unprocessed
conversations, (2) promote high-salience summaries to wiki, (3) rescore
existing summaries. Idempotent. Skips already-processed sessions.
**Wired into production:** YES — cron via `scripts/emit_signal.py nightly_cycle`
→ orchestrator → `scripts/scheduled/nightly_consolidation.sh`
**Gap:** None beyond the `salience.py` bug above.

### scripts/summarize_conversations.py
**Status:** EXISTS_IN_HEAD
**LOC:** 508
**Last commit:** b6b0fb4a (2026-05-11)
**What it does:** Reads conversation markdown files, calls LLM to extract
structured summary (title, topics, decisions, constraints, entities,
open_loops, wiki_candidates), writes summary markdown with YAML frontmatter
including all salience fields, records to Neon.
**Wired into production:** YES — called by nightly_consolidation.py
**Gap:** None.

### scripts/promote_to_wiki.py
**Status:** EXISTS_IN_HEAD
**LOC:** 438
**Last commit:** 8a0db076 (2026-05-10)
**What it does:** Reads summaries, applies salience-based promotion gates
(`should_promote()`: low=skip, medium=only decisions, high/critical=promote),
dedup checks against existing wiki pages, writes promoted pages with
provenance (salience label + score).
**Wired into production:** YES — called by nightly_consolidation.py
**Gap:** None.

### scripts/memory_neon.py
**Status:** EXISTS_IN_HEAD
**LOC:** 565
**Last commit:** b6b0fb4a (2026-05-11)
**What it does:** Neon persistence for the memory pipeline. Records summary
events with salience metadata, links summaries to conversations, provides
salience-aware search (ranked by salience_score DESC then recency).
**Wired into production:** YES — called by summarize_conversations.py
**Gap:** None.

### umh/protocols/common.py — MemoryType.EPISODIC
**Status:** EXISTS_IN_HEAD
**LOC:** 1 line (enum value)
**What it does:** Defines `EPISODIC = "episodic"` as one of 14 memory types.
**Wired into production:** NO — the enum is defined but no production code
creates entries with `memory_type="episodic"`. The nightly pipeline processes
conversations (stored as markdown), not typed episodic memory entries.
**Gap:** Episodic logging exists conceptually (conversations ARE episodic
memories) but no code writes `MemoryType.EPISODIC` entries to the canonical
memory store.

---

## Phase 4: Classification

**Classification: RELOCATED**

The salience pipeline code exists in `scripts/` (operator tooling), not
`runtime/` (core execution layer). This is architecturally appropriate —
salience scoring is a nightly batch concern, not a request-path concern.

The migration test suite (and the PROVEN-IN-NAME-ONLY finding) searched
only in `runtime/` and concluded the code doesn't exist. It does exist.
It runs nightly. It has produced 150 scored summaries and 55 promoted wiki
pages.

### Evidence

| Sub-claim from §34 | Status | Evidence |
|---------------------|--------|---------|
| Episodic logging | **PARTIAL** | MemoryType.EPISODIC enum exists. Conversations are logged as markdown files (functionally episodic). But no code writes typed episodic entries to Neon/canonical store. |
| Salience scoring | **PROVEN** | `scripts/salience.py` — 597 LOC, 10 signal types, heuristic weights, per-session + cross-session scoring. All 150 summaries have scores. |
| Consolidation | **PROVEN** (with bug) | `scripts/nightly_consolidation.py` — runs nightly, 14 successful runs logged (2026-04-24 through 2026-05-12). Today's run crashed on `salience.py:472` (None guard bug). |
| Promotion thresholds | **PROVEN** | `scripts/promote_to_wiki.py:should_promote()` — low=skip, medium=decisions only, high/critical=promote. 55 wiki pages promoted with salience provenance. |
| Neon metadata | **PROVEN** | `scripts/memory_neon.py` — records salience_score, salience_label, salience_reasons per summary. Provides salience-aware search ranking. |

### Overall: 4/5 sub-claims PROVEN, 1/5 PARTIAL

---

## Implications for §34

**§34 is materially correct but needs two corrections:**

1. **Episodic logging**: Reword from "episodic logging" to "conversation
   logging" or add a note that episodic entries are stored as markdown
   files, not as typed MemoryType.EPISODIC entries in the canonical store.

2. **Location**: The claim should note that the pipeline lives in `scripts/`
   (operator tooling), not `runtime/`. This is correct architecture but
   the implicit assumption of "PROVEN in runtime" was wrong.

### §35 correction needed

Line 1610: "Cross-session salience (logged but not yet consolidated nightly)"

**This is stale.** Cross-session salience IS implemented and runs nightly.
`score_cross_session()` in `scripts/salience.py:496` detects repeated
themes across a 30-day window. 150 summaries have `cross_session_salience_score`.
This line should move from §35 to §34.

### §36 correction needed

Line 1619: "Nightly consolidation cron for memory promotion"

**This is stale.** The cron is running and has been since 2026-04-24.
This line should move from §36 to §34.

---

## Implications for Migration Plan

Since classification is **RELOCATED** (not GHOST or PLANNED):

1. **The migration manifest must track these 5 files** as part of the
   salience pipeline. They currently live in `scripts/` which is correct
   for operator tooling, but any migration that reorganizes `scripts/`
   must preserve the import chain:
   ```
   cron → emit_signal.py → orchestrator → nightly_consolidation.sh
       → nightly_consolidation.py
           → summarize_conversations.py → salience.py + memory_neon.py
           → promote_to_wiki.py
   ```

2. **The None guard bug** in `scripts/salience.py:472` should be fixed
   before or during migration. It's a one-line fix (`current_items or []`).

3. **The migration test suite finding** should be updated: the salience
   pipeline is not PROVEN-IN-NAME-ONLY — it's PROVEN in `scripts/`, not
   in `runtime/`.

---

## Active Bug

**File:** `scripts/salience.py:472`
**Function:** `_find_repeated(current_items, past_summaries, field)`
**Bug:** `current_items` can be `None` when LLM output omits `open_loops`.
Line 472 iterates `current_items` without a None guard.
**Impact:** Crashed the 2026-05-13 03:00 nightly consolidation run.
**Fix:** `for item in (current_items or []):` — one-line change.
**Status:** Not fixed (this audit is read-only).

---

## Recommendation

**Address DURING migration:**

- Track the 5 scripts as a pipeline unit in the migration manifest
- Fix the None guard bug (`salience.py:472`)
- Correct §34/§35/§36 classifications in the synthesis doc
- Update the migration test suite PROVEN-IN-NAME-ONLY finding
- No architectural changes needed — `scripts/` is the right location

---

## Chat Summary

- Classification: **RELOCATED** (scripts/, not runtime/)
- Code locations: scripts/salience.py, scripts/nightly_consolidation.py, scripts/summarize_conversations.py, scripts/promote_to_wiki.py, scripts/memory_neon.py (~2,100 LOC)
- Git history: introduced f845218e (2026-04-06), never removed, recently path-migrated
- §34 correction needed: yes — episodic logging is conversation logging (no typed entries), pipeline is in scripts/ not runtime/
- Recommendation: address during migration (track pipeline, fix None guard bug, correct §34/§35/§36)
