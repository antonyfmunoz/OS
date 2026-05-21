---
title: "Layer 3.1 — Sovereignty Cleanup Retrospective"
date_completed: 2026-05-20
status: CLOSED
related_principles:
  - Leverage Principle
  - Ownership Principle
related_merges:
  - d74a9149  # prequel — WIKI_RULES + CORPUS/CANON rename
  - b6efdc6e  # 3.1a — fix 9 broken imports
  - 02e0901e  # 3.1b — LLM prompts + martell_patterns rename
  - f8b8b7fc  # 3.1c — CEO soul mechanical
  - 90a4fc38  # 3.1d — CEO soul structural
  - 02658f81  # 3.1e — skill docs
  - d47a7572  # 3.1f — code metadata
  - 0bf127f6  # 3.1g — knowledge system
  - 38ced536  # 3.1h — portfolio cluster + residual
successor: "[[LAYER_3_UNIFIED_ARCHITECTURE]] — canonical Layer 3 architecture reference"
---

## 1. Scope Summary

Layer 3.1 systematically stripped external IP attribution from the
UMH system codebase. Every file where an external name appeared as
system IDENTITY (section headers, module docstrings, variable names,
LLM prompt labels, comments attributing framework logic) was edited
to replace the branded reference with an OST-native functional
descriptor or pure strip.

External names appearing as DATA the system observes (competitor
tracking lists, search queries, ICP landscape entries, Google Doc
title references) were explicitly preserved per the Leverage Principle.

### Tally

| Metric | Count |
|---|---|
| Merges total | 9 (1 prequel + 8 numbered: 3.1a through 3.1i) |
| Manual STRIP violations closed | 191 |
| Auto-regen violations cleared | 67 (via scripts/update-graph after source edits) |
| KEEP-AS-DATA confirmed legitimate | 32 |
| Total surface-area hits handled | ~290 |
| Original audit estimate | 67 |
| Manual-STRIP overshoot | +185% |

### Git History

| Merge | Branch | Commit | Scope |
|---|---|---|---|
| Prequel | layer3-sovereignty-wiki-rules | `d74a9149` | WIKI_RULES + CORPUS/CANON rename + Leverage Principle codified |
| 3.1a | layer3.1a-fix-broken-imports | `b6efdc6e` | Fix 9 broken imports from incomplete March 31 rename |
| 3.1b | layer3.1b-debrand-llm-prompts | `02e0901e` | LLM prompts + martell_patterns.py rename |
| 3.1c | layer3.1c-debrand-ceo-soul-mechanical | `f8b8b7fc` | CEO operational ruleset — mechanical strip |
| 3.1d | layer3.1d-rebrand-ceo-soul-structural | `90a4fc38` | CEO operational ruleset — structural rename (HORMOZI→GROWTH) |
| 3.1e | layer3.1e-debrand-skill-docs | `02658f81` | 12 skill docs + CEO primary-path completion |
| 3.1f | layer3.1f-debrand-code-metadata | `d47a7572` | 7 code metadata files + research_engine few-shot exemplars |
| 3.1g | layer3.1g-debrand-knowledge-system | `0bf127f6` | knowledge_domains.py (25 edits) + knowledge_integrator.py (3 edits) |
| 3.1h | layer3.1h-debrand-portfolio-cluster-plus-residual | `38ced536` | Portfolio advisor cluster + all residual active-code violations (14 files, 61 edits) |
| 3.1i | layer3.1i-verification-and-retrospective | — | Verification + this retrospective doc (no code edits) |

All branches preserved on origin.

---

## 2. Audit-Undercount System Property

Every estimation tier exhibited consistent undercount. The original
audit estimated 67 violations. The actual manual-STRIP count was 191
(+185%). This was not a one-time miss — the undercount pattern held
across 8 independent sample points.

### Sample Points

| Merge | Audit Estimate | Actual Edits | Overshoot | Notes |
|---|---|---|---|---|
| 3.1a | 5 | 9 | +80% | Broken imports from partial rename |
| 3.1b | 5 | 11 | +120% | LLM prompts had nested references |
| 3.1c+3.1d | 5 | 15+ | +200% | CEO ruleset was densely attributed |
| 3.1e | ~20 | 32 | +60% | Skill docs had sibling file pattern |
| 3.1f | 17 | 17 | +0% | Cialdini surfaced post-audit |
| 3.1g | 2 | 28 | +1300% | knowledge_domains.py had 21 domains × historical layers |
| 3.1h (repo grep) | — | — | — | Full-repo grep revealed entire portfolio advisor cluster invisible to original audit |
| 3.1h (spec phase) | 41 | 61 | +49% | Deep file inspection surfaced more than initial grep |

### Four Estimation Tiers

1. **Audit → repo** (original 67 → actual 191): 2.85x baseline.
   Audits scan for known patterns. They miss nested references,
   multi-line attributions, and whole agent clusters.

2. **Audit → file** (knowledge_domains.py: 2 → 25): up to 12.5x.
   Files with list/dict data structures compound the worst. A
   single module with 21 domain entries × historical layers
   produced 25 violations from an estimate of 2.

3. **Audit → agent topology** (portfolio advisor cluster invisible):
   When finding attribution in one agent's operational standards
   file, grep for sibling operational-standards files for ALL agents.
   The portfolio advisor cluster (standards + skill + gateway
   injection) was completely invisible to the original audit.

4. **Spec → execution** (41 → 61): 1.5x baseline.
   Deep file inspection during spec review surfaces additional
   hits that initial grep misses (parenthetical attributions,
   multi-word phrases, embedded references in long strings).

### Planning Guidance for Future Cleanups

- Budget 3x audit estimates as baseline
- Budget 5x as upper-bound contingency
- Grep for sibling files in agent topology (if one agent has it, all agents might)
- Expect within-spec-phase undercount of 50%
- Files with list/dict data structures: budget 10x
- Audit estimates are structural lower bounds, not estimates — plan headroom by data-structure category, not flat percentage

### Post-Closure Corroboration

The undercount property held across every cleanup-shaped merge
after Layer 3.1 closed. Three subsequent arcs independently
confirmed the pattern:

| Arc | Estimate | Actual | Ratio |
|---|---|---|---|
| Archive Bucket D (dormant files) | ~40 | 1,122 | ~28x |
| Q1 codebase pages migration | 2,416 | 5,805 | 2.4x |
| Sovereignty-grep tool itself | 19 | 20 | +1 (recursive) |

The Bucket D case exhibited the worst ratio — dormant data files
compound the same list/dict structure problem that produced the
12.5x blow-up in knowledge_domains.py. The Q1 codebase pages
case confirmed the 2-3x range for flat generated content.

The sovereignty-grep case is recursive: the audit tool itself
undercounted by 1 because a `docs/migrations/` hit was always
present but below the tool's effective scan window prior to the
Q2-Q6 wiki doc placement (commit `b94c0e27`). The audit tool
is itself subject to the undercount law.

Updated planning guidance: budget 2-3x baseline for flat
content, 10x upper bound for data-structure-heavy files,
and verify the audit tool's own scan window at spec time.
When a clean count seems too clean, distrust it.

---

## 3. Vocabulary Mappings Library

Complete reference table of all locked vocabulary renames from
Merges 1-7. This is the canonical reference for future writing —
any new attribution should be checked against this table.

### Variable / Module Renames

| Old | New | Merge |
|---|---|---|
| `buyback_rate` | `founder_rate` | 3.1a |
| `drip_matrix` / `drip` | `yield_matrix` / `yield` | 3.1a |
| `perfect_week` | `ideal_week` | 3.1a |
| `martell_patterns` | `leverage_patterns` | 3.1b |
| `camcorder_method` | `delegation_protocol` | 3.1b |
| `time_assassin` | `leverage_killer` | 3.1b |
| `131_rule` / `check_131_rule` | `solution_standard` / `check_solution_standard` | 3.1b |
| `HORMOZI_RULES` | `GROWTH_RULES` | 3.1d |
| `HORMOZI_PRICING` | `GROWTH_PRICING` | 3.1d |

### Module Path Renames

| Old Path | New Path | Merge |
|---|---|---|
| `eos_ai/martell_patterns.py` | `understanding/intelligence/leverage_patterns.py` | 3.1b |
| `runtime/drip_matrix.py` | (removed — yield_matrix integrated) | 3.1a |
| `runtime/buyback_rate.py` | `state/metrics/founder_rate.py` | 3.1a |
| `runtime/perfect_week.py` | (removed — ideal_week integrated) | 3.1a |
| `martell_patterns.py` (planned) | `leverage_patterns.py` | 3.1h |

### Source Field Metadata

| Old | New | Context |
|---|---|---|
| `hormozi_youtube` | (kept as example in docstring) | knowledge_integrator source field example — DATA |

### Author-Prefix Strips (Alphabetical)

The following author names were stripped from section headers,
comments, docstrings, and LLM prompt labels across all merges.
The content they attributed remains — only the name-as-IDENTITY
was removed.

Aristotle, Bezos, Buffett, Campbell, Carnegie, Christensen,
Cialdini, Dalio, Epictetus, Festinger, Goldratt, Graham,
Halbert, Kahneman, Karpathy, Grove, Martell, McKee, Munger,
Ogilvy, Porter, Robbins, Rosenberg, Sandler, Thiel, Voss

### Branded-Label → Functional Descriptor

| Old (Branded) | New (Functional) | Merge |
|---|---|---|
| Toyota Production System | Lean production | 3.1g |
| Aristotle's Poetics | Classical story structure | 3.1g |
| Campbell's Hero's Journey | Hero's Journey (stripped Campbell) | 3.1g |
| EOS (Traction) | Business operating framework | 3.1g |
| Rosenberg NVC | (pure strip — content stands alone) | 3.1g |
| Challenger Sale | (pure strip) | 3.1g |
| HORMOZI framework | GROWTH framework | 3.1d |
| Martell Rule | Recognition protocol / pre-meeting intel check | 3.1h |
| Charlie Morgan follow-up methodology | Follow-up methodology | 3.1h |
| Dan Martell's framework for valuing | Framework for valuing | 3.1h |
| Perfect Week | Ideal Week | 3.1a, 3.1h |
| Munger/Dalio framework (gateway label) | (pure strip) | 3.1h |

### Branded-Label → Pure Strip

Cases where the branded label was removed entirely because the
content stands alone without attribution:

- All `(Munger)` parentheticals in portfolio advisor standards (21 instances)
- All `(Dalio)` parentheticals in portfolio advisor standards
- All `(Dalio + Bezos)` parentheticals
- All `(Munger / Graham)` parentheticals
- `(Martell Rule)` in EA operational standards
- Rosenberg NVC — content is "nonviolent communication principles"
- Challenger Sale — content is "sales methodology"
- Various `Hormozi, Carnegie, Voss, etc.` enumeration lists in docstrings

### Book-Title Removals

| Removed | Context | Merge |
|---|---|---|
| "Buy Back Your Time" quote (verbatim) | CEO operational ruleset section header | 3.1c |
| "$100M Offers" / "$100M Leads" | LLM prompt labels, section headers | 3.1d |

---

## 4. Protected-File Safety Pattern

Four files were designated as protected at the start of Layer 3.1:
`gateway.py`, `cognitive_loop.py`, `model_router.py`, `agent_runtime.py`.
These are core runtime files where any change carries HIGH/CRITICAL
risk classification.

### The Reusable Pattern (5 Steps)

When a protected file contains an IDENTITY violation that requires
editing:

1. **Lazy import inside the consumer function** — not module-level.
   The change site is inside a function body, limiting blast radius.

2. **try/except guarded** — the import or consumption is inside
   exception handling, so if the upstream module changes, the
   protected file degrades gracefully.

3. **Conditional on agent_id routing** — the code path only executes
   when a specific agent is routed. It is not on the hot path for
   all requests.

4. **Pure identifier rename OR pure string literal change** — the
   edit changes a string label, variable name, or import path.
   It does not modify control flow, data flow, or function signatures.

5. **Minimal diff surface** — 1-2 lines typical. The edit is
   reviewable in isolation without understanding the surrounding
   function.

### Application History

- **Merge 3.1b** (gateway.py): Renamed `martell_patterns` import path
- **Merge 3.1d** (gateway.py): Updated `HORMOZI→GROWTH` consumer string
- **Merge 3.1h** (gateway.py): Stripped `(Munger/Dalio framework)` prompt labels (2 lines)

All three touches were pure string/identifier changes. No logic
modifications. `cognitive_loop.py`, `model_router.py`, and
`agent_runtime.py` required zero edits — they contained no
IDENTITY violations.

### Symbolic-vs-Actual-Path Precedent

The protected file list included `runtime/primitives.py`, but this
path was dead (file had been moved). The actual canonical module at
`understanding/ontology/primitives.py` was unlisted but received the
same careful treatment — inspected for violations (none found),
included in py_compile verification gates. The precedent: protected
status is semantic (the concern the file represents), not syntactic
(the exact path string). When a listed path is dead, find the
canonical module at its current location and treat it with care.

---

## 5. DATA-vs-IDENTITY Heuristic Validation

The Leverage Principle defines a 4-part sovereignty framework:

1. System sovereignty — OST never hardcodes external IP/framework
   names/attribution into system text
2. External IP lives in CORPUS/CANON/SCHEMA memory layer
3. Live leverages wrapped behind OST-native interfaces
4. Ownership Roadmap tracks live external code deps

Part 2 includes a critical nuance: external names appearing as
DATA the system observes (competitor tracking, search queries, ICP
landscape entries) are legitimate and must be preserved. The
DATA-vs-IDENTITY distinction is not theoretical — it was
load-bearing during this cleanup.

### The 32 KEEP-AS-DATA Confirmations

Merge 7 (3.1h) performed the largest-scale test of this heuristic.
The full-repo sovereignty grep surfaced 93 hits, of which 32 were
classified as KEEP-AS-DATA:

**world_pulse.py** — Search queries and creator tracking entries:
- `'Alex Hormozi new content 2026'` (search query)
- `'Charlie Morgan outreach sales 2026'` (search query)
- `'Andrew Tate business 2026'` (search query)
- `'Iman Gadzhi, Alex Hormozi, and other men\'s coaching'` (market query)
- Creator name/search_query pairs in CREATORS dict

**competitive_intel.py** — Tracked competitor list:
- `'Alex Hormozi', 'Dan Koe', 'Andrew Tate', 'Hamza Ahmed'`
- These are the system's observation targets, not system identity

**venture_knowledge.py** — ICP competitive landscape:
- `"Competes where Robbins and Dispenza can't"` (positioning data)
- `"Robbins = hype events + surface-level motivation"` (competitor analysis)
- `"Tony Robbins — hype events, surface-level motivation"` (competitor entry)

**knowledge_integrator.py** — Docstring source field example:
- `source: 'hormozi_youtube'` (example of source identifier format)

**docs/system/w0_001_*.md** — Google Doc title references:
- `"Hormozi conversation"` appears as a Google Drive document title
- The system references the document by its actual title — DATA

**Skill tool docs** — Use-case examples in best_practices.md:
- Apify: `"hormozi"` as profile scraper target username
- Instagram: `"hormozi"` as business account example
- Perplexity: `"Gadzhi, Hormozi"` as competitor intelligence query
- TikTok: creator names as content batching strategy examples

### Why This Matters

Mechanical strip (replace all matches without semantic review)
would have broken:
- World pulse competitor tracking (search queries would return wrong results)
- Competitive intelligence functionality (tracked competitor list emptied)
- ICP landscape data (competitive positioning analysis destroyed)

The semantic-review framework was load-bearing, not theoretical.
This validates Leverage Principle parts 1 and 2 working together:
system text is sovereign (part 1), observed data about the external
world is preserved (part 2).

---

## 6. Deferred Items

The following items were explicitly excluded from Layer 3.1 scope
and are tracked for future work:

### Test-Hygiene Merge

Canonical test baseline after Layer 3.1: **66 passed, 18 deselected**.

The 18 deselected items come from 4 broken test classes in
`tests/test_ea_final.py`:
- `TestDripMatrix` (4 items) — imports `runtime.drip_matrix` (removed)
- `TestBuybackRate` (4 items) — imports `runtime.buyback_rate` (removed)
- `TestLeveragePatterns` (7 items) — imports `runtime.leverage_patterns` (removed)
- `TestPerfectWeek` (3 items) — imports `runtime.perfect_week` (removed)

The `--deselect` flags also include 11 class names from
`tests/test_command_surface_sync_v1.py`, but these are no-ops —
those class names do not exist in that file (they were from an
earlier test arrangement). The effective deselection is 4 classes,
18 items, all from `test_ea_final.py`.

The test-hygiene merge should either update these tests to use the
new module paths or remove them if the underlying functionality
was intentionally retired.

### Archive-Hygiene Merge (Bucket D)

37+ files across `archive/`, `_archive/`, `vault/`,
`data/umh/traces/` contain external attribution. These are dormant
data files not consumed by any runtime code. A separate archive-
hygiene pass can strip them, but the priority is low — they carry
no runtime risk.

### Discord Command Identifiers

`!buyback`, `!drip`, `!perfectweek` — user-facing command names
in Discord. Renaming these is a user-facing breaking change that
requires a separate user-identifier-sovereignty decision, not a
code cleanup merge.

### w0_001 Historical Docs (Bucket C)

75 hits across `docs/` including w0_001 audit documents and
`docs/superpowers/plans/` historical build plans. These reference
Google Doc titles, old module names, and historical plan content.
They are frozen history — editing them rewrites the record.

### Architecture Docs

6 open questions in the unified architecture doc and an expensive
docs-migration merge remain long-pending. Separate from sovereignty
cleanup.

---

## 7. Strategic Learnings

Four observations distilled from the cleanup, framed for reuse
in future system-wide refactoring or cleanup initiatives:

### 1. Audit hit counts are a structural lower bound

Audits scan for known patterns. They miss nested references in
data structures (lists, dicts), multi-line attributions split
across string concatenation, and entire agent clusters whose
operational-standards files weren't in the initial scan.

Plan headroom by data-structure category:
- Flat code (comments, docstrings): 2-3x audit estimate
- List/dict data files: 10x+ audit estimate
- Agent topology (standards files): grep all siblings when one has hits

### 2. Atomic renames — module + all consumers in same commit

The March 31 partial rename (`martell_patterns.py` → file renamed
but not all import paths updated) produced 9 broken imports that
persisted for 7 weeks until Layer 3.1a fixed them. Partial renames
create silent runtime breakage that only surfaces when the broken
code path is exercised.

Rule: every module rename must include all consumers in the same
commit. `grep -rn 'old_name'` before committing.

### 3. The DATA-vs-IDENTITY distinction is load-bearing

Cleaning sovereignty without preserving observed-data references
breaks system functionality. The 32 KEEP-AS-DATA confirmations in
Merge 7 proved that mechanical strip would have destroyed world
pulse competitor tracking and competitive intelligence features.

Rule: every cleanup initiative needs a semantic-review framework,
not just a find-and-replace script.

### 4. When in doubt on vocabulary, strip more rather than less

Across 7 code-editing merges, every "keep the branded label"
judgment call that was considered was eventually replaced with
pure strip on closer inspection. Pure-functional descriptors
compound in clarity over time — they make the system's logic
self-evident without requiring knowledge of the external source.

Rule: if the content stands alone without the attribution, strip
the attribution. The burden of proof is on keeping the branded
label, not on removing it.

### 5. Post-migration import verification is non-optional

The March 31 partial rename (§7 item 2) showed that renames
must include all consumers in the same commit. The Wave 3
structural reorganization (commit `756730dc`, `core/runtime/`
split to `execution/runtime/` + `adapters/adapter_engine/`)
demonstrated the detection corollary: even when the
reorganization is intentional and complete, relative imports
silently break if the target module moves to a different
package. Python won't error at parse time — only at import time.

`canonical_runtime_spine_v1.py` used `from .adapter_lifecycle_manager_v1`
(relative import within `execution/runtime/`), but the module
had been relocated to `adapters/adapter_engine/`. The broken
import was latent for weeks. It was caught because an untracked
test file happened to import the spine — without that test, the
breakage would have remained invisible.

Rule: after any structural reorganization, run
`python3 -c "from <pkg> import <mod>"` for every module in the
dependency graph. Import verification is not a nicety — it is
the only reliable detection mechanism for relative-import
breakage post-reorg.

### 6. Verification tools can mask their own failures

A prior handoff claimed "17 → 0 failures" based on
`pytest --tb=no` output. The count was accurate for tracked
tests. It masked a collection error: an untracked test file
could not be imported (broken relative import in its
dependency chain), so its 59 tests were invisible to the suite.
The file never reached the "pass/fail" stage — it failed at
collection, and `--tb=no` suppressed the traceback.

"0 failures" and "1 collection error" coexist without
contradiction. The failure count measures tests that ran and
failed. Collection errors measure tests that never ran at all.
A clean failure count is not evidence of clean collection.

Rule: when a test run reports success, check collection
separately. `pytest --collect-only <path>` per file in
suspect scope. The verification tool is itself subject to
the audit-undercount law (§2) — its reported count is a
lower bound on the true test surface.

### 7. Dead code in shell scripts has no natural predator

In compiled and interpreted languages, linters catch
unreferenced symbols. Bash does not. The `EXCLUDES` array in
`scripts/sovereignty-grep.sh` used ripgrep `--glob` syntax
for a planned ripgrep migration that never shipped. The script
settled on `grep` with pipe filters. The array sat inert —
the shell allocated it, nothing read it, no tool flagged the
waste.

The danger is not the dead code itself. The danger is that a
future maintainer edits the array expecting effect. There is
no signal — no warning, no lint error, no test failure — that
the variable is inert. The ripgrep `--glob` syntax was the
only tell, and only if the reader noticed the script uses
`grep`, not `rg`.

Rule: when a tool choice changes mid-implementation, audit
for old scaffolding before merging. Treat unreferenced bash
variables with active suspicion during review. If a shell
array doesn't flow into any later command, verify by removing
it and re-running.
