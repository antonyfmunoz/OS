# Phase 12.0 — Universal Propagation Graph / Correspondence Layer

**Date:** 2026-05-30
**Status:** COMPLETE
**Predecessor:** Phase 11.1R (PR #57, ptd-85fb7318, poc-532ce3d)

## Phase 11.1R Preflight Proof

All 14 preflight checks pass. See `phase12_0_preflight_111r_verification.md`.

## Propagation Graph Model

**File:** `substrate/organism/propagation_graph.py` (433 lines)

- `PropagationNode` — 30 node types covering work packets, workcells, roadmap phases, templates, knowledge models, agents, memory, companies, products, offers, API routes, cockpit panels, production truth deltas, outcomes, and human actions
- `PropagationEdge` — 19 edge types, 14 propagation modes, 4 strength levels
- `PropagationGraph` — full graph with add_node/add_edge, upstream/downstream traversal, affected_by_change, impact_radius, cycle detection, orphan detection, persist/load, to_dict/from_dict/to_safe_dict
- Registered in `canonical_types.py`: PropagationNodeType, PropagationEdgeType, PropagationMode, EdgeStrength

## Change Event Model

**File:** `substrate/organism/change_event.py` (370 lines)

- `ChangeEvent` — 17 change types, before/after state, changed fields/files/entities/relationships, risk class, idempotency key
- `PropagationAction` — action per node, 8 statuses, approval/validation/human gates
- `PropagationWave` — ordered wave with parallel grouping and reconvergence
- `PropagationPlan` — full plan with waves, blocked/approval/human/validation/no-op node lists
- `PropagationResult` — execution result with wave results, completed/failed/blocked/approval/human/no-op action lists
- Registered in `canonical_types.py`: ChangeType, PropagationActionStatus

## Graph Extractor

**File:** `substrate/organism/propagation_graph_builder.py` (532 lines)

Extracts from 11 real system sources:
1. WorkPacket store (5 packets)
2. Workcell store (5 workcells + advisor branches)
3. SelfBuildQueue items
4. RoadmapEngine phases
5. TemplateRegistry
6. KnowledgeModelRegistry
7. RoleContracts
8. ProductionTruthDelta (ptd-85fb7318)
9. ProductionOutcomeCommitted (poc-532ce3d)
10. API routes (10 Universal Work routes)
11. EntityMetadata (companies/products)

**Initial graph:** 49 nodes, 19 edges — all from real system state, zero fake nodes.

## Impact Analyzer

**File:** `substrate/organism/impact_analyzer.py` (323 lines)

- BFS downstream traversal from change source
- Direct vs indirect impact classification
- Impact scoring: node type risk multiplier × edge strength × depth decay
- Parallelizable group computation (by depth)
- Reconvergence point detection (multiple affected parents)
- Risk summary with distribution
- Medium-risk events block non-safe propagation modes

## Propagation Planner

**File:** `substrate/organism/propagation_planner.py` (196 lines)

- Wave assignment by node type (Wave 1: packets/workcells, Wave 2: roadmap/entities, Wave 3: API/templates, Wave 4: memory/candidates)
- Wave ordering enforced
- Parallel action grouping within waves
- Reconvergence required after diverging branches
- Idempotency keys on every action
- Medium-risk → blocked or approval_required
- Default execution_mode: dry_run

## Dry-Run Executor

**File:** `substrate/organism/propagation_executor.py` (239 lines)

4 execution modes:
- `dry_run` — logs what would execute, no mutation (Phase 12.0 default)
- `recompute_only` — safe recomputations only
- `notify_only` — log only
- `governed_execution` — blocked in Phase 12.0

Features:
- Idempotency key deduplication
- Blocked/approval/human action handling
- Wave ordering preservation
- Failure isolation (blocked actions don't stop parallel siblings)
- Reconvergence tracking
- Result persistence to JSONL

## Correspondence Layer Proof

3-scale proof demonstrating the same propagation pattern at:

1. **UMH Self-Build Level** — Phase 12 roadmap status change propagates to self-build queue, work packets, API routes
2. **Business/EOS Level** — EOS Dashboard work packet status change propagates to workcells, human approval gates, validation plans
3. **Knowledge/Workflow Level** — B2B AI Automation knowledge model update propagates to templates, role contracts, content opportunities

All three scales use identical pipeline: ChangeEvent → ImpactAnalyzer → PropagationPlanner → PropagationExecutor.

## UniversalWorkQueue Integration

- 5 work packets visible as propagation nodes
- 5 workcells linked to packets via OWNS edges
- Impact analysis on packet change computes affected workcells, roadmap phases, API routes
- Dry-run ranking update produced
- Follow-up candidate creation in dry-run only

## API Routes

**File:** `transports/api/cockpit_propagation_graph_routes.py` (216 lines)

10 routes mounted under `/api/umh/`:

| Method | Path | Auth |
|--------|------|------|
| GET | /organism/propagation-graph | API key |
| GET | /organism/propagation-graph/summary | API key |
| GET | /organism/propagation-graph/nodes | API key |
| GET | /organism/propagation-graph/edges | API key |
| GET | /organism/propagation-graph/change-events | API key |
| GET | /organism/propagation-graph/results | API key |
| GET | /organism/propagation-graph/correspondence-proof | API key |
| POST | /organism/propagation-graph/impact | Operator token |
| POST | /organism/propagation-graph/plan | Operator token |
| POST | /organism/propagation-graph/execute-dry-run | Operator token |

## Cockpit Panel

**File:** `cockpit/src/renderer/panels/PropagationGraphPanel.tsx`

Sections:
1. Graph Summary (nodes, edges, types, orphans, cycles, built_at)
2. Impact Simulator (select node, run impact analysis)
3. Impact Analysis (direct, indirect, approval, human, blocked, waves)
4. Correspondence Proof (3 scales)

Registered in Shell.tsx and cockpitStore.ts.

## Lifecycle Dry-Run

Full lifecycle proof for "Build the first EOS operating dashboard for Empyrean Studios" moving from planned to ready_for_review:

1. Change event created
2. Graph identifies source node
3. Impact analyzer finds affected nodes
4. Propagation planner creates waves
5. Workcells marked for review/reconvergence
6. Human approval gate identified
7. Validation plan marked active
8. Roadmap link affected
9. EOS projection marked affected
10. UniversalWorkQueue ranking dry-run update produced
11. No production execution occurs
12. Dry-run result persisted
13. API returns result

## Tests & Gates

**78 Phase 12.0 tests pass** covering:
- PropagationNode serialization (4 tests)
- PropagationEdge serialization (6 tests)
- PropagationGraph build/traversal (9 tests)
- Cycle detection (3 tests)
- Graph persistence (2 tests)
- ChangeEvent serialization (4 tests)
- PropagationPlan serialization (2 tests)
- PropagationAction (2 tests)
- PropagationResult (2 tests)
- ImpactAnalyzer (6 tests)
- PropagationPlanner (8 tests)
- PropagationExecutor (10 tests)
- GraphBuilder (7 tests)
- UniversalWorkQueue integration (2 tests)
- Correspondence proof (1 test)
- API route shapes (3 tests)
- Cockpit data shapes (3 tests)
- Safety invariants (3 tests)

**Gates:**
- py_compile: PASS
- Type divergence: PASS
- Dependency direction: PASS
- Line count: PASS (all files under 1000 lines)
- Route auth: PASS
- No fake data: PASS

**Prior phase regression:**
- Phase 11.1: 109/109 PASS
- Combined: 187/187 PASS

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `substrate/organism/propagation_graph.py` | 433 | Graph model |
| `substrate/organism/change_event.py` | 370 | Change event + plan + result models |
| `substrate/organism/propagation_graph_builder.py` | 532 | Graph extractor from system state |
| `substrate/organism/impact_analyzer.py` | 323 | Impact analysis engine |
| `substrate/organism/propagation_planner.py` | 196 | Wave-based plan creation |
| `substrate/organism/propagation_executor.py` | 239 | Dry-run executor |
| `transports/api/cockpit_propagation_graph_routes.py` | 216 | API routes |
| `cockpit/src/renderer/panels/PropagationGraphPanel.tsx` | ~200 | Cockpit panel |
| `substrate/organism/tests/test_phase12_0_propagation_graph.py` | 989 | 78 tests |

## Data Files

11 proof/verification files in `data/umh/propagation_graph/`:
- `phase12_0_preflight.json`
- `phase12_0_initial_graph.json` (49 nodes, 19 edges)
- `phase12_0_impact_analysis_proof.json`
- `phase12_0_propagation_plan_proofs.json`
- `phase12_0_executor_dry_run_proof.json`
- `phase12_0_correspondence_layer_proof.json`
- `phase12_0_universal_work_integration.json`
- `phase12_0_api_verification.json`
- `phase12_0_cockpit_verification.json`
- `phase12_0_main_lifecycle_dry_run.json`
- `phase12_0_test_gate_results.json`
- `graph.json`
- `change_events.jsonl`

## Remaining Blockers

None. All 17 success criteria met.

## Decision

**READY FOR PHASE 13 — Jarvis-Level UMH Operator Experience**

UMH can now model and plan how changes propagate across the entire system. The correspondence layer proves the same pattern works at self-build, business/EOS, and knowledge/workflow scales.
