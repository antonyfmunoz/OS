# Windows Relay Runtime Runbook v1

**Phase:** 96.8J
**Status:** Active

This runbook covers the three environments involved in the Windows
Interactive Desktop Relay and exact commands for each.

---

## Environment Map

| Label | Environment | Machine | Role |
|-------|-------------|---------|------|
| A | VPS Claude Code (tmux) | VPS 100.77.233.50 | Orchestration, control, packet construction |
| B | Windows PowerShell 5.1 | Local Windows desktop | Relay -- GUI actuation, runs in logged-in session |
| C | WSL tmux | Local WSL instance | Client -- writes requests, reads results |

Communication: A instructs C via SSH/tmux. C writes JSON to shared
filesystem. B reads, processes, writes result. C reads result.

---

## Prerequisites

- Windows desktop is logged in with founder account
- Chrome is installed at standard path
- PowerShell is available (Windows PowerShell 5.1 ships with Windows 10/11)
- WSL has access to /mnt/c (default on Windows with WSL installed)
- OS repo is cloned at /opt/OS on VPS and accessible from WSL

---

## B: Starting the Windows Relay

Open PowerShell in the logged-in Windows desktop session.

Navigate to the repo or copy the relay script, then run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\windows_interactive_desktop_relay.ps1
```

Or with pwsh (PowerShell 7+):

```powershell
pwsh scripts\windows_interactive_desktop_relay.ps1
```

Expected startup output:

```
[HH:MM:SS] [relay] ==========================================
[HH:MM:SS] [relay] Windows Interactive Desktop Relay v1
[HH:MM:SS] [relay] Phase 96.8I (PS 5.1 compatible)
[HH:MM:SS] [relay] ==========================================
[HH:MM:SS] [relay] Inbox:  C:\Users\antonys beast pc\eos_advisor_messages\windows_desktop_relay\inbox
[HH:MM:SS] [relay] Outbox: C:\Users\antonys beast pc\eos_advisor_messages\windows_desktop_relay\outbox
[HH:MM:SS] [relay] Poll:   2s
[HH:MM:SS] [relay] PowerShell version: 5.1.x.x
[HH:MM:SS] [relay] Watching inbox for requests...
```

The relay creates inbox/outbox directories automatically if missing.

To stop: press Ctrl+C in the PowerShell window.

---

## C: Running PING from WSL

From a WSL terminal (or tmux session):

```bash
cd /opt/OS && python3 eos_ai/substrate/windows_desktop_relay_client.py \
  --action PING \
  --relay-root "/mnt/c/Users/antonys beast pc/eos_advisor_messages/windows_desktop_relay" \
  --timeout 30 \
  --debug
```

Expected output (success):

```json
{
  "relay_inbox_exists": true,
  ...
  "status": "completed",
  "request_id": "REQ-PING-...",
  "result": {
    "adapter_status": "pong",
    ...
  }
}
```

The critical field is `adapter_status: pong`.

---

## C: Running Chrome Open from WSL (NEXT GATE -- DO NOT RUN YET)

This command is documented for the CHROME_OPEN_VISIBLE_PROOF gate.
Do not run until that gate is explicitly opened.

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

---

## Troubleshooting

### UTF-8 BOM parse error

**Symptom:** WSL client finds result file but json.load fails with
"Unexpected UTF-8 BOM".

**Cause:** PowerShell 5.1 `Out-File -Encoding UTF8` prepends a 3-byte
BOM (EF BB BF).

**Fix:** Already fixed in Phase 96.8I. The WSL client reads with
`encoding="utf-8-sig"` which strips the BOM silently. If you see this
error, pull latest code.

### PowerShell 5.1 ConvertFrom-Json -AsHashtable

**Symptom:** Relay crashes on startup or on first request with
"A parameter cannot be found that matches parameter name AsHashtable".

**Cause:** `-AsHashtable` was added in PowerShell 6. Windows ships
with PowerShell 5.1.

**Fix:** Already fixed in Phase 96.8I. The relay uses `ConvertFrom-Json`
without `-AsHashtable`, then converts via `ConvertTo-Hashtable` helper.
If you see this error, pull latest code.

### Dirty git working tree on Windows

**Symptom:** `git status` shows thousands of modified files after
pulling on Windows.

**Cause:** Line ending conversion (CRLF vs LF) or generated graph/palace
files that differ between VPS and local.

**Fix:** These are generated files. Run `git checkout -- 10_Wiki/` to
discard generated changes, or commit them. The graph files are rebuilt
by `scripts/update-graph` and are safe to regenerate.

### Windows-invalid filenames

**Symptom:** `git clone` or `git pull` fails on Windows with
"Invalid argument" or "filename not valid".

**Cause:** Files with colons (`:`) in their names. NTFS does not allow
colons in filenames.

**Fix:** Rename files on the Linux/VPS side to replace colons with
underscores. Already addressed in commit ed722684.

### Relay not running

**Symptom:** WSL client times out after writing request.

**Cause:** The Windows PowerShell relay is not started, or it crashed.

**Fix:** Start the relay in a PowerShell window on the Windows desktop.
Check for error output in the PowerShell console.

### Wrong relay root

**Symptom:** WSL client writes request but relay never sees it, or
relay writes result but client never finds it.

**Cause:** Path mismatch between WSL client and Windows relay.

**Fix:** Both sides must agree on the relay root. The canonical path is:
- Windows: `%USERPROFILE%\eos_advisor_messages\windows_desktop_relay`
- WSL: `/mnt/c/Users/{username}/eos_advisor_messages/windows_desktop_relay`

Use `--relay-root` on the WSL client and `-InboxPath`/`-OutboxPath`
on the PowerShell relay to override if needed.

Verify with `--debug` flag on the WSL client to see resolved paths.

### Request processed but no result file

**Symptom:** Relay logs "Processing: REQ-PING-xxx.json" but no
result file appears in outbox.

**Cause:** Handler threw an unhandled exception before Write-Result.

**Fix:** Already hardened in Phase 96.8I. All handlers are wrapped in
try/catch that writes error results. Check the PowerShell console for
ERROR log lines. If you see this, pull latest code.
