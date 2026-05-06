# Founder Visual Confirmation Gate v1

**Phase:** 96.8E (updated from Phase 95)
**Status:** Active
**Layer:** UMH Substrate — Execution Proof (Human Approval Adapter)
**Module:** `core/environment_bridge/chrome_visible_launch.py`

## Doctrine

Process existence is not proof. Window metadata is not proof.
Only founder visual confirmation constitutes proof that a GUI
application is visibly open on the desktop.

## Why

WSL/tmux execution can spawn Windows processes via interop without
reliable foreground visibility. Chrome can report `MainWindowHandle != 0`
and `MainWindowTitle = "Google Drive"` while no visible window exists
on the founder's desktop. This was confirmed during Phase 96.8D local
testing — the worker advanced to VERIFY_ACTIVE_GOOGLE_ACCOUNT based on
metadata that was a false positive.

## When This Gate Applies

- CU drove a visible GUI action on a remote/local machine
- Process/window metadata cannot reliably prove foreground visibility
- No independent verification mechanism (camera, screen recording) exists
- The maturity claim depends on what appeared on screen

## When This Gate Does NOT Apply

- API-only paths (no GUI involved)
- An independent verification mechanism recorded the screen
- A future Windows Interactive Desktop Adapter provides reliable proof
- The founder explicitly waives the gate

## Gate Flow

```
Worker launches Chrome via direct executable
  → Collects process/window metadata as EVIDENCE
  → Writes chrome_launch_proof
  → Writes visible_chrome_confirmation_request
  → Status: PENDING_FOUNDER_VISUAL_CONFIRMATION
  → BLOCKED — waiting for founder

Founder observes desktop
  → Writes confirmation: confirmed=true or confirmed=false
  → Worker reads confirmation from inbox

  confirmed=true  → FOUNDER_CONFIRMED_VISIBLE → VERIFY_ACTIVE_GOOGLE_ACCOUNT
  confirmed=false → FOUNDER_DENIED_VISIBLE → BLOCKED
```

## Metadata Evidence Levels

| Level | Meaning | Proof? |
|-------|---------|--------|
| `none` | No Chrome processes found | NO |
| `process_detected_only` | PIDs exist, no window metadata | NO |
| `window_metadata_detected` | MainWindowHandle/Title nonzero | NO |

Metadata supports the proof artifact (auditable evidence) but CANNOT
finalize pass. Only `founder_confirmed_visible` passes the gate.

## How to Confirm

Founder runs on local WSL:

```bash
# Chrome IS visibly open:
python3 /opt/OS/eos_ai/substrate/write_founder_gate_confirmation.py \
  --work-order-id WO-LOCAL-PILOT-GDRIVE-GDOCS-001 \
  --gate VISIBLE_CHROME_LAUNCH \
  --confirmed true \
  --notes "Chrome visibly open with Google Drive"

# Chrome is NOT visibly open:
python3 /opt/OS/eos_ai/substrate/write_founder_gate_confirmation.py \
  --work-order-id WO-LOCAL-PILOT-GDRIVE-GDOCS-001 \
  --gate VISIBLE_CHROME_LAUNCH \
  --confirmed false \
  --notes "Chrome did not visibly open"
```

The confirmation file is written to `~/eos_advisor_messages/inbox/`
where the worker polls for it.

## Confirmation File Format

```json
{
  "response_type": "founder_visual_confirmation",
  "work_order_id": "WO-LOCAL-PILOT-GDRIVE-GDOCS-001",
  "gate": "VISIBLE_CHROME_LAUNCH",
  "confirmed": true,
  "visible_app": "Google Chrome",
  "notes": "Chrome visibly open with Google Drive",
  "timestamp": "2026-05-06T..."
}
```

## Confirmation Statuses

| Status | Meaning |
|--------|---------|
| `pending_founder_visual_confirmation` | Waiting for founder |
| `founder_confirmed_visible` | Founder confirmed GUI visible |
| `founder_denied_visible` | Founder confirmed GUI NOT visible |
| `chrome_not_found` | No Chrome processes at all |
| `launch_method_disallowed` | explorer/default-browser used |

## Impact on Gate Progression

- `pending` → VERIFY_ACTIVE_GOOGLE_ACCOUNT blocked
- `founder_confirmed_visible` → VERIFY_ACTIVE_GOOGLE_ACCOUNT proceeds
- `founder_denied_visible` → worker stops, investigation required

## Future: Windows Interactive Desktop Adapter

A future Windows Interactive Desktop Adapter could provide reliable
foreground proof without founder manual confirmation. Until then,
founder visual confirmation is the hard proof gate.

See: `docs/operations/windows_interactive_desktop_adapter_requirement_v1.md`

## Code Reference

- Gate module: `core/environment_bridge/chrome_visible_launch.py`
- Confirmation helper: `eos_ai/substrate/write_founder_gate_confirmation.py`
- Worker integration: `eos_ai/substrate/local_worker_auto_loop.py`
