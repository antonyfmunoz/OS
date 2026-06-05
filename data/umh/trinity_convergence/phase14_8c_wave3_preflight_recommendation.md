# Phase 14.8C — Wave 3 Preflight Recommendation

## Date: 2026-06-05
## Status: PREFLIGHT RECOMMENDATION ONLY — NOT AUTHORIZED FOR IMPLEMENTATION

---

## Idle Cleanup Result

| Check | Result | Evidence |
|-------|--------|----------|
| Stale processes | 1 stale pytest (PID 1625587) — read-only test run from seal session, will exit naturally | `ps aux` |
| Chrome/Playwright | MCP server processes — not stale, expected | `ps aux` |
| local main = origin/main | PASS | Both at `ff987c47` |
| Source-code drift | ZERO | `git status --short` on `cockpit/src`, `substrate/`, `transports/`, `tests/`, `adapters/` → empty |
| Modified tracked files | Daemon runtime data only | 15 files under `data/umh/organism/`, `data/umh/intelligence/`, `data/umh/context_assimilation/` |
| Wave 2 seal artifact on main | PASS | `phase14_8b_wave2_final_seal.md` exists |

**Workspace is idle and clean.**

---

## Full 12-Packet Inventory

### Delivered Packets (8/12)

| Packet | Wave | Delivered By | Evidence |
|--------|------|-------------|----------|
| WP-1.1 | 1 | Phase 14.7A | `cockpit_reality_model_routes.py` — 15 routes operational |
| WP-1.2 | 1 | Phase 14.8A | `d1872fe2` — WorldModelPanel rewired to 9 `/reality-model/*` routes |
| WP-1.3 | 1 | Phase 14.7A | `cockpit.py` L478-526 — typed `ConversationMemory` + `AgentMemory` integration |
| WP-1.4 | 1 | Phase 14.7A | `cockpit.py` L2051-2130 — 4 execution control endpoints wired to `WorkPacketEngine` |
| WP-2.1 | 2 | Phase 14.8B | `2b5f9b71` — POST `/intent/classify` with spine `_INTENT_PATTERNS` + `ConversationMemory` |
| WP-2.2 | 2 | Phase 14.8B | `2b5f9b71` — POST `/generate` with `UniversalWorkQueue.ingest_user_intent()` + `detect_capability()` |
| WP-2.3 | 2 | Phase 14.7A | `cockpit.py` L403-429 — `/approvals` CRUD + `approvalStore.ts` + `ApprovalsPanel.tsx` |
| WP-2.4 | 2 | Phase 14.8B | `2b5f9b71` — `/execution/start` routing chain: `detect_capability` → `route_capability` → `call_with_fallback` |

### Remaining Packets (4/12)

| Packet | Wave | 14.6G Status | Codebase Reality | Remaining Work |
|--------|------|-------------|-----------------|----------------|
| **WP-3.1** | 3 | Planned | PARTIAL — `InstanceRealityModel.record()` and `CanonicalRealityModel.store()` exist. `ConversationMemory.log_outcome()` at L245 exists. But NO wiring from work packet completion → reality model observation. Execution terminal states (`COMPLETED`, `FAILED`) exist in lifecycle FSM but trigger no callback. | Wire execution terminal state transitions → reality model recording with governance gating for canonical |
| **WP-3.2** | 3 | Planned | LARGELY WIRED — `cockpit_autonomous_routes.py` (586 lines) has cadence/dry-run routes. `cockpit_self_build_routes.py` (191 lines) has queue routes. `SelfBuildPanel.tsx` (303 lines) exists. `AutonomousCadence.run_cycle()` at L172 exists. `DRY_RUN_ONLY` mode at L31 exists. BUT: need to verify end-to-end data flow and ensure `dry_run_only` enforcement cannot be overridden via API | Verify e2e wiring; add dry_run_only enforcement test; fix any stub responses |
| **WP-3.3** | 3 | Planned | NOT STARTED — 4 gate scripts exist (`check_dependency_direction.py`, `check_type_divergence.py`, `check_instance_leak.py`, `check_projection_leak.py`). Work packets have `acceptance_criteria` field. But NO wiring from packet completion → verification trigger → result attachment | Wire packet terminal state → gate script execution → result persistence → Cockpit visibility |
| **WP-3.4** | 3 | Planned | NOT STARTED — `projections/` and `saas/` directories exist. Work packet engine has 0 references to "projection" or "saas". Routing is capability-based (code_write, shell_execute, etc.) not directory-aware. | Add projection-aware routing in work packet engine; verify architecture layer law compliance; ensure no projection-specific logic in substrate |

---

## Wave 3 Analysis (14.6G Definition: WP-3.1, WP-3.2, WP-3.3, WP-3.4)

### Infrastructure Assessment

**WP-3.1 (Outcome Recording):** Both reality model classes have write methods (`store()` for canonical, `record()` for instance). `ConversationMemory.log_outcome()` exists. The work packet lifecycle FSM has `EXECUTING → VALIDATING → COMPLETED` and `EXECUTING → FAILED` transitions. The gap is a callback or hook on these terminal transitions that calls the reality model. Governance gating for canonical is already built (AC-8.3). **Complexity: LOW.**

**WP-3.2 (Self-Improvement Cadence):** Routes, engine, and panel all exist. The preflight question is whether they're wired end-to-end or returning stubs. `run_cycle()` exists. `DRY_RUN_ONLY` mode exists. 1080 total lines of existing infrastructure. **Complexity: LOW** if wired, **MEDIUM** if significant stubs need filling.

**WP-3.3 (Verification Pipeline):** All 4 gate scripts are production (pre-commit hooks). Work packet has `acceptance_criteria`. The gap is triggering these scripts from a work packet completion event and attaching results. **Complexity: LOW-MEDIUM.**

**WP-3.4 (Projection Build Loop):** Work packet engine has zero projection awareness. Routing is capability-based, not directory-aware. Adding projection awareness requires: (1) detecting when user_intent targets a projection, (2) routing to correct codebase, (3) ensuring no substrate contamination, (4) verifying architecture layer law. **Complexity: MEDIUM** — genuinely new logic, not just wiring.

### Dependency Graph (from 14.6G)

```
WP-3.1 (outcome → model)     WP-3.2 (cadence)     WP-3.3 (verification)
     └──────────┬─────────────────┘                     │
                └─────────────────────┬─────────────────┘
                                      ▼
                              WP-3.4 (projection loop)
```

WP-3.1, WP-3.2, and WP-3.3 can be parallelized. WP-3.4 depends on all three.

---

## Recommended Next Phase Name

**Phase 14.8C**

Rationale: Wave 1 was 14.8A, Wave 2 was 14.8B, Wave 3 is 14.8C. Consistent with the `14.8{letter}` per-wave naming convention.

---

## Recommended Next Wave Scope

### Phase 14.8C: Wave 3 — Feedback Loop (4 packets)

| Packet | Scope | Complexity | Parallelizable |
|--------|-------|-----------|----------------|
| WP-3.1 | Outcome Recording — wire execution terminal states to `InstanceRealityModel.record()` and governance-gated `CanonicalRealityModel.store()` | LOW | YES (with WP-3.2, WP-3.3) |
| WP-3.2 | Self-Improvement Cadence — verify e2e wiring, ensure `dry_run_only` enforcement, fix stub responses if any | LOW | YES (with WP-3.1, WP-3.3) |
| WP-3.3 | Verification Pipeline — wire packet completion → gate script execution → result persistence | LOW-MEDIUM | YES (with WP-3.1, WP-3.2) |
| WP-3.4 | Projection Build Loop — add projection-aware routing, architecture law compliance, projection-agnostic design | MEDIUM | NO (depends on WP-3.1, WP-3.2, WP-3.3) |

**All 4 remaining packets are in scope.** After Wave 3, all 12 Stage 1 packets are delivered and all 10 acceptance criteria (50 tests) are addressable.

### Recommended Execution Order

```
Phase 1 (parallel): WP-3.1 + WP-3.2 + WP-3.3
Phase 2 (sequential): WP-3.4 (after all three complete)
```

---

## Likely Files/Routes/Components Touched

### WP-3.1: Outcome Recording to Reality Model

| File | Change Type |
|------|-------------|
| `substrate/organism/work_packet_engine.py` | EXTEND — add outcome recording hook on status transition to COMPLETED/FAILED |
| `substrate/reality_model/instance.py` | READ ONLY — use `record()` |
| `substrate/reality_model/canonical.py` | READ ONLY — use `store()` (governance-gated) |
| `substrate/state/memory/memory.py` | READ ONLY — use `log_outcome()` |
| `transports/api/cockpit_universal_work_routes.py` | POSSIBLE EXTEND — outcome visibility endpoint |

### WP-3.2: Self-Improvement Cadence Wiring

| File | Change Type |
|------|-------------|
| `transports/api/cockpit_autonomous_routes.py` | VERIFY + POSSIBLY FIX — confirm e2e data flow |
| `transports/api/cockpit_self_build_routes.py` | VERIFY + POSSIBLY FIX — confirm e2e data flow |
| `cockpit/src/renderer/panels/SelfBuildPanel.tsx` | VERIFY + POSSIBLY FIX — confirm data binding |
| `substrate/organism/autonomous_cadence.py` | READ ONLY — verify `dry_run_only` enforcement |

### WP-3.3: Verification Pipeline Integration

| File | Change Type |
|------|-------------|
| `substrate/organism/work_packet_engine.py` | EXTEND — add verification trigger on completion |
| `substrate/organism/work_packet.py` | POSSIBLY EXTEND — verification result fields |
| `scripts/check_dependency_direction.py` | READ ONLY — called by verification |
| `scripts/check_type_divergence.py` | READ ONLY — called by verification |
| `scripts/check_instance_leak.py` | READ ONLY — called by verification |
| `scripts/check_projection_leak.py` | READ ONLY — called by verification |

### WP-3.4: Projection Build Loop

| File | Change Type |
|------|-------------|
| `substrate/organism/work_packet_engine.py` | EXTEND — projection-aware routing |
| `substrate/execution/runtime/capability_router.py` | READ ONLY — existing routing infrastructure |
| `projections/` | READ ONLY — projection configs |
| `scripts/check_dependency_direction.py` | READ ONLY — architecture law verification |

### NOT Modified (scope discipline)

- `cockpit/src/renderer/panels/WorldModelPanel.tsx` — Wave 1 sealed
- `cockpit/src/renderer/stores/worldModelStore.ts` — Wave 1 sealed
- `transports/api/cockpit_reality_model_routes.py` — Wave 1 sealed
- `cockpit/src/renderer/panels/ApprovalsPanel.tsx` — WP-2.3 sealed
- `cockpit/src/renderer/stores/approvalStore.ts` — WP-2.3 sealed
- `transports/api/cockpit.py` — Wave 2 endpoints sealed (intent/classify, execution/start routing)

---

## Entry Criteria (must all pass before starting)

| # | Criterion |
|---|-----------|
| 1 | Main at `ff987c47` or safe-forward (no source divergence) |
| 2 | Phase 14.8B Wave 2 final seal artifact on main |
| 3 | 58 Wave 2 tests + existing baseline passing |
| 4 | Runtime serves `index-DBaZ_nqZ.js` + `index-C6nKRX2W.css` |
| 5 | Wave 1 and Wave 2 endpoints operational |
| 6 | `InstanceRealityModel.record()` exists and importable |
| 7 | `CanonicalRealityModel.store()` exists and importable |
| 8 | `ConversationMemory.log_outcome()` exists and importable |
| 9 | `AutonomousCadence.run_cycle()` exists and importable |
| 10 | All 4 gate scripts exist and executable |
| 11 | `projections/` and `saas/` directories exist |
| 12 | No active feature branches conflicting with target files |

---

## Exit Criteria (must all pass before sealing Wave 3)

| # | Criterion |
|---|-----------|
| 1 | Work packet completion records outcome to instance reality model |
| 2 | Work packet failure records failure observation to instance reality model |
| 3 | Canonical reality model updates require HIGH risk governance gate |
| 4 | Updated observations visible in Cockpit WorldModelPanel (or via API) |
| 5 | `AutonomousCadence.run_cycle()` returns candidates from template registry |
| 6 | `dry_run_only = true` is enforced and CANNOT be overridden via API |
| 7 | SelfBuildPanel renders candidates and cycle history |
| 8 | Completed work packets trigger verification (gate scripts + tests) |
| 9 | Verification results attached to work packet records |
| 10 | Failed verification blocks packet COMPLETED status |
| 11 | Projection-targeted work packets route to correct codebase |
| 12 | Projection routing is projection-agnostic (no hardcoded EOS/CreatorOS/LyfeOS) |
| 13 | Projection work packets pass `check_dependency_direction.py` |
| 14 | All existing tests pass (excluding documented pre-existing exceptions) |
| 15 | New Wave 3 tests pass |
| 16 | Zero regressions in Wave 1 and Wave 2 surfaces |
| 17 | Runtime cockpit rebuilt (if frontend changes) and serving |
| 18 | Promotion readiness report passes all checks |

---

## Forbidden Actions

1. Do not modify Wave 1 sealed files (WorldModelPanel, worldModelStore, reality model routes)
2. Do not modify Wave 2 sealed endpoints (intent/classify response contract, generate response contract, execution/start routing contract)
3. Do not set `dry_run_only = false` on autonomous cadence
4. Do not run auth migrations
5. Do not provision paid infrastructure
6. Do not perform public deployment (Fly.io)
7. Do not modify governance gate configuration
8. Do not add projection-specific logic to `substrate/` code
9. Do not commit runtime daemon data
10. Do not commit dist-web build outputs if gitignored
11. Do not commit Playwright screenshots/snapshots
12. Do not delete existing working routes or endpoints
13. Do not implement EOS, CreatorOS, or LyfeOS feature surfaces (only routing awareness)

---

## Required Proof Artifacts

1. `phase14_8c_preflight_scope_lock.md` — entry criteria verification + scope lock
2. `phase14_8c_wp31_implementation_report.md` — outcome recording details
3. `phase14_8c_wp32_implementation_report.md` — self-improvement cadence details
4. `phase14_8c_wp33_implementation_report.md` — verification pipeline details
5. `phase14_8c_wp34_implementation_report.md` — projection build loop details
6. `phase14_8c_wave3_promotion_readiness.md` — exit criteria verification
7. `phase14_8c_wave3_main_promotion_report.md` — merge to main details
8. `phase14_8c_wave3_final_seal.md` — canonical seal

---

## Acceptance Criteria Coverage (14.6G)

Wave 3 satisfies AC-7, AC-8, AC-9, and AC-10 from the 14.6G Stage 1 acceptance criteria:

| AC | Name | Tests | Wave 3 Packet |
|----|------|-------|--------------|
| AC-7 | Output Verification | 5 tests | WP-3.3 |
| AC-8 | Reality Model Update After Outcomes | 5 tests | WP-3.1 |
| AC-9 | Governed Self-Improvement | 5 tests | WP-3.2 |
| AC-10 | Build Projections from Inside UMH | 5 tests | WP-3.4 |

After Wave 3, all 10 acceptance criteria (50 tests) are addressed across 3 waves + pre-delivered packets.

---

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| `work_packet_engine.py` becomes a god file with WP-3.1/3.3/3.4 extensions | MEDIUM | Track line count; extract verification/outcome modules if >500 lines |
| `dry_run_only` enforcement may have API bypass | LOW | Explicit test that POST cannot override; check all routes |
| Projection routing adds substrate-boundary-violating code | MEDIUM | Run `check_projection_leak.py` on all changes; WP-3.4 is the highest-risk packet |
| Verification pipeline subprocess calls may timeout | LOW | Use existing gate script timeout patterns; verification is async to user |
| SelfBuildPanel data binding may be heavily stubbed | MEDIUM | Verify before committing WP-3.2 as "LOW"; may need route handler fixes |

---

## GO / PARTIAL GO / NO-GO Determination

### **GO**

Phase 14.8C Wave 3 preflight recommendation is ready. All idle cleanup checks pass — workspace is clean, main and origin aligned at `ff987c47`, zero drift. All 8 of 12 packets are delivered (Waves 1 + 2). The remaining 4 packets (WP-3.1 through WP-3.4) complete the full Stage 1 organism. Infrastructure prerequisites exist: reality model write methods, memory outcome logging, autonomous cadence engine, 4 gate scripts, projection directories. The highest-risk packet is WP-3.4 (projection routing — genuinely new logic). Three of four packets can be parallelized (WP-3.1/3.2/3.3), with WP-3.4 depending on all three. Entry criteria are met. Dependency order is clear.

**Recommendation:** Authorize Phase 14.8C execution with parallel WP-3.1 + WP-3.2 + WP-3.3, then sequential WP-3.4. This is the final wave — after Wave 3, all 12 Stage 1 work packets are delivered and all 10 acceptance criteria are testable.
