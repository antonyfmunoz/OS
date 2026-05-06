# Local Pull Worker as Tmux Relay v1

**Phase:** 96.8D
**Status:** Active
**Layer:** UMH Substrate — Execution Plane
**Modules:** `eos_ai/substrate/local_worker_auto_loop.py`, `core/environment_bridge/`

## Purpose

Documents that the local pull worker is the permanent "VPS sends to
local tmux" system. It is not a temporary workaround — it IS the relay.

## Architecture

```
VPS Orchestrator
  │
  ├── Creates governed work packet (w0_packet_builder.py)
  ├── Places packet in VPS outbox (/opt/OS/data/work_queue/outbox/)
  │
  ▼
Local Pull Worker (running in tmux on WSL)
  │
  ├── Polls VPS outbox (or copies from it via scp/rsync)
  ├── Claims packet
  ├── Validates packet (routing fields, governance, proof requirements)
  ├── Runs safe preflight
  ├── Runs GUI backend healthcheck
  ├── Requests first gate approval
  ├── Waits for advisor response
  ├── Executes approved action (direct Chrome executable launch)
  ├── Collects visible-window proof
  ├── Writes proof artifact
  ├── Stops at VERIFY_ACTIVE_GOOGLE_ACCOUNT (if proof passes)
  │
  ▼
Founder (physically present)
  │
  ├── Visually confirms correct Google account
  ├── Reports confirmation via observation checklist
  │
  ▼
Results synced back to VPS
```

## Why Pull, Not Push

Phase 96.8C proved that VPS → local SSH push is blocked by the VPS
sandbox classifier. All outbound network commands (ping, ssh, tailscale)
were blocked. The SSH key and target exist, but execution is prevented.

This is a fundamental constraint, not a configuration error. The bridge
doctrine's "Pull over push" design decision was validated empirically.

## What the Founder Does

The founder's role is strictly:

1. **One-time bootstrap** — run local WSL setup commands (Phase 96.8B)
2. **Approval gates** — respond to approval requests at governed gates
3. **Visual confirmation** — confirm correct Google account visible in Chrome
4. **Report results** — use observation checklist to report confirmation

The founder does NOT:
- Manually patch packet fields
- Manually launch Chrome
- Manually run CU commands
- Debug worker errors

## What the Worker Does Automatically

After bootstrap, the worker handles:
- Packet loading and validation
- Preflight checks
- GUI backend healthcheck
- Approval request emission
- Chrome direct executable launch
- Visible-window proof collection
- Proof artifact writing
- Gate progression/blocking

## Packet Schema Correction

Phase 96.8D corrected the W0-001 packet to include all required
routing fields so manual patching is never needed:

| Field | Value | Purpose |
|-------|-------|---------|
| `target_account` | antonyfm@empyreanstudios.co | Account identity |
| `worker_mode` | auto | Automatic execution mode |
| `approval_routing` | advisor_relay | Approval goes through advisor |
| `preferred_backend` | GUI_COMPUTER_USE | Direct Chrome, not explorer |
| `playwright_enabled` | false | No Playwright |
| `screenshot_capture` | false | No screenshots |
| `cdp_enabled` | false | No Chrome DevTools Protocol |

## Generating a Correct Packet

```python
from core.environment_bridge.w0_packet_builder import build_w0_001_packet
packet = build_w0_001_packet()
```

This produces a packet with all routing, governance, proof, and
adapter boundary fields populated. No manual patching required.
