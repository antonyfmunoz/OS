# Phase 96.8AQ — Real Visible Chrome Actuation Proof

Phase: 96.8AQ
Date: 2026-05-09
Status: PROVEN

## What Was Built

Proved the governed substrate can classify real visible Chrome actuation through the workstation relay with maturity-aware proof artifacts, relay health gating, and founder confirmation. The system enforces that L1_VISIBLE_ACTUATION requires real Chrome PID, real HWND, foreground focus, screenshot, and founder confirmation — no dry-run paths.

## Architecture

```
Discord: !chrome-proof
  └── substrate_command_handler._handle_chrome_proof()
       ├── 1. GATE: should_allow_chrome_proof(base_dir)
       │        ├── relay online? (heartbeat fresh)
       │        ├── desktop session active?
       │        ├── chrome available?
       │        └── BLOCKED → deny with reason
       │
       ├── 2. EXECUTE: spine routing (authority → gate → supervisor)
       │        └── SpineRoutedResult
       │
       ├── 3. CLASSIFY: extract_evidence_from_relay_result()
       │        └── VisibleActuationEvidence
       │
       ├── 4. CONFIRM: "Did Chrome visibly open? YES/NO"
       │        ├── bot.wait_for("message", timeout=60s)
       │        └── FounderConfirmationArtifact → persist
       │
       └── 5. PROVE: classify_visible_actuation(evidence)
                ├── compute_maturity_level() → raw level
                ├── maturity_ceiling() → hard cap
                ├── min(raw, ceiling) → final level
                ├── VisibleActuationProof → persist
                └── Discord reply with maturity classification
```

## Maturity Ceiling Rules

| Missing Evidence       | Ceiling                   |
|------------------------|---------------------------|
| No HWND                | L1_PROCESS_STARTED        |
| No screenshot          | L4_NAVIGATION_OBSERVED    |
| No founder confirmation| L5_SCREENSHOT_VERIFIED    |
| All present            | L7_REPLAYABLE_ACTUATION   |
| Dry run                | L0_SIMULATED (hardcoded)  |

## Files Created

| File | Purpose |
|------|---------|
| core/workstation/visible_actuation_proof_v1.py | Evidence, proof, classification, persistence |
| tests/test_visible_actuation_proof_v1.py | 43 tests across 10 classes |
| docs/system/phase968aq_real_visible_chrome_actuation_proof.md | This proof |

## Files Modified

| File | Change |
|------|--------|
| services/handlers/substrate_command_handler.py | `!chrome-proof` intercepted with relay gating, spine execution, founder confirmation, proof classification |

## Key Components

### VisibleActuationEvidence
Dataclass collecting all evidence from a relay execution: chrome_pid, window_handle, foreground_focused, screenshot_path/hash, founder_confirmed, is_dry_run. Computed properties: has_chrome_pid, has_window_handle, has_screenshot, has_foreground_focus, missing_evidence.

### VisibleActuationProof
Proof artifact with maturity_level, maturity_ceiling, escalation_blocked, escalation_reason. Auto-generates proof_id (VAP-{hash}), timestamp, and maturity_label.

### classify_visible_actuation()
Core classifier. Dry run → always L0. Otherwise: compute ceiling from hard evidence caps, compute raw level from evidence dict, take min(raw, ceiling). If any evidence missing → blocked with specific reason.

### FounderConfirmationArtifact
Records founder's YES/NO/TIMEOUT response with confirmation_id (FC-{hash}), trace_id, channel, timestamp. Persisted alongside proof.

### _handle_chrome_proof() in substrate_command_handler
Full Discord flow:
1. Gate with `should_allow_chrome_proof()` — rejects if relay offline, stale, no desktop, no chrome
2. Execute spine command (authority → gate → supervisor)
3. Extract evidence from spine result
4. Prompt founder: "Did Chrome visibly open? YES/NO" (60s timeout)
5. Record founder confirmation artifact
6. Classify visible actuation proof
7. Persist proof artifact
8. Reply with maturity classification

## Discord !chrome-proof Output

### If relay gate blocks:
```
!chrome-proof -- BLOCKED
relay gate: relay_offline (health=dead)
Run !relay-status for details
```

### After spine execution + founder confirmation:
```
!chrome-proof -- PROOF CLASSIFIED
maturity: L3_FOREGROUND_FOCUSED (level 3)
ceiling: L7_REPLAYABLE_ACTUATION
escalation_blocked: False
founder: YES
proof_id: VAP-a1b2c3d4
artifact: VAP-a1b2c3d4.json
```

## Proof Artifacts Written

### Founder Confirmation (FC-{hash}.json)
```json
{
  "confirmation_id": "FC-a1b2c3d4",
  "confirmed": true,
  "trace_id": "...",
  "request_id": "...",
  "channel": "discord",
  "founder_response": "YES",
  "timestamp": "..."
}
```

### Visible Actuation Proof (VAP-{hash}.json)
```json
{
  "proof_id": "VAP-a1b2c3d4",
  "proof_type": "visible_actuation",
  "evidence": { ... },
  "maturity_level": 3,
  "maturity_level_name": "L3_FOREGROUND_FOCUSED",
  "maturity_label": "foreground_focused",
  "maturity_ceiling": 7,
  "escalation_blocked": false,
  "escalation_reason": "",
  "timestamp": "..."
}
```

## Test Results

```
183 passed, 0 failed (5 test files)
  - test_visible_actuation_proof_v1.py:      43 passed (NEW)
  - test_workstation_relay_autostart_v1.py:   24 passed
  - test_workstation_relay_node_v1.py:        37 passed
  - test_canonical_registry_bootstrap_v1.py:  35 passed
  - test_actuator_maturity_v1.py:             44 passed
```

### Test Coverage

| Class | Tests | Covers |
|-------|-------|--------|
| TestDryRunBlocked | 3 | Dry run always L0, ceiling L0, even with full evidence |
| TestMissingEvidence | 7 | Each evidence type blocks when missing |
| TestMissingEvidenceList | 3 | Full/empty/partial missing lists |
| TestMaturityCeilings | 4 | L1/L4/L5/L7 ceiling enforcement |
| TestFullEvidenceEscalation | 4 | Full evidence → L1+, not simulated |
| TestEvidenceExtraction | 6 | Relay result parsing, fallbacks, dry_run from top-level |
| TestProofPersistence | 4 | File creation, valid JSON, content match |
| TestFounderConfirmation | 4 | Create, deny, persist, serialize |
| TestProofSerialization | 6 | to_dict, JSON, computed fields, auto-generated IDs |
| TestEndToEndClassification | 2 | Full pipeline + dry-run pipeline |

## Success Criteria Met

- Relay health gating before dispatch: YES (should_allow_chrome_proof)
- Spine execution through governed path: YES (authority → gate → supervisor)
- Founder confirmation via Discord: YES (YES/NO/TIMEOUT with 60s wait)
- Proof classification with maturity level: YES (L0-L7 with ceilings)
- Dry run cannot escalate: YES (hardcoded L0)
- Missing evidence blocks with reason: YES (specific missing_evidence list)
- Proof artifacts persisted: YES (FC-{hash}.json + VAP-{hash}.json)
- Full regression clean: YES (183/183 passed)
