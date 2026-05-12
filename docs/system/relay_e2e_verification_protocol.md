# Relay End-to-End Verification Protocol

> Date: 2026-05-12
> Module: runtime/transport/windows_desktop_relay_client.py
> Script: scripts/verify_relay_end_to_end.sh

---

## Prerequisites

1. **WSL environment** — script must run from WSL (not VPS, not native Windows)
2. **Tailscale up** — both VPS and Windows machine on the same Tailscale network
3. **Windows relay running** — PowerShell relay process active on the Windows host
4. **/mnt/c accessible** — WSL can reach the Windows filesystem

## Starting the Windows Relay

On the Windows machine (PowerShell as Administrator):

```powershell
cd $env:USERPROFILE\eos_advisor_messages\windows_desktop_relay
.\scripts\windows_interactive_desktop_relay.ps1
```

Or from the VPS via SSH-over-Tailscale to the Windows machine:

```bash
ssh windows-host "powershell -File C:\Users\<username>\eos_advisor_messages\windows_desktop_relay\scripts\windows_interactive_desktop_relay.ps1"
```

The relay must be running and writing heartbeats before verification.

## Expected Heartbeat Behavior

The Windows relay writes a heartbeat file every ~10 seconds:

```
<relay_root>/heartbeats/windows_relay_heartbeat.json
```

Contents:

```json
{
  "timestamp": "2026-05-12T15:30:00Z",
  "relay_version": "1.0",
  "status": "running"
}
```

The verification script checks that this file exists and was modified
within the last 60 seconds. If stale, the relay is not running.

## Running the Verification

From WSL:

```bash
cd /opt/OS
./scripts/verify_relay_end_to_end.sh
```

The script:
1. Detects WSL (checks /mnt/c)
2. Resolves the relay root via `_default_relay_root()` (uses `cmd.exe` → `%USERPROFILE%`)
3. Checks heartbeat freshness (must be < 60 seconds old)
4. Sends a dry-run PING request to the relay inbox
5. Polls the outbox for 30 seconds for the relay's response

## PASS Criteria

All must be true:
- WSL detected
- Relay root directory exists
- Heartbeat file exists and is fresh (< 60s)
- PING request successfully written to inbox
- Relay processes the PING and writes result to outbox within 30s
- Proof artifact written to `data/runtime/workstation_relay/proofs/<timestamp>_ping.json`

## Common Failure Modes

| Failure | Cause | Fix |
|---------|-------|-----|
| `/mnt/c not found` | Running on VPS, not WSL | Run from WSL session |
| `Relay root does not exist` | Windows user home resolution failed, or relay never initialized | Run `mkdir -p` on the relay root from Windows |
| `No heartbeat file` | Windows relay not running | Start the PowerShell relay script |
| `Heartbeat stale` | Relay crashed or was stopped | Restart the PowerShell relay |
| `Timeout (30s)` | Relay running but not processing inbox | Check relay logs on Windows; may need restart |
| `Linux home path used` | `_resolve_windows_home()` fell through to `Path.home()` | Ensure `cmd.exe` is accessible from WSL |

## Proof Artifacts

Each verification run writes a JSON proof to:

```
data/runtime/workstation_relay/proofs/<ISO_UTC>_ping.json
```

Fields:
- `timestamp` — UTC ISO timestamp of the run
- `request_id` — unique PING request identifier
- `relay_root` — resolved relay root path
- `heartbeat_age_seconds` — age of heartbeat at check time
- `poll_result_status` — relay response status or "timeout"
- `poll_result_raw` — full relay response JSON

## After First Successful PASS

The relay end-to-end path is proven. This unblocks:
1. Work order dispatch from VPS to local Windows execution
2. Computer Use (CU) actions via the relay
3. GUI actuation proofs with real screenshots
