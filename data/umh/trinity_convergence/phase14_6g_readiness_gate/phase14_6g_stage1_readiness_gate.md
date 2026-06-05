---
phase: "14.6G"
status: "DRAFT"
operator_approved: false
allows_implementation: false
date: "2026-06-04"
provenance: "READINESS_GATE"
sources:
  - "18 ratified P0 decisions (Phases 14.6C + 14.6E)"
  - "60 revised canon artifacts (Phase 14.6F)"
  - "845 tests across 14.6C/D/E/F"
  - "Codebase survey of existing substrate/adapters/transports/cockpit code"
---

# Phase 14.6G: UMH Stage 1 Functional Organism Readiness Gate

## What This Is

This document defines the implementation-readiness gate for UMH Stage 1: the minimum viable Jarvis-style organism. It is the final planning artifact before implementation begins. No source code was modified. No implementation occurred.

## Implementation Gate Status

| Gate | Status | Explanation |
|------|--------|-------------|
| operator_approved | **false** | Readiness gate = planning, not implementation |
| allows_implementation | **false** | Implementation requires explicit operator approval of Phase 14.7A |

## Stage 1 Definition (from ratified canon)

Per DEC-146C-003 (Option B, RATIFIED 2026-06-04), Stage 1 is ONE minimum viable UMH organism:

**Reality Model + Cockpit + Memory + Governed Execution Loop**

These four components are indivisible. Each increment must advance the integrated organism across all four components. Stage 1 does not require commercial-grade completeness. It requires a partially functional integrated vertical slice sufficient for the operator to actually operate through it.

## Canon Consistency Verification

### All 18 P0 Decisions Verified in Canon

| # | Decision ID | Title | Reflected In Canon |
|---|-------------|-------|--------------------|
| 1 | DEC-146C-001 | UMH Reality Model Identity | YES -- 6 primary UMH artifacts |
| 2 | DEC-146C-002 | Materialization Principle | YES -- execution boundary model, lossless canon, cockpit doctrine |
| 3 | DEC-146C-003 | Indivisible Stage 1 Organism | YES -- all cockpit readiness artifacts, lossless canon, execution boundary |
| 4 | DEC-146B-UMH-001 | Canonical Product Name | YES -- naming canonicalization, 5 primary identity docs |
| 5 | DEC-146B-UMH-002 | PHILOSOPHY.md Scope | YES -- open questions queue (RESOLVED) |
| 6 | DEC-146B-UMH-003 | Execution Path Unification | YES -- execution boundary model, open questions queue |
| 7 | DEC-146B-UMH-004 | Dead Workstation Code | YES -- implementation debt register, quarantine candidates |
| 8 | DEC-146B-UMH-005 | ProductConnectionManager | YES -- projection registration protocol |
| 9 | DEC-146B-EOS-001 | Beast Branch Promotion | YES -- EOS source truth packet |
| 10 | DEC-146B-EOS-002 | MVP Scope R1-R5 | YES -- EOS decision queue (RESOLVED) |
| 11 | DEC-146B-EOS-003 | Auth Finalization (Clerk) | YES -- EOS auth security truth |
| 12 | DEC-146B-COS-001 | CreatorOS MVP Scope | YES -- CreatorOS decision queue (RESOLVED) |
| 13 | DEC-146B-COS-002 | CreatorOS Auth (Clerk) | YES -- CreatorOS auth security truth |
| 14 | DEC-146B-COS-003 | CreatorOS Source Baseline | YES -- CreatorOS decision queue (RESOLVED) |
| 15 | DEC-146B-COS-004 | CreatorOS Module Build Sequence | YES -- CreatorOS decision queue (RESOLVED) |
| 16 | DEC-146B-LOS-001 | LyfeOS PRD v2.0 | YES -- LyfeOS source truth packet |
| 17 | DEC-146B-LOS-002 | LyfeOS Clerk Migration Timing | YES -- LyfeOS auth migration plan |
| 18 | DEC-146B-LOS-003 | LyfeOS Infrastructure (Fly.io) | YES -- LyfeOS infrastructure map |

### Consistency Checks

| Check | Result |
|-------|--------|
| Stale contradictions | **NONE FOUND** -- all 60 revised artifacts internally consistent |
| Product name | **PASS** -- "Universal Meta Harness" is canonical throughout; "Universal Mastery Hierarchy" appears only in labeled debt/gap documentation |
| System definition | **PASS** -- UMH defined as ONE integrated system, not separate products |
| Stage 1 scope | **PASS** -- defined as usable integrated vertical slice, not complete build or sequential isolated build |
| Implementation gates | **PASS** -- `allows_implementation: false` in all 60 revised artifacts |

## Codebase Reality vs Canon Gap Analysis

### The Critical Finding

The codebase survey reveals that **~80% of Stage 1 infrastructure already exists as production code**. The primary gap is not building engines but wiring existing components through Cockpit HTTP endpoints and unifying the execution path.

### Component-by-Component Status

| Component | Canon Requirement | Codebase Status | Gap Type |
|-----------|-------------------|-----------------|----------|
| Reality Model | Canonical + Instance + Simulation | All 3 classes exist, import clean | **WIRING** -- no HTTP routes expose them to Cockpit |
| Cockpit | Operator's reality-model interface | 55 TSX panels, 12+ Python route files | **WIRING** -- WorldModelPanel not connected to reality model classes |
| Memory | Conversation + Agent + Canonical stores | AgentMemory + ConversationMemory production, Neon-persisted | **WIRING** -- memory routes use raw JSONL, not typed memory classes |
| Governed Execution | 8-stage spine + risk classification | ExecutionSpine (522 lines) + governance stack exist | **WIRING** -- execution control endpoints return static `{"ok": true}` |
| Work Packets | Governed work decomposition | WorkPacket in organism/ + nodes/ layers | **WIRING** -- no Cockpit UI for work packet lifecycle |
| Agent/Tool Routing | model_router with fallback chain | call_with_fallback() production, 10 providers | **MINIMAL** -- already production |
| Verification/Audit | Pre-commit gates + audit scripts | 4 gate scripts + 93 test files | **EXTEND** -- add reality-model verification |
| Self-Improvement | Governed autonomous cadence | AutonomousCadence + SelfBuildQueueEngine production | **WIRING** -- cadence dry_run_only, needs Cockpit approval UI |

### Gap Classification

| Gap Category | Count | Description |
|--------------|-------|-------------|
| WIRING | 6 | Connecting existing production code through HTTP routes and Cockpit UI |
| EXTEND | 1 | Adding reality-model verification to existing audit infrastructure |
| MINIMAL | 1 | Already production, minimal or no changes needed |
| BUILD | 0 | No major new engines need to be built from scratch |

## Stage 1 Build Definition

See `phase14_6g_stage1_acceptance_criteria.md` for the 50 testable acceptance criteria.
See `phase14_6g_stage1_work_packet_index.md` for the complete work packet decomposition.

### Build Philosophy

1. **Wire first, build later.** Most engines exist. Connect them.
2. **Indivisible increments.** Every increment touches Reality Model + Cockpit + Memory + Execution.
3. **No mock data in Cockpit.** Every panel reads from the actual reality model or returns explicit "not yet wired" state.
4. **Governance from day one.** Risky actions gate on operator approval even in Stage 1.
5. **Deterministic spine.** Every LLM-enhanced path has a deterministic fallback.

### Build Sequence (3 Waves)

**Wave 1: Foundation Wiring (must be first)**
- Wire reality model classes to HTTP routes
- Wire Cockpit WorldModelPanel to reality model endpoints
- Wire execution control endpoints to actual spine
- Wire memory routes to typed memory classes

**Wave 2: Organism Loop (depends on Wave 1)**
- Work packet lifecycle through Cockpit
- Intent capture → work packet generation
- Agent/tool routing from work packets
- Approval UI for governed actions

**Wave 3: Feedback Loop (depends on Wave 2)**
- Outcome recording back to reality model
- Self-improvement work packet generation
- Verification pipeline integration
- Autonomous cadence Cockpit controls

## Recommended Next Phase

**Phase 14.7A: Open UMH Stage 1 Implementation Gate**

Phase 14.7A would begin Wave 1 implementation after operator approval. The gate conditions are defined in `phase14_6g_governance_gate.md`.

## What This Phase Did NOT Do

- Did not modify any product source code
- Did not begin Cockpit implementation
- Did not begin UMH reality-engine implementation
- Did not begin EOS, CreatorOS, or LyfeOS app implementation
- Did not run auth migrations
- Did not deploy anything
- Did not provision infrastructure
- Did not set `allows_implementation = true`
