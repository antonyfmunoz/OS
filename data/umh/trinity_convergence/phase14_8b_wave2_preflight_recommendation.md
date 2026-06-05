# Phase 14.8B — Wave 2 Preflight Recommendation

## Date: 2026-06-05
## Status: PREFLIGHT RECOMMENDATION ONLY — NOT AUTHORIZED FOR IMPLEMENTATION

---

## Canonical State Confirmation

| Check | Result | Evidence |
|-------|--------|----------|
| local main = origin/main | PASS | Both at `98a75129` |
| d1872fe2 on main | PASS | `git branch --contains` → 1 |
| 3dbad086 on main | PASS | `git branch --contains` → 1 |
| dc2fdadd on main | PASS | `git branch --contains` → 1 |
| 98a75129 on main | PASS | `git branch --contains` → 1 |
| Wave 1 seal artifact on main | PASS | `phase14_8a_wave1_final_seal.md` exists |

---

## Full 12-Packet Inventory

### Delivered Packets (5/12)

| Packet | Wave | Delivered By | Evidence |
|--------|------|-------------|----------|
| WP-1.1 | 1 | Phase 14.7A | `cockpit_reality_model_routes.py` — 15 routes (12 GET + 3 POST) operational |
| WP-1.2 | 1 | Phase 14.8A | `d1872fe2` — WorldModelPanel rewired from 5 `/organism/*` to 9 `/reality-model/*` routes |
| WP-1.3 | 1 | Phase 14.7A | `cockpit.py` L478-526 — typed `ConversationMemory` + `AgentMemory` integration, not raw JSONL |
| WP-1.4 | 1 | Phase 14.7A | `cockpit.py` L2051-2130 — 4 execution control endpoints wired to `WorkPacketEngine` with status lifecycle |
| WP-2.3 | 2 | Phase 14.7A | `cockpit.py` L403-429 — `/approvals`, `/approvals/{id}/approve`, `/approvals/{id}/deny` fully operational; `approvalStore.ts` calls all three; `ApprovalsPanel.tsx` renders pending/history |

### Remaining Packets (7/12)

| Packet | Wave | 14.6G Status | Codebase Reality | Remaining Work |
|--------|------|-------------|-----------------|----------------|
| **WP-2.1** | 2 | Planned | PARTIAL — `/chat/converse` and `/dex/converse` exist; spine `_classify_intent()` exists; `ConversationMemory` integrated; but NO dedicated `/intent` endpoint that classifies → persists → returns typed intent | Wire intent classification pipeline as endpoint; ensure classified intent persists to memory with type annotation |
| **WP-2.2** | 2 | Planned | PARTIAL — `cockpit_universal_work_routes.py` has 12 routes at `/organism/universal-work/*`; `WorkPacketEngine.create_packet_from_intent()` exists; `UniversalWorkPanel.tsx` (497 lines) renders packets. BUT: no `/generate` endpoint that takes raw intent and produces packets | Add packet generation from intent endpoint; verify `UniversalWorkPanel` renders all lifecycle states |
| **WP-2.4** | 2 | Planned | NOT STARTED — `WorkPacketEngine` has no capability routing; no `call_with_fallback` usage; no agent delegation logic; execution endpoints (start/stop/pause/resume) only transition status, don't dispatch to capabilities | Build routing from approved packets to capabilities (cc_sdk, shell, GitHub); integrate with model_router fallback chain |
| **WP-3.1** | 3 | Planned | NOT STARTED — no outcome recording to reality model after work packet execution | Wire execution completion → `instance.observe()` / `canonical.observe()` with governance gating |
| **WP-3.2** | 3 | Planned | LARGELY WIRED — `cockpit_autonomous_routes.py` (586 lines) has cadence status, dry-run, mode-set routes; `cockpit_self_build_routes.py` (191 lines) has queue overview, items, status; `SelfBuildPanel.tsx` (303 lines) calls these routes. BUT: need to verify data flows end-to-end (routes → engine → panel) vs returning stubs | Verify end-to-end data flow; ensure dry_run_only enforcement; fix any stub responses |
| **WP-3.3** | 3 | Planned | NOT STARTED — no verification pipeline triggered on work packet completion | Wire gate scripts to packet completion; attach verification results to packet records |
| **WP-3.4** | 3 | Planned | NOT STARTED — no projection-aware routing in work packet engine | Add projection-agnostic routing for saas/projections targets; verify architecture layer law compliance |

---

## Wave 2 Analysis (14.6G Definition: WP-2.1, WP-2.2, WP-2.3, WP-2.4)

### Already Delivered
- **WP-2.3 (Approval UI Wiring)**: Fully operational. Backend `/approvals` CRUD + frontend `approvalStore.ts` + `ApprovalsPanel.tsx`. Same pattern as Wave 1 — 14.7A already shipped it.

### Partially Delivered
- **WP-2.1 (Intent Capture Pipeline)**: Chat/converse flow exists but no dedicated intent classification endpoint. Spine `_classify_intent()` is production. `ConversationMemory` is integrated. Gap is the specific pipeline: text input → classify → persist with type → return typed result.
- **WP-2.2 (Work Packet Lifecycle)**: 12 universal work routes exist. `WorkPacketEngine.create_packet_from_intent()` exists. `UniversalWorkPanel.tsx` renders packets. Gap is the generation-from-intent endpoint and verifying full lifecycle rendering.

### Not Started
- **WP-2.4 (Agent/Tool Routing)**: The core gap. Execution endpoints transition packet status but don't dispatch work to capabilities. `WorkPacketEngine` has no `call_with_fallback` integration. No capability routing logic.

---

## Recommended Next Phase Name

**Phase 14.8B**

Rationale: The 14.6G work packet index defines Waves 1/2/3. Phase 14.8A delivered Wave 1. The naming convention for this series is `14.8{letter}` per wave. Wave 2 is `14.8B`.

---

## Recommended Next Wave Scope

### Phase 14.8B: Wave 2 — Organism Loop (3 packets)

| Packet | Scope | Complexity |
|--------|-------|-----------|
| WP-2.1 | Intent Capture Pipeline — wire dedicated `/intent` endpoint through spine `_classify_intent()` to `ConversationMemory` persistence | LOW (backend exists, need to compose) |
| WP-2.2 | Work Packet Lifecycle — add `/organism/universal-work/generate` endpoint using `WorkPacketEngine.create_packet_from_intent()`; verify `UniversalWorkPanel` end-to-end | LOW-MEDIUM (engine exists, need endpoint + panel verification) |
| WP-2.4 | Agent/Tool Routing — wire `execution/start` through capability routing to `call_with_fallback`; implement typed gap on unavailable capability | MEDIUM (new logic in work_packet_engine.py) |

**WP-2.3 is excluded** — already delivered by 14.7A.

### Dependency Order

```
WP-2.1 (intent capture)
    ↓ feeds
WP-2.2 (packet generation from intent)
    ↓ feeds          WP-2.3 (DELIVERED — approval UI)
    ↓                    ↓
    └────────────────────┘
                ↓
            WP-2.4 (agent/tool routing from approved packets)
```

WP-2.1 and WP-2.2 have a soft dependency (2.2 needs intent to generate from), but both can be developed independently against test data. WP-2.4 depends on all three predecessors being functional.

Recommended execution order: WP-2.1 → WP-2.2 → WP-2.4 (sequential).

---

## Likely Files/Routes/Components Touched

### WP-2.1: Intent Capture Pipeline
| File | Change Type |
|------|-------------|
| `transports/api/cockpit.py` | New POST `/intent` endpoint |
| `substrate/execution/spine.py` | READ ONLY — use `_classify_intent()` |
| `substrate/state/memory/memory.py` | READ ONLY — use `ConversationMemory.log()` |

### WP-2.2: Work Packet Lifecycle
| File | Change Type |
|------|-------------|
| `transports/api/cockpit_universal_work_routes.py` | New POST `/organism/universal-work/generate` endpoint |
| `substrate/organism/work_packet_engine.py` | READ ONLY — use `create_packet_from_intent()` |
| `cockpit/src/renderer/panels/UniversalWorkPanel.tsx` | Verify rendering, fix if needed |
| `cockpit/src/renderer/stores/` | Possibly update universal work store if generate call missing |

### WP-2.4: Agent/Tool Routing
| File | Change Type |
|------|-------------|
| `substrate/organism/work_packet_engine.py` | EXTEND — add capability routing logic |
| `transports/api/cockpit.py` | EXTEND — `execution/start` calls routing after status transition |
| `adapters/models/model_router.py` | READ ONLY — use `call_with_fallback()` |

### NOT Modified (scope discipline)
- `substrate/reality_model/` — no changes
- `cockpit/src/renderer/panels/WorldModelPanel.tsx` — sealed from Wave 1
- `cockpit/src/renderer/stores/worldModelStore.ts` — sealed from Wave 1
- Backend reality model routes — sealed
- Backend approval routes — sealed

---

## Entry Criteria (must all pass before starting)

| # | Criterion |
|---|-----------|
| 1 | Main at `98a75129` or safe-forward (no source divergence) |
| 2 | Phase 14.8A Wave 1 seal artifact on main |
| 3 | 289/289 tests pass on main |
| 4 | Runtime serves `index-DBaZ_nqZ.js` + `index-C6nKRX2W.css` |
| 5 | WP-2.3 confirmed delivered (approval routes + panel operational) |
| 6 | `WorkPacketEngine.create_packet_from_intent()` exists and importable |
| 7 | `ExecutionSpine._classify_intent()` exists and callable |
| 8 | `ConversationMemory` class exists and integrates with Neon |
| 9 | `call_with_fallback()` is production and has active fallback chain |
| 10 | No active feature branches conflicting with target files |

---

## Exit Criteria (must all pass before sealing Wave 2)

| # | Criterion |
|---|-----------|
| 1 | POST `/intent` classifies text and persists to ConversationMemory |
| 2 | POST `/organism/universal-work/generate` produces packets from intent |
| 3 | GET `/organism/universal-work/packets` returns generated packets |
| 4 | `UniversalWorkPanel.tsx` renders work packets with correct lifecycle states |
| 5 | `execution/start` on approved packet routes to capability (cc_sdk, shell, or fallback) |
| 6 | Unavailable capability returns typed UNAVAILABLE gap, not silent failure |
| 7 | Fallback chain activates when primary capability is unavailable |
| 8 | 289+ tests pass (existing + new Wave 2 tests) |
| 9 | Zero regressions in Wave 1 surfaces (WorldModelPanel, approval routes, reality model routes) |
| 10 | Runtime cockpit rebuilt and serving updated build |
| 11 | All 3 packets have implementation report artifacts |
| 12 | Promotion readiness report passes all checks |

---

## Forbidden Actions

1. Do not modify Wave 1 sealed files (WorldModelPanel, worldModelStore, reality model routes)
2. Do not start Wave 3 packets (WP-3.1 through WP-3.4)
3. Do not start EOS, CreatorOS, or LyfeOS feature implementation
4. Do not run auth migrations
5. Do not provision paid infrastructure
6. Do not perform public deployment (Fly.io)
7. Do not modify governance gate configuration
8. Do not set `dry_run_only = false` on autonomous cadence
9. Do not commit runtime daemon data
10. Do not commit dist-web build outputs if gitignored
11. Do not commit Playwright screenshots/snapshots
12. Do not delete existing working routes or endpoints

---

## Required Proof Artifacts

1. `phase14_8b_preflight_scope_lock.md` — entry criteria verification + scope lock
2. `phase14_8b_wp21_implementation_report.md` — intent capture pipeline details
3. `phase14_8b_wp22_implementation_report.md` — work packet lifecycle details
4. `phase14_8b_wp24_implementation_report.md` — agent/tool routing details
5. `phase14_8b_wave2_promotion_readiness.md` — exit criteria verification
6. `phase14_8b_wave2_main_promotion_report.md` — merge to main details
7. `phase14_8b_wave2_final_seal.md` — canonical seal

---

## Acceptance Criteria Mapping (14.6G → Wave 2)

Wave 2 satisfies AC-4, AC-5, and AC-6 from the 14.6G Stage 1 acceptance criteria:

| AC | Name | Tests | Wave 2 Packet |
|----|------|-------|--------------|
| AC-4 | Work Packet Generation from Intent | 5 tests | WP-2.1 + WP-2.2 |
| AC-5 | Work Routing to Agents/Tools | 5 tests | WP-2.4 |
| AC-6 | Governed Execution Approval Gates | 7 tests | WP-2.3 (DELIVERED) + WP-2.4 |

AC-6 is partially delivered via WP-2.3 (approval UI). The remaining AC-6 tests (risk classification → approval required → action blocked/executed) are validated through WP-2.4's routing integration.

---

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| `WorkPacketEngine.create_packet_from_intent()` may need LLM for decomposition | MEDIUM | Has deterministic fallback (required by Deterministic-First Principle) — verify |
| `execution/start` currently only transitions status; routing is genuinely new | HIGH | Scope WP-2.4 carefully — routing decision logic is new code, not just wiring |
| Universal work routes use `/organism/*` prefix (not `/reality-model/*`) | LOW | These are organism routes, not reality model — prefix is correct per current architecture |
| `ExecutionPanel.tsx` may need extension for routing visibility | MEDIUM | Check if panel shows routing decisions; if not, scope as WP-2.4 sub-task |

---

## GO / PARTIAL GO / NO-GO Determination

### **GO**

Phase 14.8B Wave 2 preflight recommendation is ready. All canonical state checks pass. The wave scope is 3 packets (WP-2.1, WP-2.2, WP-2.4) after confirming WP-2.3 is already delivered. Infrastructure prerequisites exist: intent classification, work packet engine, memory persistence, approval UI, model routing. The primary new work is WP-2.4 (agent/tool routing from approved packets), which requires new logic in `work_packet_engine.py`. Entry criteria are met. Dependency order is clear.

**Recommendation:** Authorize Phase 14.8B execution with WP-2.1 → WP-2.2 → WP-2.4 sequential order.
