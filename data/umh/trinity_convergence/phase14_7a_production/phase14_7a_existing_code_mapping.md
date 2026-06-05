---
phase: "14.7A"
artifact: existing_code_mapping
created: "2026-06-04"
allows_implementation: true
product_name: "Universal Meta Harness"
---

# Phase 14.7A — Existing Code Mapping

## Summary

~80% of Stage 1 infrastructure exists as production code.
Zero components require building from scratch.
The work is WIRING existing production classes through HTTP routes and connecting Cockpit panels.

## Component Classification

| Component | Status | Key File(s) | LOC | Gap |
|-----------|--------|-------------|-----|-----|
| Reality Model | PARTIALLY_WIRED | substrate/reality_model/{canonical,instance,simulation}.py | 735 | **ZERO HTTP routes existed (now added in WP-1.1)** |
| Memory System | PRODUCTION_READY | substrate/state/memory/memory.py | 1040 | Route upgraded from raw JSONL to typed classes |
| Execution Spine | PRODUCTION_READY | substrate/execution/spine.py | 522 | `/execution/status` was static stub (now wired in WP-1.4) |
| Governance | PRODUCTION_READY | substrate/governance/*.py + substrate/control_plane/governance.py | ~900 | Full chain works; approval CRUD in Neon |
| Work Packets | PARTIALLY_WIRED | substrate/organism/work_packet_engine.py + universal_work_queue.py | ~640 | Routes exist; end-to-end lifecycle needs verification |
| Agent/Tool Routing | PRODUCTION_READY | adapters/models/model_router.py | 1442 | call_with_fallback production workhorse |
| Self-Improvement | PARTIALLY_WIRED | substrate/organism/autonomous_cadence.py + self_build_queue.py | ~1030 | dry_run_only enforced; candidate supply needs wiring |
| Intent Classification | PRODUCTION_READY | substrate/organism/intent_classifier.py | 325 | Deterministic, 17 domains, no LLM required |
| Cockpit API | PRODUCTION_READY | transports/api/cockpit.py + 12 auxiliary routers | ~5500 | 60+ routes; reality model routes added |
| Cockpit UI | PARTIALLY_WIRED | cockpit/src/renderer/panels/*.tsx (27 panels) | ~5200 | WorldModelPanel needs rewiring to reality model routes |

## Files Modified (Wave 1)

1. `transports/api/cockpit_reality_model_routes.py` — NEW (WP-1.1)
   - 15 HTTP routes for canonical patterns, instance observations, simulation
   - Follows cockpit_*_routes.py pattern (configure + _build_router)
   - Mounted via _mount_reality_model_router() in cockpit.py

2. `transports/api/cockpit.py` — MODIFIED (WP-1.3, WP-1.4)
   - `/memory` route: upgraded from raw JSONL to ConversationMemory + AgentMemory + ontology fallback
   - `/execution/status`: wired from static stubs to live organism/spine/work packet data
   - `/execution/start`: requires packet_id, checks approval gates, uses valid lifecycle transitions
   - `/execution/stop`: transitions to BLOCKED
   - `/execution/pause`: transitions to BLOCKED
   - `/execution/resume`: transitions from BLOCKED to CLASSIFIED
   - Reality model router mounted at end of file

3. `tests/test_phase14_7a_wave1.py` — NEW
   - 75 tests covering all Wave 1 work packets and safety gates

## Files NOT Modified (Governance Compliance)

- substrate/reality_model/*.py — READ ONLY (routes call, don't modify)
- substrate/types.py — UNCHANGED
- substrate/state/memory/memory.py — UNCHANGED
- substrate/governance/*.py — UNCHANGED
- adapters/models/model_router.py — UNCHANGED
- services/discord_bot.py — UNCHANGED
- saas/ — UNCHANGED
- projections/ — UNCHANGED
- Database schemas — NO MIGRATIONS

## Wave 1 Acceptance Criteria Status

| AC | Description | Status |
|----|-------------|--------|
| AC-1.1 | Cockpit loads without errors | EXISTING (27 panels render) |
| AC-1.2 | 5 required panels render | EXISTING (panels exist) |
| AC-2.1 | Text persisted to memory | WIRED (typed ConversationMemory) |
| AC-3.1 | Canonical model loads | PASS (production class) |
| AC-3.2 | Instance model loads | PASS (production class) |
| AC-3.3 | WorldModelPanel displays | NEEDS WIRING (WP-1.2, deferred to frontend) |
| AC-3.4 | Covers ventures/agents/files | PARTIAL (instance observations track these) |
| AC-3.5 | Confidence decay | PASS (180-day half-life canonical, 14-day instance) |
