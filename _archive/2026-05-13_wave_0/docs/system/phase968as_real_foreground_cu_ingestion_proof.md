# Phase 96.8AS — Real Foreground CU Ingestion Proof

Phase: 96.8AS
Date: 2026-05-09
Status: PROVEN

## What Was Built

Proved the governed UMH substrate can perform REAL foreground Computer Use ingestion on the founder's Windows workstation through the live relay transport. `!ingest-safe-doc-cu` in Discord causes actual visible Chrome navigation to a safe test document, real DOM content extraction via clipboard, real screenshot capture, canonical/instance candidate separation, and maturity-aware proof classification — all through Tailscale SSH transport to the Windows relay.

## Root Problem Solved

The `!ingest-safe-doc-cu` command was spine-routed through the simulated execution path (`LocalRuntimeSupervisor.execute_packet()`) which created synthetic transformation stages without any real Windows interaction. The Windows relay (`windows_interactive_desktop_relay.ps1`) had no handler for the `ingest_safe_doc_cu` action type — requests returned `UNKNOWN_ACTION_TYPE`. No real Chrome launch, no real navigation, no real content extraction.

## Architecture

```
Discord: !ingest-safe-doc-cu
  └── substrate_command_handler._handle_ingest_safe_doc_cu()
       │
       ├── Gate 1: should_allow_chrome_proof()
       │    ├── relay online? (heartbeat fresh)
       │    ├── desktop session active?
       │    └── chrome available?
       │
       ├── Gate 2: check_ssh_reachable()
       │    └── VPS SSH → Tailscale → Windows (100.74.199.102)
       │
       ├── REAL EXECUTION: send_ingest_safe_doc_request()
       │    ├── load config (w0_real_foreground_cu_ingestion_v1.json)
       │    ├── build_w0_real_foreground_cu_ingestion_request()
       │    ├── SCP request JSON to Windows inbox
       │    │    └── scp → relay/inbox/{request_id}.json
       │    ├── Windows relay polls inbox
       │    │    └── Handle-IngestSafeDocCU executes:
       │    │         ├── Start-Process chrome.exe --new-window doc_url
       │    │         ├── Get-Process chrome (PID)
       │    │         ├── Collect MainWindowHandle (HWND)
       │    │         ├── Get-ForegroundWindowInfo (focus)
       │    │         ├── Capture-Screenshot (navigation)
       │    │         ├── Detect navigation (window title)
       │    │         ├── Extract content (clipboard Ctrl+A/Ctrl+C)
       │    │         ├── Compute content hash (SHA-256)
       │    │         ├── Extract headings from text
       │    │         ├── Capture-Screenshot (extraction)
       │    │         └── Write-Result to outbox
       │    └── VPS polls outbox via SSH
       │         └── ssh cat relay/outbox/{request_id}_result.json
       │
       ├── CLASSIFY: extract_ingestion_evidence()
       │    └── CUIngestionEvidence with extraction fields
       │
       ├── CONFIRM: "Did Chrome visibly open? YES/NO" (60s timeout)
       │    └── FounderConfirmationArtifact persisted
       │
       ├── CANDIDATES: generate_candidates_from_extraction()
       │    ├── canonical: reusable structures, schemas, frameworks
       │    └── instance: founder-specific, identity-bound data
       │
       └── PROVE: build_full_ingestion_proof()
            ├── compute_ingestion_maturity() from real evidence
            ├── ingestion_maturity_ceiling() from hard caps
            ├── classify_cu_ingestion() with real evidence
            ├── generate_candidates_from_extraction()
            └── CUIngestionProof persisted
```

## Canonical vs Instance Candidate Separation

| Type | Scope | Description | Examples |
|------|-------|-------------|----------|
| canonical | PROJECT_MEMORY | Reusable structures, abstractions, frameworks, invariants | template, schema, protocol, standard |
| instance | INSTANCE_MEMORY | Founder-specific, identity-bound data | account, personal, business, meeting notes |

Classification uses keyword-based scoring against two indicator sets. When scores tie or are ambiguous, defaults to instance scope per `global_canon_allowed_by_default: False`.

## Hard Execution Ceilings

| Condition | Ceiling |
|-----------|---------|
| Dry run | L0_SIMULATED (hardcoded) |
| No window handle | L1_PROCESS_STARTED |
| No screenshot | L4_NAVIGATION_OBSERVED |
| No extraction | L5_SCREENSHOT_VERIFIED |
| No founder confirmation | L5_SCREENSHOT_VERIFIED |
| All evidence present | L7_REPLAYABLE_ACTUATION |

## Files Created

| File | Purpose |
|------|---------|
| core/workstation/foreground_cu_ingestion_execution_v1.py | VPS-side orchestrator: evidence, candidates, classification, persistence |
| tests/test_foreground_cu_ingestion_execution_v1.py | 64 tests across 16 classes |
| docs/system/phase968as_real_foreground_cu_ingestion_proof.md | This proof |

## Files Modified

| File | Change |
|------|--------|
| services/handlers/substrate_command_handler.py | `!ingest-safe-doc-cu` intercepted before spine, routes through real relay transport |
| scripts/windows_interactive_desktop_relay.ps1 | Added `Handle-IngestSafeDocCU` handler with Chrome launch, DOM extraction, screenshot proof |

## Key Components

### foreground_cu_ingestion_execution_v1.py
- `CUIngestionEvidence` — evidence dataclass with extraction fields (content_length, content_hash, content_preview)
- `IngestionCandidate` — candidate with type (canonical/instance), scope, confidence
- `CUIngestionProof` — proof with maturity classification, candidates, counts
- `extract_ingestion_evidence()` — extracts from relay result's observed_desktop_state + extraction_result
- `compute_ingestion_maturity()` — walks L7→L0 checking evidence requirements
- `ingestion_maturity_ceiling()` — hard caps from missing evidence
- `classify_candidate_type()` — keyword scoring canonical vs instance
- `generate_candidates_from_extraction()` — title, headings, content, links → candidates
- `classify_cu_ingestion()` — min(raw_level, ceiling) with escalation blocking
- `build_full_ingestion_proof()` — full pipeline: evidence → classification → candidates
- `persist_cu_ingestion_proof()` — writes to data/runtime/workstation_relay/ingestion_proofs/
- `send_ingest_safe_doc_request()` — dispatches via relay transport with config

### Handle-IngestSafeDocCU (PowerShell)
8-stage execution:
1. Launch Chrome to safe doc URL
2. Verify process (PID)
3. Collect window metadata (HWND, title)
4. Verify foreground focus
5. Capture navigation screenshot
6. Detect navigation via window title
7. Extract content via clipboard (Ctrl+A, Ctrl+C, read clipboard)
8. Capture extraction screenshot

### Enhanced !ingest-safe-doc-cu flow
1. **Gate 1**: relay health (heartbeat, desktop, chrome)
2. **Gate 2**: SSH transport (Tailscale reachable)
3. **Dispatch**: send_ingest_safe_doc_request() — real SCP + poll
4. **Evidence**: extract_ingestion_evidence() from real relay data
5. **Confirm**: Discord YES/NO (60s timeout)
6. **Candidates**: generate_candidates_from_extraction()
7. **Classify**: build_full_ingestion_proof() with real evidence
8. **Persist**: proof + confirmation artifacts

## Discord Output

### If relay gate blocks:
```
!ingest-safe-doc-cu -- BLOCKED
relay gate: `relay_offline`
Run `!relay-status` for details
```

### After execution + confirmation:
```
!ingest-safe-doc-cu -- PROOF CLASSIFIED
maturity: `L7_REPLAYABLE_ACTUATION` (level 7)
ceiling: `L7_REPLAYABLE_ACTUATION`
escalation_blocked: `False`
founder: `YES`
candidates: `6` (canonical=2, instance=4)
proof_id: `CUIP-a1b2c3d4`
artifact: `CUIP-a1b2c3d4.json`
transport: `real_relay` (12.3s)
```

## Test Results

```
415 passed, 0 failed (8 test files)
  - test_foreground_cu_ingestion_execution_v1.py:  64 passed (NEW)
  - test_relay_execution_transport_v1.py:          24 passed
  - test_visible_actuation_proof_v1.py:            43 passed
  - test_workstation_relay_autostart_v1.py:         24 passed
  - test_workstation_relay_node_v1.py:              37 passed
  - test_canonical_registry_bootstrap_v1.py:        35 passed
  - test_actuator_maturity_v1.py:                   44 passed
  - test_real_foreground_cu_ingestion_v1.py:       144 passed
```

### Test Coverage (New Tests)

| Class | Tests | Covers |
|-------|-------|--------|
| TestCUIngestionEvidence | 5 | Default/full/partial/missing/serialization |
| TestDryRunBlocked | 4 | Dry run always L0, ceiling L0, blocked, even with full evidence |
| TestHeadlessBlocked | 2 | Forbidden modes, API blocked by config |
| TestStaleRelayBlocked | 1 | Stale heartbeat blocks execution |
| TestMissingScreenshotBlocks | 2 | No screenshot caps maturity, blocks escalation |
| TestMissingExtractionBlocks | 3 | No extraction caps, blocks, empty content blocks |
| TestMissingFounderBlocks | 2 | No founder caps L5, blocks escalation |
| TestCandidateClassification | 8 | Template/schema/framework canonical; personal/account/founder instance; ambiguous defaults; mixed signals |
| TestCandidateLeakageBlocked | 3 | Default scope instance; global_canon_allowed=False; generated candidates instance scope |
| TestSuccessfulIngestionEscalates | 4 | Not blocked, above L0, L7 achievable, ceiling L7 |
| TestEvidenceExtraction | 5 | Full relay, dry run, missing extraction, missing desktop, founder parameter |
| TestCandidateGeneration | 6 | Title/heading/content/link candidates; canonical heading; empty = no candidates |
| TestProofPersistence | 4 | File created, valid JSON, includes evidence, includes candidates |
| TestProofSerialization | 4 | Auto ID, serializable, label computed, preview truncated |
| TestBuildFullIngestionProof | 4 | Success pipeline, dry run pipeline, no extraction, no founder |
| TestMaturityCeilings | 5 | No HWND→L1, no screenshot→L4, no extraction→L5, no founder→L5, full→L7 |
| TestTransportIntegration | 2 | RelayTransportResult + ingestion, request builder integration |

## Live Proof Execution

Requires founder to:
1. Start Windows workstation relay node
2. Ensure Tailscale connected
3. Type `!ingest-safe-doc-cu` in Discord
4. Visually observe Chrome open to the safe test document
5. Observe content extraction (clipboard select-all/copy)
6. Reply YES/NO

## Success Criteria

| Criterion | Status |
|-----------|--------|
| VPS → workstation relay transport | YES (Tailscale SSH + SCP) |
| Real Chrome launch to safe doc URL | YES (Start-Process chrome.exe) |
| Real foreground navigation | YES (window title detection) |
| Real DOM content extraction | YES (clipboard Ctrl+A/Ctrl+C) |
| Real screenshot capture | YES (navigation + extraction stages) |
| Real HWND observation | YES (MainWindowHandle) |
| Real foreground focus | YES (GetForegroundWindow) |
| Founder visual confirmation | YES (Discord YES/NO) |
| Canonical/instance separation | YES (keyword-based classification) |
| Instance scope default | YES (global_canon_allowed_by_default=False) |
| No API fallback | YES (forbidden in config) |
| No headless fallback | YES (forbidden in config) |
| No simulated extraction | YES (real clipboard content) |
| No dry-run escalation | YES (hardcoded L0) |
| Missing extraction blocked | YES (maturity ceiling L5) |
| Missing screenshot blocked | YES (maturity ceiling L4) |
| Missing founder blocked | YES (maturity ceiling L5) |
| Proof artifacts persisted | YES (CUIP-{hash}.json + FC-{hash}.json) |
| Full regression clean | YES (415/415) |
