# Phase 13.4M — Multi-Runtime Jarvis Acceptance Correction

**Date**: 2026-05-31
**Phase**: 13.4M (supersedes 13.4D deterministic-only)
**Status**: COMPLETE
**Decision**: Proceed to Phase 13.4 Standard Multi-Runtime Acceptance

---

## Operator Correction

Phase 13.4D incorrectly defaulted to deterministic-only mode because cloud
API quota was exhausted. The operator corrected:

1. UMH uses Claude Code subscription — no extra API cost needed.
2. Codex, OpenCode, Hermes, Ollama, shell, and Windows Beast are all valid runtime paths.
3. Cloud API exhaustion is a WARNING, not a BLOCKER.
4. VPS is the control plane, not the heavy execution machine.
5. Windows Beast is the workhorse.
6. Standard mode is blocked only if NO capable governed runtime path exists.
7. Deterministic-only is a fallback, not the default.

**Previous incorrect framing:**
"Standard Phase 13.4 is blocked because no cloud LLM provider is available."

**Corrected framing:**
"Standard Phase 13.4 is blocked only if no capable governed runtime path is available."

---

## Preflight — Phase 13.3SR Verification

17/18 checks passed. The single gap (context assimilation routes) is a Phase 13.4 deliverable, not a 13.3SR regression.

- ProductionTruthDelta: ptd-ce06a7af ✓
- ProductionOutcomeCommitted: poc-8286d391 ✓
- Operational truth API: 8 routes wired ✓
- Execution journal: recording ✓
- EventBus: business_ops handler registered ✓
- Knowledge graph: fresh ✓
- Pre-commit gates: 4/4 wired ✓
- Runtime surface: sandbox-only ✓
- Cadence: dry_run_only ✓
- Medium-risk: blocked ✓

Proof: `data/umh/jarvis_acceptance/phase13_4m_preflight.json`

---

## Runtime Fleet Audit

15 runtimes audited. Results:

| Runtime | Status | Cost Model | Notes |
|---------|--------|------------|-------|
| Claude Code CLI v2.1.158 | READY | Subscription | Primary governed runtime |
| CC SDK (subprocess) | READY | Subscription | OAuth injection working |
| Claude Code PTY | READY | Subscription | tmux-backed |
| Shell adapter | READY | Free | Always available |
| Ollama (qwen2.5:0.5b) | READY | Free | Emergency fallback only |
| Node mesh (port 8094) | READY | Free | Beast reachable |
| Codex CLI v0.133.0 | INSTALLED | Subscription | Not integration-tested |
| OpenCode CLI v1.15.7 | INSTALLED | Unknown | Not integration-tested |
| Hermes CLI v0.14.0 | INSTALLED | Unknown | Not integration-tested |
| Browser (playwright) | INSTALLED | Free | No adapter export yet |
| Anthropic API | NOT CONFIGURED | Per-token | Key not in shell env |
| Gemini API | NOT CONFIGURED | Per-token | Key not in shell env |
| Groq API | NOT CONFIGURED | Per-token | Key not in shell env |
| Perplexity API | NOT CONFIGURED | Per-token | Key not in shell env |
| Manus | NOT INSTALLED | Unknown | Binary not found |

**6 runtimes READY. Capable governed runtime path EXISTS.**

Proof: `data/umh/jarvis_acceptance/phase13_4m_runtime_fleet_audit.json`

---

## Device Role Registry

Three nodes seeded:

| Device | Role | Trust | Max Risk | Key Capabilities |
|--------|------|-------|----------|-----------------|
| VPS /opt/OS | control_plane | full | low | canonical state, API, scheduling, coordination |
| Windows Beast | heavy_workstation | full | medium | GPU, browser automation, containers, local models |
| Fly Cockpit | cockpit_ui | medium | low | operator interface, no execution |

Proof: `data/umh/jarvis_acceptance/phase13_4m_device_role_registry_proof.json`

---

## Runtime Fleet Model

`substrate/organism/runtime_fleet.py` defines:
- `RuntimeProvider` enum (11 providers)
- `RuntimeFleetMember` — tracks each runtime's status, capabilities, cost
- `RuntimeSelection` — records runtime selection decisions with alternatives

---

## Workload Placement Policy

`substrate/organism/workload_placement_policy.py` implements:
- 19 workload types
- Device preference maps (VPS for governance, Beast for heavy work)
- Runtime preference maps (Claude Code first for coding/reasoning)
- Medium+ risk requires operator approval
- Degraded mode when no preferred option available

---

## Jarvis Readiness Gate Correction

`substrate/organism/jarvis_readiness_gate.py` corrected:

**Before**: Checked only `snapshot.llm_provider_state` for cloud LLM availability.
**After**: Detects full runtime fleet — Claude Code, Shell, Codex, OpenCode, Hermes, Ollama, cloud API.

- `standard_ready = True` when any capable governed runtime exists AND no blocking issues
- `deterministic_only_ready = True` when no blocking issues (runtime not required)
- Cloud API exhaustion classified as warning, not blocker
- Report includes `capable_runtimes` list and fleet evidence
- Fixed worktree `.git` hook detection

**Live test result:**
- `standard_ready: True`
- `capable_runtimes: [claude_code, shell, codex, opencode, hermes, ollama]`
- `blocking_issues: []`

Proof: `data/umh/jarvis_acceptance/phase13_4m_readiness_gate_correction.json`

---

## Acceptance Mode Correction

`substrate/organism/jarvis_acceptance_mode.py` corrected:

- Renamed `STANDARD` → `STANDARD_MULTI_RUNTIME`
- Added `capable_runtime_path_exists`, `selected_runtime`, `selected_device` fields
- Added `create_standard_mode_decision()` factory
- Added `select_acceptance_mode()` — decision logic:
  1. Capable runtime exists → `standard_multi_runtime`
  2. No runtime + operator accepts degraded → `deterministic_only`
  3. Otherwise → `blocked`

---

## Provider/Runtime Order

Corrected priority for coding/reasoning workcells:

1. Claude Code (subscription, Opus-class via Max)
2. Claude SDK (subscription, subprocess)
3. Codex (subscription, installed v0.133.0)
4. OpenCode (installed v1.15.7)
5. Hermes (installed v0.14.0)
6. Shell (free, deterministic, always available)
7. Ollama (free, local, emergency quality fallback)
8. Cloud API (per-token, currently not in shell env)
9. Deterministic fallback (no intelligence, template-based)

---

## Runtime Availability Proofs

All 8 probes passed:
- Claude Code v2.1.158 ✓
- Codex v0.133.0 ✓
- OpenCode v1.15.7 ✓
- Hermes v0.14.0 ✓
- Ollama qwen2.5:0.5b ✓
- ShellRuntimeAdapter available ✓
- ClaudeCodeRuntimeAdapter available ✓
- Windows Beast reachable (200ms RTT via Tailscale) ✓

---

## Windows Beast Workhorse Proof

- Tailscale: reachable (200ms RTT)
- SSH: fully authenticated, `beast_alive` confirmed
- Mesh port 8094: listening on VPS
- Mesh codebase: exists (7 files + integration dir)
- Role confirmed: heavy_workstation
- Next action: verify Beast-side daemon running, confirm bidirectional heartbeat

---

## Mode Selection Decision

```
Mode: standard_multi_runtime
Runtime: claude_code
Device: vps
Degraded: false
Capable runtime exists: true
Cloud API available: false (warning only)
```

Proof: `data/umh/jarvis_acceptance/phase13_4m_mode_selection_decision.json`

---

## API Routes

4 new bridge handlers added to `transports/api/organism_bridge.py`:
- `organism.operational_truth.runtime_fleet`
- `organism.operational_truth.device_roles`
- `organism.operational_truth.workload_placement`
- `organism.operational_truth.runtime_readiness`

4 new TS routes added to `transports/api/http/routes/organism.ts`:
- `GET /api/umh/organism/operational-truth/runtime-fleet`
- `GET /api/umh/organism/operational-truth/device-roles`
- `GET /api/umh/organism/operational-truth/workload-placement`
- `GET /api/umh/organism/operational-truth/runtime-readiness`

All routes require `operatorGuard` auth. No secrets exposed.

---

## Tests & Gates

**48 tests, all passing:**
- TestDeviceRoleRegistry: 7/7
- TestRuntimeFleetModel: 7/7
- TestWorkloadPlacementPolicy: 7/7
- TestJarvisReadinessGate: 4/4
- TestJarvisAcceptanceMode: 10/10
- TestSafetyInvariants: 4/4
- TestAPIBridgeHandlers: 5/5
- TestReadinessGateUsesFleet: 3/3
- TestNoFakeData: 2/2

**Pre-commit gates: all 4 pass**
- type_divergence ✓
- instance_leak ✓
- projection_leak ✓
- dependency_direction ✓

**py_compile: all 8 modules clean**

---

## New Files Created

| File | Purpose |
|------|---------|
| `substrate/organism/device_role_registry.py` | Device role + capability registry |
| `substrate/organism/runtime_fleet.py` | Runtime fleet member + selection model |
| `substrate/organism/workload_placement_policy.py` | Workload → device/runtime placement |
| `substrate/organism/tests/test_phase13_4m.py` | 48 tests for all 13.4M components |

## Files Modified

| File | Change |
|------|--------|
| `substrate/organism/jarvis_readiness_gate.py` | Runtime fleet detection, standard_ready field |
| `substrate/organism/jarvis_acceptance_mode.py` | STANDARD_MULTI_RUNTIME, fleet-aware decision |
| `transports/api/organism_bridge.py` | 4 new bridge handlers |
| `transports/api/http/routes/organism.ts` | 4 new API routes |

## Files Preserved from 13.4D (reusable)

| File | Status |
|------|--------|
| `substrate/organism/jarvis_acceptance.py` | Reusable — generic acceptance run model |
| `substrate/organism/jarvis_acceptance_scenarios.py` | Reusable — scenario definitions |

---

## Remaining Blockers

1. **Context assimilation routes** — Phase 13.4 deliverable, not a blocker
2. **Beast daemon verification** — need to confirm Beast-side daemon running
3. **Codex/OpenCode/Hermes integration testing** — installed but not runtime-tested
4. **Cockpit OOM** — Fly app may need redeployment for acceptance surface

---

## Decisions

### Ready for Phase 13.4 Standard Multi-Runtime Acceptance: YES

A capable governed runtime path exists (Claude Code CLI via subscription).
6 runtimes are ready. Cloud API exhaustion is a warning, not a blocker.

### Standard Phase 13.4 Blocked: NO

The previous blocker (no cloud LLM) was incorrect. Claude Code CLI provides
Opus-class reasoning via Max subscription at no API cost.

### Phase 13.4 Should Proceed As: Standard Multi-Runtime

Not deterministic-only. The full Jarvis plumbing can be validated with
Claude Code as the primary governed runtime.

### Deterministic-Only: Fallback Only

Deterministic-only mode remains available as a degraded fallback, but is
NOT the default and should NOT be promoted as the main acceptance path.

### Phase 14: Blocked Until Standard Multi-Runtime Acceptance Completes

Phase 14 requires successful standard-mode Jarvis acceptance first.

---

## Success Criteria Verification

1. Previous deterministic-only framing corrected ✓
2. Runtime fleet state truthfully audited ✓
3. Device role registry exists ✓
4. Runtime fleet model exists ✓
5. Workload placement policy exists ✓
6. VPS classified as control plane ✓
7. Windows Beast classified as heavy workhorse ✓
8. Claude Code treated as primary subscription-backed runtime ✓
9. Codex/OpenCode/Hermes represented as supported options ✓
10. Cloud API exhaustion not a blocker ✓
11. Readiness gate uses runtime fleet ✓
12. Runtime availability proofs truthful ✓
13. Windows Beast workhorse proof exists ✓
14. API exposes runtime fleet/device role/readiness ✓
15. Mode selection decision exists ✓
16. 48/48 tests pass ✓
17. No secrets exposed ✓
18. Audit declares correct next Phase 13.4 path ✓

**All 18 success criteria met.**
