# Founder Visual Confirmation Gate v1

## Doctrine

When CU acts through a local visible GUI and the remote orchestrator
cannot independently verify the visible result, founder visual
confirmation can be required before final maturity is accepted.

## Why This Gate Exists

The VPS orchestrator (Linux) drives CU execution on the Windows desktop
remotely via SSH + Task Scheduler /IT. The VPS receives output files
but has no camera, screen share, or independent sensor on the Windows
display. It trusts the output of the PowerShell UI Automation script.

This is strong evidence — the script reads the Chrome accessibility tree
and produces structured JSON. But it is not independently verifiable
from the VPS. The founder's eyes are the only independent verifier
available.

## When This Gate Applies

- CU drove a visible GUI action on a remote machine
- The founder was not physically present during execution
- No independent verification mechanism (camera, screen recording) exists
- The maturity claim depends on what appeared on screen

## When This Gate Does NOT Apply

- API-only paths (no GUI involved)
- Founder was present and visually confirmed
- An independent verification mechanism recorded the screen
- The founder explicitly waives the gate

## Confirmation Statuses

| Status | Meaning |
|--------|---------|
| CONFIRMED | Founder visually verified the CU output |
| NOT_CONFIRMED | Gate active, no founder response yet |
| NOT_REQUIRED | Founder waived or not applicable |
| REQUIRED | Waiting for founder confirmation |
| EXPIRED | Confirmation was given but is no longer valid |
| INVALID | Confirmation was rejected or retracted |

## How to Resolve

The founder can resolve this gate by:

1. **Re-running the CU inventory** on the Windows desktop while
   physically present, confirming Chrome opens, Drive loads,
   and 26 files are visible with the correct account.

2. **Retrospectively confirming** by reviewing the evidence file
   (visible_drive_inventory.json) and the Phase 95 reports,
   and stating that the output matches their knowledge of
   their Drive contents.

3. **Waiving the gate** by setting confirmation to NOT_REQUIRED,
   accepting the remote execution evidence as sufficient.

## Impact on Maturity

- While gate is REQUIRED or NOT_CONFIRMED: maturity is provisional
- While gate is CONFIRMED or NOT_REQUIRED: maturity can finalize
- While gate is EXPIRED or INVALID: maturity reverts to provisional

## Code Reference

- Gate: core/adapter_package_manager/cu_founder_confirmation_gate.py
- Builder: build_w_gdrive_cu_founder_confirmation_gate()
- Resolver: apply_founder_confirmation(gate, status, response)
