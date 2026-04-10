# Comparative Tool Mastery Batch Validation

**Date:** 2026-04-09
**Scope:** 8 tools across the TME pipeline
**Pipeline version:** research agent + author agent + verifier (Phase 6)

---

## 1. Executive Summary

The Tool Mastery pipeline was measured across 8 real tools spanning different
difficulty classes. All 8 tools had existing human-authored skills, so every
author run triggered **preserve-mode** (correctly refusing to overwrite).

The underlying evidence analysis reveals:

- **28.3% section coverage** (43/152 sections sourced across 8 tools)
- **71.7% uncovered** — the pipeline cannot ground most sections from fetched docs
- **Prose dominates**: 86% of sourced sections came from prose keyword matching;
  structured patterns contributed only 1.3% of all sections
- **4 sections are always uncovered** across all 8 tools: Version Pinning,
  Design Intent and Tradeoffs, Operational Behavior and Edge Cases,
  Conceptual Model and Solution Recipes
- **Best case** (Stripe): 13/19 sourced — strong docs produce real signal
- **Worst case** (Higgsfield, CLO3D): 0/19 sourced — weak-signal tools get nothing

The system is **honest**: no fabrication detected, preserve-mode works correctly,
and uncovered sections are transparently marked. But the coverage gap is the
dominant bottleneck — the pipeline acquires sources well but extracts too
little signal from them.

---

## 2. Batch Selection

| # | Tool | Reason | Expected Difficulty | Actual Difficulty |
|---|------|--------|--------------------|--------------------|
| 1 | notion | Strong API docs, registry entry | Medium | Medium |
| 2 | stripe | Gold-standard API docs, registry entry | Easy-Medium | Easy |
| 3 | posthog | Analytics product, SPA docs, registry entry | Medium | Medium |
| 4 | drizzle_orm | GitHub-heavy ORM, no registry, official URL provided | Medium-Hard | Medium |
| 5 | remotion | React video framework, GitHub repo | Medium | Hard |
| 6 | higgsfield | AI video startup, minimal docs | Hard | Extreme |
| 7 | clo3d | 3D fashion software, niche docs | Hard | Extreme |
| 8 | shadcn_ui | Component library, GitHub-heavy | Medium | Medium |

---

## 3. Baseline Table

| Tool | Existing Skill | BP Lines | Human-Authored | Research Artifacts (prior) | Verifier Pass |
|------|---------------|----------|----------------|---------------------------|---------------|
| notion | Yes | 926 | Yes | 3 runs (best: ok, 2 fetched) | PASS |
| stripe | Yes | 959 | Yes | None | PASS |
| posthog | Yes | 750 | Yes | None | PASS |
| drizzle_orm | Yes | 406 | Yes | None | PASS |
| remotion | Yes | 353 | Agent-generated (prev run) | 2 runs (best: partial, 6 fetched) | PASS |
| higgsfield | Yes | 1107 | Yes | 5 runs (best: ok, 2 fetched) | PASS |
| clo3d | Yes | 774 | Yes | 6 runs (best: partial, 4 fetched) | PASS |
| shadcn_ui | Yes | 914 | Yes | None | PASS |

---

## 4. Per-Tool Outcomes

### 4.1 Notion

| Metric | Value |
|--------|-------|
| Research status | ok |
| Sources planned / fetched ok | 2 / 2 |
| Source origins | tool_doc_registry (2) |
| Source tiers | official_docs (1), official_api_ref (1) |
| Total bytes fetched | 757,908 |
| Author status | AUTHORED_READY (preserve-mode) |
| Sections sourced (evidence) | 4/19 |
| Sections uncovered (evidence) | 15/19 |
| Grounding | prose: 4, pattern: 0 |
| Sourced sections | Core Operations, Pagination Patterns, Data Model, Problem-Solution Map |
| Quality assessment | **Medium** — only 2 source pages fetched; keyword density is low on Notion's reference page. More pages would improve coverage. |

### 4.2 Stripe

| Metric | Value |
|--------|-------|
| Research status | partial |
| Sources planned / fetched ok | 24 / 10 |
| Source origins | tool_doc_registry (1), llms.txt (6), structured_crawl (3) |
| Source tiers | official_docs (9), official_api_ref (1) |
| Total bytes fetched | 6,473,795 |
| Author status | AUTHORED_READY (preserve-mode) |
| Sections sourced (evidence) | 13/19 |
| Sections uncovered (evidence) | 6/19 |
| Grounding | prose: 13, pattern: 0 |
| Sourced sections | Authentication, Core Operations, Rate Limits, Error Codes, SDK Idioms, Anti-Patterns, Data Model, Webhooks, Limits, Cost Model, Problem-Solution Map, Ecosystem Position, Industry Expert |
| Quality assessment | **High** — best performer. Stripe's docs are prose-rich. llms.txt + structured crawl surfaced 9 additional pages. Zero patterns despite high coverage — prose keyword matching carries the entire load. |

### 4.3 PostHog

| Metric | Value |
|--------|-------|
| Research status | partial |
| Sources planned / fetched ok | 24 / 6 |
| Source origins | tool_doc_registry (1), llms.txt (3), structured_crawl (2) |
| Source tiers | official_docs (5), official_api_ref (1) |
| Total bytes fetched | 2,607,329 |
| Author status | AUTHORED_READY (preserve-mode) |
| Sections sourced (evidence) | 10/19 |
| Sections uncovered (evidence) | 9/19 |
| Grounding | prose: 9, pattern: 1, mixed: 0 |
| Extracted patterns | api: 4, usage: 0, workflows: 0 |
| Sourced sections | Authentication, Core Operations, Pagination, Error Codes, SDK Idioms, Data Model, Webhooks, Limits, Problem-Solution Map, Industry Expert |
| Quality assessment | **Medium-High** — 1 section grounded via pattern (structured API extraction). Most coverage still from prose. 17 sources skipped (signal too low). |

### 4.4 Drizzle ORM

| Metric | Value |
|--------|-------|
| Research status | partial |
| Sources planned / fetched ok | 23 / 10 |
| Source origins | request (1), llms.txt (7), structured_crawl (2) |
| Source tiers | official_docs (10) |
| Total bytes fetched | 1,993,342 |
| Author status | AUTHORED_READY (preserve-mode) |
| Sections sourced (evidence) | 6/19 |
| Sections uncovered (evidence) | 13/19 |
| Grounding | prose: 4, pattern: 1, mixed: 1 |
| Extracted patterns | usage: 22, api: 2, workflows: 0 |
| Sourced sections | Core Operations, SDK Idioms, Data Model, Problem-Solution Map, Trajectory, Industry Expert |
| Quality assessment | **Medium** — 22 usage patterns extracted but most mapped to sections that were already prose-covered. Pattern → section routing underperforms: high extraction, low section reach. Authentication uncovered despite ORM connection strings being in the docs. |

### 4.5 Remotion

| Metric | Value |
|--------|-------|
| Research status | partial |
| Sources planned / fetched ok | 13 / 5 |
| Source origins | github_extractor (5) |
| Source tiers | official_repo (5) |
| Total bytes fetched | 39,872 |
| Author status | AUTHORED_READY (preserve-mode, latest run) |
| Sections sourced (evidence) | 5/19 |
| Sections uncovered (evidence) | 14/19 |
| Grounding | prose: 4, mixed: 1, pattern: 0 |
| Sourced sections | SDK Idioms, Data Model, Cost Model, Problem-Solution Map, Trajectory |
| Quality assessment | **Low-Medium** — only GitHub raw files as sources (39KB total). No docs site pages fetched. README and CHANGELOG provide some signal but the low byte count limits prose density. Remotion has a docs site (remotion.dev) that was NOT discovered — source discovery gap. |

### 4.6 Higgsfield

| Metric | Value |
|--------|-------|
| Research status | ok (best run) / fetch_failed (latest) |
| Sources planned / fetched ok | 2 / 2 (best run) |
| Source origins | generated (2) |
| Source tiers | official_docs (1), official_repo (1) |
| Total bytes fetched | 2,013,680 |
| Author status | BLOCKED_NO_SOURCES (latest) / preserve-mode (best artifact) |
| Sections sourced (evidence) | 0/19 |
| Sections uncovered (evidence) | 19/19 |
| Grounding | uncovered: 19 |
| Quality assessment | **None** — 2MB fetched but zero prose blocks pass the quality gate. The content is likely marketing pages, nav menus, or code-heavy without explanatory prose. This is a tool with genuinely sparse documentation. Honestly measured. |

### 4.7 CLO3D

| Metric | Value |
|--------|-------|
| Research status | partial (best run) |
| Sources planned / fetched ok | 11 / 4 (best run) |
| Source origins | generated (4) |
| Source tiers | official_docs (2), official_repo (1), official_package (1) |
| Total bytes fetched | 258,040 |
| Author status | AUTHORED_READY (preserve-mode) |
| Sections sourced (evidence) | 0/19 |
| Sections uncovered (evidence) | 19/19 |
| Grounding | uncovered: 19 |
| Quality assessment | **None** — similar to Higgsfield. CLO3D's online resources are either marketing, login-gated knowledge bases, or non-prose content. The pipeline correctly reports zero coverage rather than fabricating. |

### 4.8 shadcn/ui

| Metric | Value |
|--------|-------|
| Research status | partial |
| Sources planned / fetched ok | 22 / 15 |
| Source origins | request (1), llms.txt (6), headless_render (1), structured_crawl (7) |
| Source tiers | official_docs (15) |
| Total bytes fetched | 9,217,078 |
| Author status | AUTHORED_READY (preserve-mode) |
| Sections sourced (evidence) | 5/19 |
| Sections uncovered (evidence) | 14/19 |
| Grounding | prose: 3, mixed: 2, pattern: 0 |
| Extracted patterns | usage: 2, api: 3, workflows: 0 |
| Sourced sections | SDK Idioms, Data Model, Problem-Solution Map, Ecosystem Position, Industry Expert |
| Quality assessment | **Low-Medium** — 9.2MB fetched from 15 sources but only 5 sections sourced. shadcn/ui docs are heavily component-example oriented (code blocks, props tables) rather than prose paragraphs. The prose gate rejects most content as too code-heavy. This is a genuine extraction gap for component library documentation. |

---

## 5. Cross-Tool Metrics

### 5.1 Coverage Distribution

| Tool | Sourced | Uncovered | Coverage % |
|------|---------|-----------|-----------|
| stripe | 13 | 6 | 68.4% |
| posthog | 10 | 9 | 52.6% |
| drizzle_orm | 6 | 13 | 31.6% |
| remotion | 5 | 14 | 26.3% |
| shadcn_ui | 5 | 14 | 26.3% |
| notion | 4 | 15 | 21.1% |
| higgsfield | 0 | 19 | 0.0% |
| clo3d | 0 | 19 | 0.0% |
| **TOTAL** | **43** | **109** | **28.3%** |

Average sourced sections per tool: **5.4 / 19**

### 5.2 Status Distribution

| Status | Count | Notes |
|--------|-------|-------|
| AUTHORED_READY (preserve-mode) | 7 | Existing human skill preserved |
| BLOCKED_NO_SOURCES | 1 | Higgsfield latest run |

All 8 tools have existing human skills → preserve-mode engaged for all.
The pipeline correctly refuses to overwrite.

### 5.3 Top 5 Sections Most Often Sourced

| Section | Tools Sourced (out of 8) |
|---------|------------------------|
| Data Model | 6 |
| Problem-Solution Map and Hidden Capabilities | 6 |
| SDK Idioms | 5 |
| Core Operations with Exact Signatures | 4 |
| Industry Expert and Cutting-Edge Usage | 4 |

### 5.4 Top 5 Sections Most Often Uncovered

| Section | Tools Uncovered (out of 8) |
|---------|--------------------------|
| Version Pinning | 8 (always) |
| Design Intent and Tradeoffs | 8 (always) |
| Operational Behavior and Edge Cases | 8 (always) |
| Conceptual Model and Solution Recipes | 8 (always) |
| Rate Limits | 7 |

### 5.5 Grounding Breakdown (all 152 section-slots)

| Grounding Type | Count | Percentage |
|---------------|-------|-----------|
| uncovered | 109 | 71.7% |
| prose | 37 | 24.3% |
| mixed (pattern + prose) | 4 | 2.6% |
| pattern (structured only) | 2 | 1.3% |

**Prose carries 86% of all sourced sections.** Structured pattern extraction
exists (17 total patterns used across the batch) but almost never promotes a
section that prose did not already cover.

### 5.6 Source Type Productivity

| Source Type | Best Performer | Worst Performer | Notes |
|------------|---------------|-----------------|-------|
| tool_doc_registry | stripe (13/19) | notion (4/19) | Most reliable — direct registry URLs always fetch |
| llms.txt discovery | stripe (6 pages), shadcn_ui (6 pages) | — | New capability; surfaces real doc pages from vendor llms.txt |
| structured_crawl | stripe (3 pages), shadcn_ui (7 pages) | — | Adds same-host doc pages; useful for deep sites |
| github_extractor | remotion (5 files) | — | Raw files only; low prose density limits section mapping |
| headless_render | shadcn_ui (1 page) | — | SPA rendering fallback; rarely triggers |

**Most productive source type: tool_doc_registry + llms.txt in combination.**
Registry ensures the root docs URL; llms.txt surfaces the vendor's recommended
doc pages. Together they produce the highest coverage (Stripe, PostHog).

**Least useful source type: GitHub raw files (for prose extraction).**
Remotion's 5 raw GitHub files yielded only 39KB and 5/19 sections. Code-heavy
content fails the prose quality gate by design.

---

## 6. Honesty / Quality Audit

### Did the system fabricate anything?
**No.** Every sourced section has explicit `[SOURCE: url]` markers and bounded
excerpts extracted from fetched captures. No section was promoted without
meeting the 2-keyword threshold + prose block requirement.

### Did it overclaim readiness anywhere?
**Partially.** All 8 tools return `AUTHORED_READY` because preserve-mode
treats existing human skills as "ready" regardless of what the pipeline
could contribute. This is **structurally correct** (the skill IS ready — it
was written by a human) but it **masks the pipeline's actual capability**.
A tool like Notion shows AUTHORED_READY but the pipeline could only source
4/19 sections if it were writing from scratch.

### Did preserve-mode behave correctly?
**Yes.** All 7 human-authored skills were preserved without modification.
Remotion (the only agent-generated skill) was also preserved on the latest
run because a prior author run already wrote to it and the reconciliation
logic now treats it as existing.

### Did any section look structurally valid but low-value?
**Yes — "Industry Expert and Cutting-Edge Usage".** This section is sourced
in 4/8 tools but its keyword set (`advanced`, `expert`, `best practice`,
`production`, `scale`) is extremely generic. Almost any substantial tech
doc page will trigger these keywords. The resulting excerpts are often
tangential to actual industry-expert usage patterns.

### Are there still false positives slipping through?
**One soft false positive identified:** The "Industry Expert" section keyword
set has a high false-positive rate. The 2-keyword threshold is met by generic
documentation prose rather than actual expert usage content. This section
should have stricter keywords or be moved to a higher confidence threshold.

---

## 7. Dominant Bottleneck

**Structured extraction coverage.**

The evidence is unambiguous:

1. **Source acquisition works.** The pipeline fetches between 2–15 sources per
   tool, totaling hundreds of KB to 9MB of raw documentation content. Four
   discovery mechanisms (registry, llms.txt, structured crawl, GitHub
   expansion) successfully acquire real documentation.

2. **Source quality is mixed but not the binding constraint.** Even with 10
   OK sources and 6.5MB of Stripe docs, 6 sections remain uncovered. Even
   with 15 sources and 9.2MB of shadcn/ui docs, 14 sections remain
   uncovered.

3. **The extraction layer loses most of the signal.** The prose gate +
   keyword mapping extracts only 28.3% of section coverage from the
   fetched content. The structured pattern extractor contributes only
   1.3% of total sections — it finds patterns (22 for Drizzle alone)
   but most don't map to sections that need them, or they repeat coverage
   prose already provides.

4. **Four sections are NEVER sourced** across any tool: Version Pinning,
   Design Intent, Operational Behavior, and Conceptual Model. Their keyword
   sets either don't match documentation prose (too specific) or match in
   places that fail the prose block quality gate (code examples, changelogs).

The bottleneck is not "can we get the docs?" — it's "can we extract the right
signal from docs we already have?"

---

## 8. Single Recommended Next Build

**Improve section mapping coverage by adding code/config-aware extraction
for the 4 permanently-uncovered sections.**

Justification:

- The 4 always-uncovered sections (Version Pinning, Design Intent,
  Operational Behavior, Conceptual Model) represent 21% of the section
  model. Fixing even 2 of them would raise average coverage from 28% to ~40%.

- The current mapping relies exclusively on prose blocks. But "Version
  Pinning" content typically appears in **config examples** (`"version":
  "2024-02-01"`, `Notion-Version: 2022-06-28`), **YAML frontmatter**, or
  **changelog headers** — none of which pass `is_prose_block()`.

- "Conceptual Model and Solution Recipes" content appears in **getting
  started guides** and **quickstart code blocks** — structured content the
  prose gate rejects.

- The fix is scoped: extend `mapping.py` with a **code-aware extraction
  mode** that recognizes config blocks, version headers, and structured
  examples as valid evidence for specific sections. This does not require
  an LLM — pattern matching against code fence contents and structured
  markers is sufficient.

- This single change would address the most common failure mode across the
  entire batch and would produce measurable improvement on the next
  validation run.

**Do not** try to fix all 19 sections at once. Fix the 4 that are always
zero first, measure, then iterate.

---

## Appendix: Raw Data Summary

| Tool | Plan | Fetched OK | Bytes | Sourced | Uncov | Pattern | Prose | Mixed | Quality |
|------|------|-----------|-------|---------|-------|---------|-------|-------|---------|
| notion | 2 | 2 | 758K | 4 | 15 | 0 | 4 | 0 | Medium |
| stripe | 24 | 10 | 6.5M | 13 | 6 | 0 | 13 | 0 | High |
| posthog | 24 | 6 | 2.6M | 10 | 9 | 1 | 9 | 0 | Med-High |
| drizzle_orm | 23 | 10 | 1.9M | 6 | 13 | 1 | 4 | 1 | Medium |
| remotion | 13 | 5 | 40K | 5 | 14 | 0 | 4 | 1 | Low-Med |
| higgsfield | 2 | 2 | 2.0M | 0 | 19 | 0 | 0 | 0 | None |
| clo3d | 11 | 4 | 258K | 0 | 19 | 0 | 0 | 0 | None |
| shadcn_ui | 22 | 15 | 9.2M | 5 | 14 | 0 | 3 | 2 | Low-Med |
| **TOTAL** | **121** | **54** | **23.3M** | **43** | **109** | **2** | **37** | **4** | — |

---

## Phase 7 Re-Run — Code/Config Extraction Impact

**Date:** 2026-04-09
**Method:** Re-ran Phase 7 extractors (4 new code/config-aware extractors) against
the same raw captures used in the baseline audit above. No re-fetching — same
sources, same raw files, same 8-tool batch. Only difference: Phase 7 extraction
logic applied retroactively.

**Phase 7 adds 14 new pattern kinds across 4 extractors:**
- Version Pinning: `version_header`, `version_constraint`, `pinned_dependencies`, `version_pin_guidance`
- Design Intent: `design_rationale`, `comparison_table`, `tradeoff_reasoning`
- Operational Behavior: `warning_admonition`, `error_handling_pattern`, `retry_backoff_pattern`, `edge_case_documentation`
- Conceptual Model: `quickstart_flow`, `conceptual_explanation`, `tutorial_progression`

---

### 9.1 Overall Coverage Before vs After

| Tool | Before | After | Delta | New Sections |
|------|--------|-------|-------|-------------|
| notion | 4/19 | 5/19 | +1 | Version Pinning |
| stripe | 13/19 | 16/19 | +3 | Design Intent, Operational Behavior, Version Pinning |
| posthog | 10/19 | 12/19 | +2 | Design Intent, Operational Behavior |
| drizzle_orm | 6/19 | 9/19 | +3 | Conceptual Model, Design Intent, Operational Behavior |
| remotion | 5/19 | 8/19 | +3 | Design Intent, Operational Behavior, Version Pinning |
| higgsfield | 0/19 | 1/19 | +1 | Operational Behavior |
| clo3d | 0/19 | 1/19 | +1 | Design Intent |
| shadcn_ui | 5/19 | 7/19 | +2 | Design Intent, Operational Behavior |
| **TOTAL** | **43/152** | **59/152** | **+16** | — |
| **Coverage** | **28.3%** | **38.8%** | **+10.5pp** | — |

Average sourced sections per tool rose from **5.4 → 7.4** out of 19.

---

### 9.2 Recovery Rate for the 4 Previously-Zero Sections

| Section | Before (all tools) | After | Recovery Rate | Recovered In |
|---------|-------------------|-------|--------------|-------------|
| Design Intent and Tradeoffs | 0/8 | **6/8** | 75% | stripe, posthog, drizzle_orm, remotion, clo3d, shadcn_ui |
| Operational Behavior and Edge Cases | 0/8 | **6/8** | 75% | stripe, posthog, drizzle_orm, remotion, higgsfield, shadcn_ui |
| Version Pinning | 0/8 | **3/8** | 37.5% | notion, stripe, remotion |
| Conceptual Model and Solution Recipes | 0/8 | **1/8** | 12.5% | drizzle_orm |

**Combined recovery: 16 section-slots recovered out of 32 that were always-zero (50%).**

---

### 9.3 Phase 7 Pattern Kinds — Which Fired on Real Data

| Kind | Fired? | Tools (count) |
|------|--------|---------------|
| comparison_table | YES | posthog(4), drizzle_orm(1) |
| tradeoff_reasoning | YES | stripe(2), posthog(1), remotion(2), clo3d(1), shadcn_ui(1) |
| edge_case_documentation | YES | stripe(1), remotion(2), higgsfield(1) |
| warning_admonition | YES | posthog(2), shadcn_ui(2) |
| retry_backoff_pattern | YES | stripe(3) |
| pinned_dependencies | YES | remotion(6) |
| version_pin_guidance | YES | stripe(2), remotion(1) |
| version_header | YES | notion(1) |
| version_constraint | YES | remotion(1) |
| error_handling_pattern | YES | drizzle_orm(1) |
| tutorial_progression | YES | drizzle_orm(2) |
| design_rationale | NEVER | — |
| conceptual_explanation | NEVER | — |
| quickstart_flow | NEVER | — |

**11/14 kinds fired on real data. 3 never fired.**

The 3 never-fired kinds (`design_rationale`, `conceptual_explanation`, `quickstart_flow`)
all require structured heading patterns (`## Why`, `## Design`, `## Getting Started`)
or mental-model language (`think of it as`, `under the hood`). These patterns exist in
original documentation but are stripped during HTML sanitization — the raw captures
contain the HTML-rendered version where headings become text fragments without markdown
`##` markers. This is a **preprocessing gap**, not a regex gap.

---

### 9.4 Pattern Contribution Before vs After

| Tool | Pre-P7 Patterns | Phase 7 Patterns | Total | Phase 7 % |
|------|-----------------|------------------|-------|-----------|
| notion | 0 | 1 | 1 | 100% |
| stripe | 1 | 8 | 9 | 89% |
| posthog | 6 | 7 | 13 | 54% |
| drizzle_orm | 55 | 4 | 59 | 7% |
| remotion | 2 | 12 | 14 | 86% |
| higgsfield | 0 | 1 | 1 | 100% |
| clo3d | 0 | 1 | 1 | 100% |
| shadcn_ui | 5 | 3 | 8 | 38% |
| **TOTAL** | **69** | **37** | **106** | **35%** |

Phase 7 patterns now represent 35% of all extracted patterns. More importantly,
they are the **only** patterns that reach the 4 previously-uncovered sections —
pre-Phase-7 patterns mapped exclusively to SDK Idioms, Core Operations, and Data Model.

---

### 9.5 Quality Assessment — False Positives

**18 genuine signals, 2 false positives detected.**

| Tool | Kind | Issue |
|------|------|-------|
| higgsfield | edge_case_documentation | Matched "Your browser does not support the video" — HTML fallback text, not real edge case documentation |
| clo3d | tradeoff_reasoning | Matched Zendesk cookie consent boilerplate — not design trade-off content |

**False positive rate: 2/37 = 5.4%.** Both false positives came from the two
extreme-difficulty tools (Higgsfield, CLO3D) where the raw captures are dominated
by marketing/boilerplate content. The extractors fired correctly on the regex patterns
but the underlying content was non-technical noise.

For the 6 tools with real documentation, the false positive rate is **0/35 = 0%**.

---

### 9.6 "Sourced Structurally" vs "Actually Useful"

Not all recovered sections are equally useful. Assessment:

| Section | Recovery | Structural Quality | Actually Useful? |
|---------|----------|-------------------|-----------------|
| Design Intent | 6/8 | `tradeoff_reasoning` + `comparison_table` carry real signal | **Yes** — Stripe's agentic commerce trade-offs, PostHog's comparison tables, Drizzle's ORM comparison data are genuinely useful for the TME section |
| Operational Behavior | 6/8 | `warning_admonition` + `retry_backoff_pattern` carry real signal | **Yes** — Stripe's 429 retry docs, PostHog's CSP warnings, shadcn's config caveats are real operational knowledge |
| Version Pinning | 3/8 | `version_header` hit Notion-Version header; `pinned_dependencies` hit Remotion's package.json; `version_pin_guidance` hit Stripe's API versioning guidance | **Mixed** — Notion and Stripe versions are genuinely useful; Remotion's package.json is structural but low TME value (it's internal monorepo deps, not user-facing version pins) |
| Conceptual Model | 1/8 | Only `tutorial_progression` fired (Drizzle's "Step 1/2/3" setup guide) | **Marginal** — the Drizzle tutorial steps are real but shallow; conceptual model needs richer "how it works" content that the extractors cannot reach |

---

### 9.7 Sections Still at Zero After Phase 7

The following sections remain uncovered across the full 8-tool batch even with
Phase 7 extractors:

**Still 0/8 (unchanged):**
- Rate Limits (7/8 uncovered in baseline, the 1 was Stripe prose)

**Still very low:**
- Conceptual Model and Solution Recipes: 1/8 (only Drizzle)
- Version Pinning: 3/8 (only tools with explicit API versioning or monorepo manifests)

The original 19-section TME model has sections that require qualitatively different
evidence than what regex extraction can provide:

- **Rate Limits** — these are in API reference tables, not prose or code patterns
- **Conceptual Model** — requires understanding of "how it works" explanations that
  live in rendered docs with HTML heading structure, not markdown
- **Anti-Patterns** — requires reasoning about what NOT to do (negative knowledge)

---

### 9.8 Answers

**1. Did Phase 7 materially improve real coverage?**

Yes. +16 sections, +10.5 percentage points (28.3% → 38.8%). This is the single
largest coverage gain from any pipeline change to date. Phase 7 patterns account
for 35% of all extracted patterns and are the only extraction path that reaches
4 of the 19 TME sections.

**2. Which of the 4 zero sections improved most?**

**Design Intent and Tradeoffs** and **Operational Behavior and Edge Cases** —
both recovered 6/8 tools (75%). These sections have the strongest structural
signals: comparison tables, warning admonitions, trade-off language, and
error-handling code are common in real documentation and survive HTML rendering.

**3. Which still remain fundamentally hard?**

**Conceptual Model and Solution Recipes** — only 1/8 recovered. The 3 pattern
kinds targeting this section (`quickstart_flow`, `conceptual_explanation`,
`tutorial_progression`) have a fundamental problem: quickstart headings use
markdown `##` syntax that doesn't survive HTML rendering into raw captures,
and "mental model" language is genuinely rare in API documentation. Only tools
with explicit numbered tutorial steps (like Drizzle's setup guide) produce
signal. This section may need a different extraction strategy entirely — either
heading recovery during HTML preprocessing, or LLM-assisted classification.

**4. What is now the single dominant bottleneck?**

**HTML heading structure loss during capture preprocessing.** Three Phase 7
pattern kinds never fired (`design_rationale`, `conceptual_explanation`,
`quickstart_flow`) because they rely on markdown heading patterns (`## Why`,
`## Getting Started`, `## Concepts`) that don't exist in HTML-rendered
captures. The raw captures contain `<h2>Getting Started</h2>` but
`preprocess_for_extraction()` strips HTML tags, leaving "Getting Started" as
plain text without the `##` marker the regex expects.

This is a solvable preprocessing gap: converting HTML headings to markdown
headings during the code-preserving sanitization pass would unlock all 3
never-fired kinds. Estimated impact: +3-5 additional section recoveries
across the batch, primarily for Conceptual Model and Version Pinning
(many tools have "## Versioning" or "## Getting Started" headings).

---

### 9.9 Updated Raw Data Summary (Phase 7)

| Tool | Before | After | P7 Patterns | P7 Kinds Fired | New Sections | FP |
|------|--------|-------|-------------|----------------|-------------|-----|
| notion | 4/19 | 5/19 | 1 | version_header | Version Pinning | 0 |
| stripe | 13/19 | 16/19 | 8 | retry_backoff, tradeoff, edge_case, version_pin | +3 sections | 0 |
| posthog | 10/19 | 12/19 | 7 | comparison, tradeoff, warning | +2 sections | 0 |
| drizzle_orm | 6/19 | 9/19 | 4 | comparison, error_handling, tutorial | +3 sections | 0 |
| remotion | 5/19 | 8/19 | 12 | version, pinned_deps, tradeoff, edge_case | +3 sections | 0 |
| higgsfield | 0/19 | 1/19 | 1 | edge_case | +1 section | 1 |
| clo3d | 0/19 | 1/19 | 1 | tradeoff | +1 section | 1 |
| shadcn_ui | 5/19 | 7/19 | 3 | tradeoff, warning | +2 sections | 0 |
| **TOTAL** | **43/152** | **59/152** | **37** | **11/14 fired** | **+16 sections** | **2** |

---

## Phase 8 — HTML Structure Preservation

**Date:** 2026-04-09
**Target:** Restore heading semantics lost during preprocessing so heading-dependent extractors can fire.

### Root Cause

`preprocess_for_extraction()` in `extraction.py` replaced ALL HTML tags
(including `<h1>`–`<h4>`) with bare newlines via `_TAG_RE.sub("\n", ...)`.
This destroyed the structural information that 3 extractors depend on:

- `design_rationale` — requires `^#{1,4}\s+(?:why|design|philosophy|...)` headings
- `quickstart_flow` — requires `^#{1,4}\s+(?:getting started|quickstart|...)` headings
- `conceptual_explanation` — requires 2+ conceptual phrases per page (not heading-dependent)

### Changes Made

1. **Heading preservation** (`preprocess_for_extraction`):
   - Added `_HEADING_TAG_RE` to convert `<h1>`–`<h4>` → `# `–`#### ` markdown markers
   - Runs BEFORE generic tag stripping so heading semantics survive
   - Nested tags inside headings (e.g. `<a>`, `<code>`) are stripped from heading content

2. **Block boundary preservation**:
   - Added `_BLOCK_BOUNDARY_RE` to ensure block-level elements (`<p>`, `<div>`, `<section>`, etc.) produce newline boundaries
   - Blank line runs capped at 2 to prevent noise inflation

3. **Heading+body extraction** (`_heading_with_body` helper):
   - New utility for extractors that need heading + following paragraph content
   - Bridges the double-newline gap between heading markers and body text
   - Grabs up to 2 body chunks (handles sub-heading + prose pattern)
   - Used by `_extract_design_intent` and `_extract_conceptual_model`

### Before vs After (5-tool batch: posthog, drizzle_orm, notion, clo3d, remotion)

| Extractor Kind          | Before | After | Delta |
|------------------------|--------|-------|-------|
| design_rationale       | 1      | 3     | +2    |
| quickstart_flow        | 0      | 2     | +2    |
| conceptual_explanation | 0      | 0     | 0     |
| stepwise_workflow      | 0      | 2     | +2 (bonus) |
| comparison_table       | 5      | 5     | 0     |
| tradeoff_reasoning     | 4      | 4     | 0     |
| tutorial_progression   | 2      | 2     | 0     |
| ordered_workflow       | 1      | 1     | 0     |
| **TOTAL**              | **13** | **19**| **+6 (+46%)** |

### New fires (previously-dead sources now producing patterns)

| Tool | Source | Kind |
|------|--------|------|
| drizzle_orm | orm.drizzle.team/docs/overview | design_rationale |
| remotion | github.com/remotion-dev/remotion | design_rationale |
| drizzle_orm | orm.drizzle.team/docs/cache | quickstart_flow |
| notion | developers.notion.com/reference | quickstart_flow |
| drizzle_orm | orm.drizzle.team/docs/connect-effect-postgres | stepwise_workflow |
| drizzle_orm | orm.drizzle.team/docs/upgrade-v1 | stepwise_workflow |

### Conceptual Model Section Coverage Improvement

The Conceptual Model and Solution Recipes section was previously 0/8 across
the original batch (Phase 7 note: "always uncovered"). After Phase 8:

- drizzle_orm: now receives `quickstart_flow` pattern evidence from cache docs
- notion: now receives `quickstart_flow` pattern evidence from API reference intro

### Regressions

**None.** All existing extractors maintain identical firing rates.
Full author pipeline tested on drizzle_orm — verifier passed, no new failures.

### conceptual_explanation: Why It Didn't Fire

Not a preprocessing issue. The regex requires 2+ matches of phrases like
"under the hood", "mental model", "think of it as" in a single page. Across
all 58 raw captures in the 5-tool batch, no single page contains 2+ such
phrases. The headings are now visible; the captured docs simply don't use
enough conceptual language to cross the threshold. This is a data limitation,
not a code limitation.

### Success Criteria Evaluation

| Criterion | Result |
|-----------|--------|
| ≥2 of 3 previously-dead extractors now fire | **PASS** (design_rationale + quickstart_flow) |
| Measurable improvement in Conceptual Model coverage | **PASS** (+2 quickstart_flow patterns) |
| No increase in false positives | **PASS** (0 new FP, 0 regressions) |

---

## Phase 8 Re-Run — HTML Structure Preservation Impact

**Date:** 2026-04-09
**Method:** Full 8-tool re-extraction batch. For each tool, the *latest*
research artifact's raw captures were loaded from disk and run through
the complete extraction + mapping + drafting pipeline using the current
Phase 8 code. No re-fetching — same raw captures as prior phases.

Phase 8 converted `<h1>`–`<h4>` HTML tags to markdown `#`–`####` markers
during `preprocess_for_extraction()`, preserving heading structure that
three Phase 7 extractors depend on (`design_rationale`, `quickstart_flow`,
`conceptual_explanation`). Also added block boundary preservation for
`<p>`, `<div>`, `<section>` elements.

---

### 10.1 Overall Coverage: Phase 6 → Phase 7 → Phase 8

| Phase | Sourced | Total | Coverage | Delta |
|-------|---------|-------|----------|-------|
| Phase 6 (baseline) | 43 | 152 | 28.3% | — |
| Phase 7 (code/config extractors) | 59 | 152 | 38.8% | +10.5pp |
| **Phase 8 (HTML heading preservation)** | **60** | **152** | **39.5%** | **+0.7pp** |

Average sourced sections per tool: **7.5 / 19** (up from 5.4 at Phase 6).

---

### 10.2 Per-Tool Comparison: Phase 6 → Phase 8

| Tool | Phase 6 | Phase 7 | Phase 8 | Delta (P6→P8) | New in P8 |
|------|---------|---------|---------|---------------|-----------|
| stripe | 13/19 | 16/19 | **16/19** | +3 | — |
| posthog | 10/19 | 12/19 | **12/19** | +2 | — |
| drizzle_orm | 6/19 | 9/19 | **9/19** | +3 | — |
| remotion | 5/19 | 8/19 | **8/19** | +3 | — |
| shadcn_ui | 5/19 | 7/19 | **8/19** | +3 | Conceptual Model |
| notion | 4/19 | 5/19 | **6/19** | +2 | Conceptual Model |
| higgsfield | 0/19 | 1/19 | **1/19** | +1 | — |
| clo3d | 0/19 | 1/19 | **0/19** | 0 | — (false positive removed) |

**Phase 8-specific gains:**
- notion: +1 section (Conceptual Model via `quickstart_flow` from API reference headings)
- shadcn_ui: +1 section (Conceptual Model via `quickstart_flow` from docs headings)
- clo3d: -1 section (Phase 7's `tradeoff_reasoning` was a false positive from Zendesk boilerplate; the source is correctly classified UNKNOWN, blocking extraction)

**Net Phase 8 delta: +1 section-slot** (60 vs 59). The true contribution is
quality improvement: 2 genuine section recoveries, 1 false positive removed.

---

### 10.3 The 4 Historically Weak Sections — Recovery Status

| Section | Phase 6 | Phase 7 | Phase 8 | Recovery Rate |
|---------|---------|---------|---------|--------------|
| Design Intent and Tradeoffs | 0/8 | 6/8 | **5/8** | 62.5% |
| Operational Behavior and Edge Cases | 0/8 | 6/8 | **5/8** | 62.5% |
| Version Pinning | 0/8 | 3/8 | **3/8** | 37.5% |
| Conceptual Model and Solution Recipes | 0/8 | 1/8 | **3/8** | 37.5% |

Design Intent and Operational Behavior dropped from 6/8 to 5/8 vs Phase 7
because Phase 7 counted clo3d (false positive tradeoff_reasoning) and
higgsfield (edge_case from browser fallback text). Phase 8's UNKNOWN
classification correctly blocks these.

**Conceptual Model is the biggest Phase 8 winner:** 1/8 → 3/8. The
`quickstart_flow` extractor now fires on HTML headings like
`<h2>Getting Started</h2>` that Phase 7 couldn't see. This pattern
fired on notion (API reference intro), drizzle_orm (cache docs), and
shadcn_ui (component setup docs).

---

### 10.4 Remaining Zero Sections

No section is at 0/8 after Phase 8. The weakest sections are:

| Section | Count | Tools | Bottleneck |
|---------|-------|-------|-----------|
| Rate Limits | 1/8 | stripe | Only in explicit rate-limit docs (API tables, not prose) |
| Anti-Patterns | 1/8 | stripe | Negative knowledge — docs rarely say "don't do X" in structured ways |
| Webhooks and Events | 2/8 | stripe, posthog | Only tools with webhook documentation |
| Limits | 2/8 | stripe, posthog | Appears in API reference tables, not prose paragraphs |
| Cost Model | 2/8 | stripe, remotion | Pricing pages are marketing, not prose docs |
| Authentication | 2/8 | stripe, posthog | Auth docs often code-heavy; prose gate rejects |
| Ecosystem Position | 2/8 | stripe, shadcn_ui | Requires comparative language rare in first-party docs |
| Trajectory | 2/8 | drizzle_orm, remotion | Only in changelogs and roadmap pages |

---

### 10.5 Per-Section Full Coverage Map

| Section | Count | Phase 6 | Sourced In |
|---------|-------|---------|-----------|
| Data Model | **7/8** | 6/8 | notion, stripe, posthog, drizzle_orm, remotion, higgsfield, shadcn_ui |
| Problem-Solution Map | **6/8** | 6/8 | notion, stripe, posthog, drizzle_orm, remotion, shadcn_ui |
| SDK Idioms | **5/8** | 5/8 | stripe, posthog, drizzle_orm, remotion, shadcn_ui |
| Design Intent | **5/8** | 0/8 | stripe, posthog, drizzle_orm, remotion, shadcn_ui |
| Operational Behavior | **5/8** | 0/8 | stripe, posthog, drizzle_orm, remotion, shadcn_ui |
| Core Operations | **4/8** | 4/8 | notion, stripe, posthog, drizzle_orm |
| Industry Expert | **4/8** | 4/8 | stripe, posthog, drizzle_orm, shadcn_ui |
| Version Pinning | **3/8** | 0/8 | notion, stripe, remotion |
| Conceptual Model | **3/8** | 0/8 | notion, drizzle_orm, shadcn_ui |
| Authentication | 2/8 | 2/8 | stripe, posthog |
| Pagination | 2/8 | 2/8 | notion, posthog |
| Error Codes | 2/8 | 2/8 | stripe, posthog |
| Webhooks | 2/8 | 2/8 | stripe, posthog |
| Limits | 2/8 | 2/8 | stripe, posthog |
| Cost Model | 2/8 | 2/8 | stripe, remotion |
| Ecosystem Position | 2/8 | 2/8 | stripe, shadcn_ui |
| Trajectory | 2/8 | 2/8 | drizzle_orm, remotion |
| Rate Limits | 1/8 | 1/8 | stripe |
| Anti-Patterns | 1/8 | 1/8 | stripe |

---

### 10.6 Grounding Breakdown

| Grounding Type | Phase 6 | Phase 8 | Change |
|---------------|---------|---------|--------|
| uncovered | 109 (71.7%) | 92 (60.5%) | -17 slots |
| prose | 37 (24.3%) | 38 (25.0%) | +1 |
| pattern | 2 (1.3%) | 18 (11.8%) | **+16** |
| mixed | 4 (2.6%) | 4 (2.6%) | 0 |

**Structured patterns grew from 1.3% to 11.8% of all grounding** — a 9x increase.
Patterns are now the second-largest grounding source. The Phase 7+8 extractors
account for all 16 new pattern-grounded sections.

---

### 10.7 Pattern Contribution

| Kind | Count | Tools | Target Section |
|------|-------|-------|---------------|
| install_command | 22 | drizzle_orm | SDK Idioms |
| quickstart_flow | 10 | notion, drizzle_orm, shadcn_ui | Conceptual Model |
| json_schema_fields | 6 | posthog, shadcn_ui | Data Model |
| tradeoff_reasoning | 5 | stripe, remotion, shadcn_ui | Design Intent |
| pinned_dependencies | 5 | remotion | Version Pinning |
| retry_backoff_pattern | 3 | stripe | Operational Behavior |
| edge_case_documentation | 3 | stripe, remotion | Operational Behavior |
| warning_admonition | 3 | posthog, shadcn_ui | Operational Behavior |
| setup_flow | 3 | remotion, shadcn_ui | SDK Idioms |
| version_pin_guidance | 2 | stripe | Version Pinning |
| function_signature | 2 | posthog, drizzle_orm | Core Operations |
| comparison_table | 2 | posthog, drizzle_orm | Design Intent |
| version_header | 1 | notion | Version Pinning |
| parameter_definitions | 1 | drizzle_orm | Core Operations |
| design_rationale | 1 | drizzle_orm | Design Intent |
| error_handling_pattern | 1 | drizzle_orm | Operational Behavior |
| config_block | 1 | shadcn_ui | SDK Idioms |

**Total: 71 patterns across 17 kinds.** Phase 8's heading preservation enabled
`quickstart_flow` (10 patterns across 3 tools) and `design_rationale` (1 pattern)
that were previously blocked by HTML tag stripping.

---

### 10.8 False Positives / Regressions

**False positives removed:** 1 (CLO3D `tradeoff_reasoning` from Zendesk boilerplate —
now correctly blocked by UNKNOWN source classification).

**New false positives:** 0. All 71 extracted patterns target real documentation content.

**Regressions:** 0. No tool lost coverage from Phase 6 → Phase 8. CLO3D's apparent
loss (0/19 vs Phase 7's 1/19) is a correction, not a regression.

---

### 10.9 Answers

**1. What is the new overall coverage rate?**

**39.5%** (60/152 section-slots). Up from 28.3% at Phase 6 baseline. The Phase 7+8
extraction improvements account for all 17 additional section recoveries.

**2. Which section is now the single hardest to recover?**

**Anti-Patterns** (1/8, only Stripe). This section requires "negative knowledge" —
documentation about what NOT to do. First-party docs rarely structure this as
prose paragraphs; it appears in forum posts, blog articles, and Stack Overflow
answers that the research agent's same-host-only crawl policy correctly excludes.
No regex extractor can synthesize negative knowledge from positive documentation.

Rate Limits (also 1/8) is close behind but has a clearer path: API reference
tables with rate limit values could be extracted with a table-aware extractor.

**3. What is the single next bottleneck?**

**The prose quality gate's interaction with code-heavy documentation.**

Evidence:
- Authentication (2/8): auth code examples dominate but fail `is_prose_block()`
- shadcn_ui has 9.2MB of fetched content but only 8/19 coverage because component
  docs are >70% code blocks with props tables
- The prose gate's 65% letter ratio and 8% symbol ceiling correctly reject code,
  but this means tools whose docs are code-example-first (component libraries,
  CLIs, ORMs) systematically underperform

The structured pattern extractors partially address this (they read code-preserved
text, not prose-gated text), but they only target specific pattern shapes. The gap
is documentation that explains concepts *through code examples* — not extractable
by prose keyword matching, not matching any pattern regex.

**4. Should we keep improving extraction, or is it time to improve schema / operator UX instead?**

**Pivot to operator UX.**

Justification:
- Extraction has gone from 28.3% → 39.5% across three phases of improvements
  (Phase 5 classification, Phase 7 code/config extractors, Phase 8 HTML
  heading preservation). Each phase delivered diminishing returns: +0% → +10.5pp
  → +0.7pp.
- The remaining uncovered sections fall into three categories:
  1. **Tool-specific** (webhooks, pagination, cost model) — only tools with that
     feature can have the section. Cannot be fixed by extraction improvements.
  2. **Negative/synthetic knowledge** (anti-patterns) — requires reasoning that
     no regex extractor can provide. Needs LLM or human input.
  3. **Code-embedded knowledge** (authentication, SDK idioms for code-heavy tools)
     — the information is in code blocks the prose gate rejects. Loosening the
     gate would increase false positives faster than true positives.
- The honest extraction ceiling for regex-only pipeline is approximately **45-50%**
  for tools with strong docs, and **0-5%** for tools with weak docs. Further
  extraction investment has diminishing ROI.
- The higher-leverage move is making the **operator UX** better: faster skill
  review, easier manual section filling, clearer gap reports. The pipeline does
  the sourcing; a human should fill the synthesis. The pipeline should make that
  handoff as efficient as possible.

Specifically recommended:
1. **Gap report per tool** — "here are your 11 uncovered sections, here are
   the raw excerpts that *almost* matched, here's what a human should add"
2. **Section editor workflow** — let the operator fill individual sections
   from a structured prompt, not from scratch
3. **Batch status dashboard** — one-page view of all skills with coverage
   heatmap and staleness indicators

---

### 10.10 Updated Raw Data Summary (Phase 8)

| Tool | Phase 6 | Phase 8 | Patterns | New Sections (vs P6) | Bytes |
|------|---------|---------|----------|---------------------|-------|
| notion | 4/19 | 6/19 | 2 | Version Pinning, Conceptual Model | 758K |
| stripe | 13/19 | 16/19 | 8 | Design Intent, Operational Behavior, Version Pinning | 6.5M |
| posthog | 10/19 | 12/19 | 6 | Design Intent, Operational Behavior | 2.6M |
| drizzle_orm | 6/19 | 9/19 | 28 | Design Intent, Operational Behavior, Conceptual Model | 1.9M |
| remotion | 5/19 | 8/19 | 11 | Design Intent, Operational Behavior, Version Pinning | 40K |
| higgsfield | 0/19 | 1/19 | 0 | Data Model (prose) | 2.0M |
| clo3d | 0/19 | 0/19 | 0 | — | 608K |
| shadcn_ui | 5/19 | 8/19 | 16 | Design Intent, Operational Behavior, Conceptual Model | 9.2M |
| **TOTAL** | **43** | **60** | **71** | **+17 sections** | **23.6M** |
