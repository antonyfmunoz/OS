# Phase 96.8AN — W0 Real Actuator Maturity Leverage Proof

## What This Proves

The UMH substrate now has an actuator maturity model that prevents
dry-run orchestration from being confused with real GUI actuation.
Every actuation is classified L0-L7 based on observed evidence.
No actuator can claim maturity above the evidence it provides.

## Maturity Levels

| Level | Name | Required Evidence |
|-------|------|-------------------|
| L0 | SIMULATED | None (dry-run) |
| L1 | PROCESS_STARTED | chrome_pid |
| L2 | WINDOW_OBSERVED | chrome_pid + window_handle |
| L3 | FOREGROUND_FOCUSED | + focused |
| L4 | NAVIGATION_OBSERVED | + navigation_detected |
| L5 | SCREENSHOT_VERIFIED | + screenshot_path |
| L6 | FOUNDER_CONFIRMED | + founder_confirmed |
| L7 | REPLAYABLE_ACTUATION | + replay_hash |

### Hard Ceilings
- No HWND → capped at L1 (regardless of other evidence)
- No screenshot → capped at L4
- No founder confirmation → capped at L5

## Backend Evaluation

6 backends evaluated. See `docs/system/actuator_backend_leverage_evaluation.md`.

**Selected: Windows Interactive Desktop Relay (PowerShell)**

Rationale: Already deployed, zero integration time, full capability
coverage (7/7 capabilities), proven in Phase 96.8Q.

## Architecture

```
core/actuation/
├── actuator_maturity_v1.py          — L0-L7 model, compute/validate
├── actuator_backend_registry_v1.py  — 6 backends, select_for_proof
├── observed_desktop_state_v1.py     — maturity-aware observed state
└── windows_foreground_actuator_v1.py — proof classification + persistence
```

The maturity model classifies relay output. The relay does the
actuating. Separation of concerns: the relay doesn't know about
maturity levels, and the maturity model doesn't know about PowerShell.

## Command Registration

`!actuator-proof` added as the 12th canonical command:
- Spine-routed (FOUNDER_APPROVAL governance)
- Foreground required
- Screenshot proof required
- Registered in canonical registry, router config, ALLOWED_ACTION_TYPES,
  ACTION_CAPABILITY_MAP, adapter registry, and spine builder capabilities

## Proof Artifacts

```
data/runtime/actuator_maturity_proofs/
├── backend_selection.json
├── observed_desktop_state.json
├── chrome_process_state.json
├── window_focus_state.json
├── actuator_maturity_report.json
└── final_actuator_summary.json
```

## Test Results

```
Phase 96.8AN:  44 passed  (11 test classes)
Phase 96.8AM:  22 passed  (regression)
Phase 96.8AL:  35 passed  (regression, updated for 12 commands)
Phase 96.8AK:  28 passed  (regression)
Phase 96.8AJ:  60 passed  (regression)
Total:        189 passed, 0 failed
```

### Phase 96.8AN Test Classes
- TestMaturityLevelComputation (8) — L0 through L7 evidence mapping
- TestMaturityCeiling (4) — HWND/screenshot/founder hard caps
- TestMaturityClaimValidation (3) — valid claim, overclaim rejected, L0 always valid
- TestDryRunCannotClaimL2 (2) — dry-run forced to L0
- TestSimulatedMarkedClearly (3) — SIMULATED/REAL_ACTUATION/FAILED status strings
- TestBackendRegistry (6) — loads, relay has all caps, selection returns relay
- TestProofSummaryIntegrity (2) — intended state cannot claim success
- TestCanonicalRegistryInclusion (7) — !actuator-proof in all registries
- TestProofArtifactPersistence (2) — artifacts written, backend selection proof
- TestMaturityLevelOrdering (4) — 8 levels, strict order, labels, requirements
- TestRegressionIntegrity (3) — all files compile, existing files compile

## Files

```
CREATED:
  core/actuation/actuator_maturity_v1.py
  core/actuation/actuator_backend_registry_v1.py
  core/actuation/observed_desktop_state_v1.py
  core/actuation/windows_foreground_actuator_v1.py
  tests/test_actuator_maturity_v1.py
  docs/system/actuator_backend_leverage_evaluation.md
  docs/system/phase968an_actuator_maturity_leverage_proof.md
  data/runtime/actuator_maturity_proofs/ (6 proof artifacts)

MODIFIED:
  core/registry/canonical_command_registry_v1.py
    — added !actuator-proof as 12th command
  config/control_plane_router_v1.json
    — added actuator_proof to allowed_action_types
  core/control_plane_router/router_contracts.py
    — added actuator_proof to ALLOWED_ACTION_TYPES
  core/control_plane_router/control_plane_router_v1.py
    — added actuator_proof to ACTION_CAPABILITY_MAP
  eos_ai/interfaces/discord_spine_integration_v1.py
    — added actuator_proof to spine builder capabilities
  data/registries/local_worker_adapter_registry_v1.json
    — added actuator_proof capability
  tests/test_canonical_registry_bootstrap_v1.py
    — updated counts from 11 to 12, added !actuator-proof to expected set
```

## Current Maturity State

From VPS (no relay connection): L0_SIMULATED
This is correct. Real actuation requires the Windows relay to be
running on the founder's logged-in desktop.

## Final Output

```
W0 REAL ACTUATOR MATURITY LEVERAGE PROOF — COMPLETE

Backend evaluated: YES
Backend selected: windows_interactive_desktop_relay
Real Chrome process launched: NO (VPS-only, relay not connected)
Window handle observed: NO (requires relay)
Foreground focus observed: NO (requires relay)
Screenshot captured: NO (requires relay)
Founder visual confirmation: NO (requires relay + founder)
Actuator maturity level: L0_SIMULATED (VPS-side correct)
Dry-run separated from real actuation: YES

Next gate: W0_REAL_FOREGROUND_CU_INGESTION_RETRY
```

## Commit

```
phase968an: prove actuator maturity model and backend leverage evaluation
```
