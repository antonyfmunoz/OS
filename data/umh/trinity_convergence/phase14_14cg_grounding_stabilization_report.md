# Phase 14.14C-G: Daily Driver Grounding Stabilization Report

**Date:** 2026-06-09
**Baseline:** Phase 14.14A PARTIAL verdict
**Failure class:** Ungrounded LLM system-state hallucination

---

## Problem Statement

Phase 14.14A daily-driver acceptance identified that DEX fabricates system state when real data is unavailable. Status queries, reports, blockers, and deployment summaries returned plausible but false information when the LLM conversation path ran without injected source data.

Core failure: **the LLM fills gaps with plausible fiction instead of admitting missing data.**

---

## Architecture

### Grounding Firewall (3 layers)

1. **classify_intent()** — deterministic keyword matching routes status/VPS/action queries to governed handlers before any LLM call
2. **detect_status_seeking()** — second-pass guard inside `_handle_conversation()` and `_handle_advisor_signal()` catches status queries that slip past intent classification
3. **_route_grounded_query()** — dispatches detected status queries to type-specific grounded handlers instead of a generic fallback

### Grounded Response Contract

Every grounded response carries:
- `model_tier: "deterministic"` in metadata
- `grounding.source` — query type that was executed
- `grounding.data` — real source data
- `grounding.confidence` — `deterministic` | `partial` | `blocked`
- `grounding.missing` — list of unavailable data sources
- `grounding.freshness` — collection time in seconds

### Confidence Levels
- **deterministic** — all required sources present, answer based on real data
- **partial** — some optional sources missing, available data shown with disclosure
- **blocked** — required source unavailable, exact blocker returned

---

## Results by Workcell

### A: Grounding Firewall — PASS
- 70+ status-seeking patterns across 16 query types
- 3-layer guard prevents LLM fabrication for all status-class queries
- Missing data returns exact blocker, not hallucination

### B: Grounded Response Contract — PASS
- GroundedResult dataclass with source, freshness, data, summary, missing, confidence
- All handlers return AdvisorResponse with model_tier="deterministic" and grounding metadata
- Confidence levels (deterministic/partial/blocked) correctly assigned

### C: Deterministic Status Handlers — PASS
- 13 collectors: docker, providers, voice, vision, work_packets, blocked_packets, workcells, beast, reports, approvals, deployments, hermes, webhook
- 16 grounded handlers covering all major status surfaces
- _route_grounded_query() dispatches to type-specific handlers

### D: VPS Catalog Expansion — PASS
- Added: webhook logs, webhook restart, system health, restart services, container health, service health
- 22 keyword groups mapping natural phrasing to catalog actions
- "restart services" now routes to VPS_CONTROL instead of LLM

### E: Report Grounding — PASS
- handle_grounded_reports() reads reports.jsonl
- "What reports were created today?" returns real report data
- Pattern fix: added "what reports", "show reports", "list reports" patterns after field test caught leak

### F: Blocker Grounding — PASS
- handle_grounded_blocked() for work packet blockers
- handle_grounded_composite_blockers() checks 6 sources: work_packets, providers, beast, docker, vision, voice
- Missing sources disclosed, no false all-clear

### G: DEX Conversation Routing Guard — PASS
- Status-seeking queries cannot fall through to generic LLM conversation
- _handle_conversation() guard catches missed classifications
- _handle_advisor_signal() guard prevents fabrication through advisor path

### H: Daily Driver Failure Queue — PASS
- 8 failures captured with structured metadata
- 4 fixed this phase (F2, F4, F5, F8)
- 4 remaining documented with priority order
- File: data/umh/trinity_convergence/phase14_14_daily_driver_stabilization_queue.md

### I: Vision Grounding Guard — PASS
- "What do you see?" requires real camera frame
- No frame = "I don't have a current camera frame"
- Not streaming = "Camera is not currently streaming"
- visual_query requires vision source (required = blocked if missing)

### J: Hermes Placeholder Truthfulness — PASS
- Hermes status: configured/available/verified tri-state
- "Is Hermes available?" returns "configured but not reachable"
- Not marked healthy until is_verified() returns True

### K: Tests — PASS
- 57 tests across 15 categories (32 new)
- Categories: NoDataNoFabrication, FirewallPreventsLLM, RealDataGrounded, Hermes, Vision, ResponseFormat, ProviderMetadata, Approvals, Deployments, Reports, VisualQuery, LLMCannotFabricate, CompositeBlockers, Webhook, VPSCatalog, GroundedResponseContract, AllPatternsValid

### L: Field Tests — PASS (12/12)

| # | Query | Grounded | Source |
|---|-------|----------|--------|
| 1 | Docker container status | deterministic | Docker socket |
| 2 | What providers are online? | deterministic | MODEL_REGISTRY |
| 3 | What voice services are healthy? | deterministic | env + TTS endpoint |
| 4 | What vision services are healthy? | deterministic | vision relay |
| 5 | What camera is active? | deterministic | vision relay |
| 6 | What work packets are blocked? | deterministic | work_packets.jsonl |
| 7 | What needs approval? | deterministic | pending_approvals |
| 8 | What reports were created today? | deterministic | reports.jsonl |
| 9 | What did we deploy last? | deterministic | git log |
| 10 | Summarize current system state | deterministic | 7 collectors |
| 11 | What do you see? | deterministic | vision relay |
| 12 | Is Hermes available? | deterministic | hermes adapter |

---

## Files Changed

| File | Change |
|------|--------|
| substrate/organism/grounding_registry.py | +4 collectors, +40 patterns, +4 query types |
| substrate/organism/grounded_handlers.py | +8 handlers (voice, approvals, deployments, reports, hermes, webhook, visual, composite blockers) |
| substrate/organism/advisor_conversation.py | +_route_grounded_query() method for type-specific dispatch |
| substrate/workstation/command_router.py | +9 VPS control signals |
| substrate/workstation/vps_control_catalog.py | +3 catalog entries, +4 keyword groups, webhook log/restart support |
| tests/test_grounding_firewall.py | +32 tests across 11 new categories |
| data/umh/trinity_convergence/phase14_14_daily_driver_stabilization_queue.md | Created |

---

## Remaining Failures (Stabilization Queue)

1. **F3** — Work packet creation response formatting (returns trace ID)
2. **F6** — Work packet lifecycle (blocked by F3)
3. **F1** — System-aware "what next" (needs organism state injection into planning prompts)
4. **F7** — CC session launcher (needs mechanism to start sessions from cockpit)

---

## Verdict: SHIPPED

All acceptance criteria met:
- Grounded/status queries cannot fall through to ungrounded LLM
- Missing data returns blocker, not hallucination
- Docker/container status uses real Docker socket data
- Provider health uses real MODEL_REGISTRY data
- Report queries read real reports.jsonl
- Blocker queries use real work_packets.jsonl
- Vision claims require a real frame
- Hermes is not marked healthy until a real call succeeds
- Daily-driver stabilization queue exists with 8 failures tracked
- 12/12 field tests pass with real data or exact blockers
- 57/57 tests pass, 46/46 work lane tests pass (103 total, 0 regression)
- Final report exists
