# Phase 96.8F — Execution Binding Contract Report

**Date:** 2026-05-06
**Status:** COMPLETE
**Gate:** COMMIT_AND_PUSH_PHASE_968F

---

## Founder Correction

The system previously collapsed environment, execution surface,
application, target service, capability, and proof into a single
`preferred_backend: GUI_COMPUTER_USE` field.

This allowed ambiguity where:
- WSL could route through `explorer.exe` instead of Chrome
- Default browser handling could open Edge instead of Chrome
- No layer explicitly declared which application was required
- No layer explicitly declared which service was being accessed

The founder corrected: each of these is a distinct concept. UMH must
bind all layers explicitly before execution.

---

## Why "Backend" Was Too Vague

`GUI_COMPUTER_USE` as a backend concept tries to answer 6 questions
simultaneously:

1. **Where?** (environment — Windows desktop)
2. **Via what?** (execution surface — PowerShell/WSL/tmux)
3. **Using what?** (application — Chrome)
4. **Accessing what?** (target service — Google Drive)
5. **Doing what?** (capability — read file inventory)
6. **Proving what?** (proof — founder saw it happen)

Each of these can vary independently. Collapsing them into one field
prevents the system from validating any single layer.

---

## The 6-Layer Execution Binding Model

```
┌──────────────────────────────────────────┐
│ 1. Environment                           │
│    local_windows_desktop                 │
│    windows_desktop                       │
│    interactive_user_session_required      │
├──────────────────────────────────────────┤
│ 2. Execution Surfaces                    │
│    wsl_tmux_worker → orchestrator        │
│    windows_powershell_relay → gui_actuator│
├──────────────────────────────────────────┤
│ 3. Application                           │
│    google_chrome_windows                 │
│    direct_executable                     │
│    BLOCKED: explorer/default/shell/generic│
├──────────────────────────────────────────┤
│ 4. Target Services                       │
│    google_drive (google_workspace)       │
│    google_docs (google_workspace)        │
├──────────────────────────────────────────┤
│ 5. Capabilities                          │
│    browser.open_url_in_application       │
│    google_drive.read_file_inventory      │
│    google_docs.extract_tabs              │
├──────────────────────────────────────────┤
│ 6. Proof                                 │
│    founder_visual_confirmation           │
│    BLOCKED: process_exists_only          │
│    BLOCKED: window_metadata_only         │
└──────────────────────────────────────────┘
```

---

## Application Binding Law

If a work packet specifies an application, that exact application must
be launched via the declared method. Generic OS shell routing is
disallowed unless the application contract explicitly permits it.

For Chrome:
- `direct_executable` → ALLOWED
- `explorer_url` → BLOCKED
- `default_browser` → BLOCKED
- `shell_url_open` → BLOCKED
- `generic_start_url` → BLOCKED
- `unknown_browser` → BLOCKED

---

## How This Prevents Chrome vs Explorer Confusion

The binding declares `launch_method: direct_executable` and includes
`explorer_url` in `disallowed_launch_methods`. The validator rejects
any binding where the launch method is in the disallowed list.

Before Phase 96.8F: system could route through explorer and claim
"Chrome launched" because a Chrome process appeared.

After Phase 96.8F: system must prove the launch method was
`direct_executable` with the correct Chrome path. Any other method
fails validation before execution begins.

---

## UMH External Boundary Law Alignment

The External Boundary Law requires governed adapter boundaries for
all external system interactions. The Execution Binding Contract
extends this by requiring that every adapter boundary work packet
declares explicit bindings for all 6 layers.

A packet with missing or invalid `execution_binding` is rejected
by both the packet validator and the local worker validator.

---

## Files Created

| File | Purpose |
|------|---------|
| core/environment_bridge/execution_binding_contracts.py | 6-layer typed execution binding model |
| core/environment_bridge/execution_binding_validator.py | Validates bindings across all layers |
| tests/test_execution_binding_contracts.py | 19 tests for binding model |
| tests/test_application_binding_law.py | 25 tests for application binding rules |
| tests/test_w0_execution_binding.py | 24 tests for W0 integration |
| docs/operations/execution_binding_contract_v1.md | Execution binding doctrine |
| docs/operations/application_binding_law_v1.md | Application binding law |
| docs/operations/application_registry_doctrine_v1.md | Application registry doctrine |

## Files Updated

| File | Change |
|------|--------|
| core/environment_bridge/w0_packet_builder.py | Emits execution_binding with all 6 layers |
| core/environment_bridge/packet_validator.py | Validates execution_binding on W0 packets |
| eos_ai/substrate/local_worker_auto_loop.py | Validates execution_binding from packet |
| tests/test_local_worker_visible_chrome_gate.py | Updated fixture to include execution_binding |

---

## Tests Passed

| Test File | Tests | Status |
|-----------|-------|--------|
| test_execution_binding_contracts.py | 19 | PASS |
| test_application_binding_law.py | 25 | PASS |
| test_w0_execution_binding.py | 24 | PASS |
| test_w0_packet_required_routing.py | 20 | PASS |
| test_local_worker_visible_chrome_gate.py | 15 | PASS |
| test_founder_visual_confirmation_gate.py | 18 | PASS |
| test_environment_packet_validator.py | 10 | PASS |
| test_environment_work_packet.py | 14 | PASS |
| **Total** | **145** | **ALL PASS** |

---

## Status

| Item | Status |
|------|--------|
| Memory promoted | NO |
| Committed | NO (awaiting explicit instruction) |
| Pushed | NO |
| W0-001 CU executed | NO |
| Drive/Docs accessed | NO |
| Secrets captured | NO |
