# Phase 87 — Leverage + Resource / Tool Taxonomy v1

**Date**: 2026-05-03
**Status**: Complete
**Extends**: Phase 86 (EOS Tomorrow Operating Loop v1)
**Tests**: 118 passing (Phase 87), 1115 total regression (Phase 80–87)
**Safety**: 8 modules checked, 0 violations, 0 warnings
**Hard rules**: 15

## Executive Summary

Phase 87 introduces the Leverage + Resource / Tool Taxonomy — a typed
advisory system that helps the user identify and apply the highest-leverage
path under real-world constraints. Everything is modeled as either a
resource (what you have) or a tool (what you use), and the taxonomy maps
both into leverage types that the scoring and recommendation engines
evaluate.

The system produces typed recommendations: DO_SELF for core judgment tasks,
AUTOMATE for repeated rule-based work, TEMPLATE for reusable processes,
DELEGATE for bottleneck resolution, RESEARCH when evidence is insufficient,
and 10 more action types. The Initiate Arena first workflow receives 9
specific leverage recommendations out of the box.

Integration with Phase 86's Tomorrow Operating Loop is additive: the daily
briefing can be enriched with leverage recommendations without changing any
existing function signatures.

Advisory-only. No execution. No mutation. No adapter calls. No LLM calls.
Deterministic v1.

## Roadmap Reconciliation Note

Phase numbering was corrected: Phase 86 was completed as "EOS Tomorrow
Operating Loop v1" (not Leverage as originally expected). Phase 87 now
implements what was originally slated as Phase 86. See
`docs/system/roadmap_reconciliation_phase86_shift.md` for full details.
The war sprint manifest has been updated to reflect the corrected numbering.

## Why Phase 87 Follows EOS Tomorrow Operating Loop

The Tomorrow Loop (Phase 86) is the daily operating cycle. The Leverage
Taxonomy (Phase 87) tells the user *what to focus on* within that cycle.
Together they answer: "What should I do today?" (Loop) and "What's the
highest-leverage way to do it?" (Leverage).

## Leverage Optimization Principle

> Maximize human capability by identifying and applying the highest-leverage
> path under real-world constraints.

Core insight: the user operates as architect/orchestrator, not bottleneck.
The system classifies every possible action by leverage type, scores it
across 9 dimensions, and recommends the appropriate action level (do self,
delegate, automate, template, eliminate, etc.).

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `umh/leverage/__init__.py` | 8 | Package marker |
| `umh/leverage/contracts.py` | ~310 | 7 enums, 7 normalizers, 5 dataclasses, helpers |
| `umh/leverage/resources.py` | ~180 | ResourceProfile factory, 18 default resources, classification |
| `umh/leverage/tools.py` | ~230 | ToolProfile factory, 18 default tools, classification |
| `umh/leverage/taxonomy.py` | ~290 | 20 LeverageTaxonomyNodes, mapping functions |
| `umh/leverage/scoring.py` | ~220 | 10 scoring functions, LeverageScorecard, ranking |
| `umh/leverage/recommendations.py` | ~300 | Action recommendation logic, 9 Initiate Arena defaults |
| `umh/leverage/views.py` | ~270 | 7 UI-safe view types, converters, dashboard builder |
| `umh/leverage/safety.py` | ~180 | AST-based import + execution pattern checking |
| `tests/test_phase87_leverage_resource_tool_taxonomy.py` | ~870 | 118 tests across 12 test classes |
| `docs/system/roadmap_reconciliation_phase86_shift.md` | ~60 | Roadmap correction documentation |

## Files Modified

| File | Change | Risk |
|------|--------|------|
| `umh/tomorrow/views.py` | Added `enrich_brief_with_leverage()` — additive only | LOW |
| `docs/strategy/war_sprint_context_manifest.md` | Updated phase numbering + reconciliation note | LOW |

## Leverage Types (21)

HUMAN, CODE_SOFTWARE, CONTENT_MEDIA, CAPITAL, SYSTEMS_PROCESS, AI_MODEL,
NETWORK_RELATIONSHIP, ATTENTION_FOCUS, DATA, DISTRIBUTION, BRAND,
PHYSICAL_INFRASTRUCTURE, ROBOTICS_AUTOMATION, REGULATORY, TIME, ENERGY,
KNOWLEDGE, REAL_ESTATE, MANUFACTURING, FULFILLMENT, UNKNOWN

## Resource Types (24)

HUMAN, MONEY, TIME, ENERGY, ATTENTION, DATA, CODE, TOOL, PLATFORM,
AUDIENCE, NETWORK, BRAND, PROCESS, TEMPLATE, LIBRARY, AI_MODEL,
REAL_ESTATE, EQUIPMENT, MANUFACTURING, FULFILLMENT, ROBOTICS,
MEDIA_ASSET, KNOWLEDGE_ASSET, UNKNOWN

## Tool Types (16)

SOFTWARE, AI_MODEL, HUMAN_EXPERT, TEMPLATE, WORKFLOW, CAPITAL_INSTRUMENT,
MEDIA_CHANNEL, PHYSICAL_ASSET, ROBOTIC_SYSTEM, API, COMPUTER_USE,
MANUAL_PROCESS, DOCUMENT, COURSE_CONTENT, SOCIAL_PLATFORM, UNKNOWN

## Scoring Model

9 dimensions, all bounded [0, 1]:

| Dimension | Weight | Purpose |
|-----------|--------|---------|
| Multiplier | 0.15 | How much output per unit input |
| Time to Impact | 0.10 | How soon value arrives |
| Cost Efficiency | 0.10 | Input cost relative to output |
| Risk-Adjusted Value | 0.15 | Multiplier penalized by risk and confidence |
| Reversibility | 0.05 | Can you undo if wrong |
| Compounding Potential | 0.15 | Does this get better over time |
| Strategic Alignment | 0.15 | Does this serve the north star |
| Attention Efficiency | 0.10 | How much founder attention required |
| Dependency Risk | 0.05 | External dependency exposure |

Adjustments: high dependency risk → 0.8x penalty. Low reversibility + high
risk → 0.7x penalty. High compounding → 1.15x bonus.

## Recommendation Model

14 action types with deterministic rules:

| Action | When |
|--------|------|
| DO_SELF | Core judgment, brand presence, high-trust selling |
| DELEGATE | Human bottleneck, non-core task |
| AUTOMATE | Repeated, rule-based, low-risk |
| TEMPLATE | Repeated but needs customization |
| HIRE | Ongoing need exceeds ad hoc delegation |
| BUY | Cheaper than building, not strategic |
| PARTNER | Complementary capability needed |
| OUTSOURCE | Execution needed, not strategic |
| SYSTEMIZE | Repeated and chaotic workflow |
| ELIMINATE | Low leverage, no strategic value |
| DEFER | Dependencies missing, risk too high |
| RESEARCH | Evidence insufficient |
| SIMULATE | High outcome uncertainty |
| APPROVE_AND_EXECUTE_LATER | Real-world action needs governance |

## EOS Tomorrow Loop Integration

`enrich_brief_with_leverage()` in `umh/tomorrow/views.py`:
- Additive only — adds to `metadata["leverage"]`
- No existing function signatures changed
- Phase 86 tests pass unmodified (81/81)
- Optional — brief works without leverage data

## Registry / Observability / API / CLI

Deferred. The existing modules have complex dependency chains and
modifications risk breaking confirmed working components. Integration
points are documented for Phase 88+.

## Safety Validation

- **Modules checked**: 8 (all leverage/*.py except __init__)
- **Forbidden imports**: 0 (subprocess, requests, httpx, aiohttp, socket, selenium, playwright, smtplib, telegram, discord)
- **Forbidden module prefixes**: 0 (umh.adapters, umh.execution, umh.governance, umh.memory, umh.storage)
- **Execution patterns**: 0 (execute, run_action, send_message, post, delete, create_resource, mutate, promote_memory)

## Tests

| Class | Tests | Covers |
|-------|-------|--------|
| TestContractNormalization | 8 | All 7 normalizers + unknown degradation |
| TestContractSerialization | 5 | All 5 dataclass to_dict/from_dict round-trips |
| TestResources | 10 | 9 named defaults + classification |
| TestTools | 11 | 10 named defaults + classification |
| TestTaxonomy | 20 | 16 leverage types + examples, failure modes, resource/tool mapping |
| TestScoring | 13 | 9 bounded scores + dependency/compounding effects + ranking |
| TestRecommendations | 14 | 7 action rules + 5 Initiate Arena checks + guardrails/non-actions |
| TestEOSIntegration | 2 | Brief enrichment + import verification |
| TestViews | 7 | 6 view serializations + secret omission |
| TestSafety | 6 | Module scan + 4 temp fixture detections + recommendation check |
| TestLayering | 13 | Per-file forbidden import checks + adapter/execution/governance/memory/model |
| TestPhase87Regression | 9 | Phase 80–87 import smoke tests |
| **Total** | **118** | |

## Regression

- **Phase 87 tests**: 118/118 passing
- **Phase 80–87 regression**: 1115/1115 passing
- **Phase 86 tests**: 81/81 passing (unchanged)
- **Safety validation**: 8 modules, 0 violations

## Known Limitations

- Advisory only — no execution
- Deterministic scoring — no ML/LLM enhancement
- No live model calls — all logic is rule-based
- No memory promotion — data stays in typed contracts
- No composition engine yet (Phase 90)
- No full template/library integration yet (Phase 88/89)
- Registry/observability/API/CLI integration deferred
- Default resources/tools are static — no dynamic discovery

## Is Phase 88 Template System Safe?

Yes. Phase 88 (Template System v1) can safely build on:
- Leverage taxonomy provides the "what type of template" classification
- Resource/tool profiles inform what templates need to produce
- Scoring model can evaluate template effectiveness
- Recommendation engine can suggest when to template vs. automate
- No Phase 87 code needs modification — Phase 88 extends, not changes
