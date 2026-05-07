# Phase 96.8J -- Windows Relay Runtime Proof Report

**Date:** 2026-05-07
**Status:** COMPLETE
**Gate:** RELAY_PING_PONG_PROVEN
**Next Gate:** CHROME_OPEN_VISIBLE_PROOF

---

## Proof Achieved

The first complete WSL-to-Windows desktop relay execution loop has been
proven end-to-end:

1. VPS Claude Code session constructed a PING request via the relay client.
2. WSL tmux client wrote the request JSON to the shared relay inbox.
3. Native Windows PowerShell 5.1 relay detected, parsed, and processed
   the request inside the logged-in desktop session.
4. Relay wrote a result JSON (with UTF-8 BOM) to the shared outbox.
5. WSL client found the result, decoded it (BOM-tolerant), and verified
   adapter_status=pong.

This proves that file-based JSON relay between WSL and the Windows
interactive desktop session works. The adapter boundary is real and
functional.

---

## Environments Involved

| Label | Environment | Role |
|-------|-------------|------|
| A | VPS Claude Code (tmux) | Control/orchestration -- constructs requests, reads results |
| B | Local Windows PowerShell 5.1 | Relay -- runs in logged-in desktop session, has GUI access |
| C | Local WSL tmux | Client -- writes requests to inbox, polls outbox for results |

Communication path: A instructs C, C writes to shared filesystem, B reads
and processes, B writes result, C reads result, C reports to A.

---

## Request and Result Paths

| Artifact | Path |
|----------|------|
| Request written by C | /mnt/c/Users/{username}/eos_advisor_messages/windows_desktop_relay/inbox/{request_id}.json |
| Result written by B | C:\Users\{username}\eos_advisor_messages\windows_desktop_relay\outbox\{request_id}_result.json |
| Result read by C | /mnt/c/Users/{username}/eos_advisor_messages/windows_desktop_relay/outbox/{request_id}_result.json |
| Processed (moved by B) | C:\Users\{username}\eos_advisor_messages\windows_desktop_relay\processed\{request_id}.json |

---

## Result Shape (Sanitized)

```json
{
  "request_id": "REQ-PING-...",
  "trace_id": "TRACE-PING-...",
  "action_type": "ping",
  "adapter_status": "pong",
  "timestamp": "2026-05-07T...",
  "notes": ["Relay is alive and listening"]
}
```

The critical field is `adapter_status=pong`. This confirms the relay
is running, parsing JSON, dispatching to the correct handler, and
writing structured results.

---

## Why This Validates Environment-Native Execution

WSL and the Windows desktop session share a filesystem via /mnt/c, but
they are separate execution environments:

- WSL runs Linux processes. It cannot create Windows GUI windows.
- The Windows desktop session runs Win32 processes. It owns the display,
  the taskbar, and the interactive desktop.
- PowerShell 5.1 running in the desktop session has real GUI access
  because it runs in the same session as the logged-in user.

The PING proof validates that:
1. WSL can successfully write to the shared filesystem.
2. Windows PowerShell can read and parse that JSON.
3. PowerShell can write results back.
4. WSL can read those results (including PS 5.1 encoding quirks).
5. The entire loop completes without either side needing to cross
   the execution boundary.

---

## Universal Harness != Universal Executor

The Universal Meta Harness (UMH) does not execute everything itself.
It harnesses environment-native capabilities through adapters:

- VPS harnesses remote orchestration (SSH, API calls, scheduling).
- WSL harnesses local relay (filesystem writes to shared paths).
- Windows desktop harnesses GUI actuation (Chrome launch, window focus).

Each environment does what it is natively capable of. The harness
routes and governs. It never pretends one environment can do what
another environment owns.

This is why the relay exists: WSL cannot launch Chrome into the
Windows desktop. But it can write a JSON file asking the Windows
relay to do it. The relay, running in the desktop session, can.

---

## Known Boundaries

| Boundary | Detail |
|----------|--------|
| WSL cannot own GUI | WSL processes do not have access to the Windows desktop session. MainWindowHandle from WSL-spawned processes is unreliable. |
| VPS cannot own local desktop | VPS is a remote server. It has no display, no GUI, no local filesystem access. It orchestrates via SSH/tmux. |
| PS 5.1 JSON encoding | ConvertFrom-Json -AsHashtable does not exist in PS 5.1. Out-File -Encoding UTF8 writes BOM. Both are handled. |
| PS 5.1 object model | ConvertFrom-Json returns PSCustomObject, not hashtable. ConvertTo-Hashtable helper converts recursively. |
| Shared filesystem timing | File writes are not atomic. The relay polls on an interval. Result may not appear instantly after request. |
| No proof from metadata alone | Process ID and MainWindowHandle are evidence, not proof. Founder visual confirmation is required for GUI actions. |

---

## Bugs Fixed During Phase 96.8I (Prerequisite)

| Bug | Root Cause | Fix |
|-----|-----------|------|
| ConvertFrom-Json -AsHashtable fails | PS 5.1 does not support -AsHashtable | Added ConvertTo-Hashtable recursive helper |
| Non-ASCII characters in PS script | Smart quotes, em dashes, arrows | Full ASCII-only rewrite |
| Silent handler failure | No try/catch around dispatch | Wrapped dispatch with error result writing |
| UTF-8 BOM in result files | PS 5.1 Out-File writes BOM | WSL client reads with encoding=utf-8-sig |

---

## What Was Not Executed

| Item | Status |
|------|--------|
| W0-001 CU executed | NO |
| Chrome opened | NO |
| Drive/Docs accessed | NO |
| Gmail accessed | NO |
| Secrets captured | NO |
| GUI actions performed | NO |
| Memory promoted | NO |

---

## Next Gate: CHROME_OPEN_VISIBLE_PROOF

The next proof requires:
1. WSL client sends open_application_url request with Chrome target.
2. Windows relay launches Chrome via direct executable.
3. Relay collects process/window metadata as evidence.
4. Relay writes result with visible_proof_status=pending_founder_visual_confirmation.
5. Founder visually confirms Chrome is visible on the Windows desktop.
6. Confirmation is recorded.

This gate has NOT been attempted. It is documented here as the next
step in the relay proof sequence.

Prepared command (do not run until gate is explicitly opened):

```bash
cd /opt/OS && python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from core.environment_bridge.windows_desktop_request_builder import build_w0_chrome_open_request
from eos_ai.substrate.windows_desktop_relay_client import send_request_and_wait, resolve_relay_paths
root, inbox, outbox = resolve_relay_paths('/mnt/c/Users/antonys beast pc/eos_advisor_messages/windows_desktop_relay')
req = build_w0_chrome_open_request()
result = send_request_and_wait(req.to_dict(), relay_inbox=inbox, relay_outbox=outbox, timeout_seconds=60)
import json; print(json.dumps(result, indent=2, default=str))
"
```
