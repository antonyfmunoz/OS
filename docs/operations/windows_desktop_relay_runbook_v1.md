# Windows Desktop Relay Runbook v1

**Phase:** 96.8H
**Status:** Active

## Prerequisites

1. Windows desktop is logged in with the founder's account
2. Chrome is installed at standard path
3. PowerShell is available
4. The relay directories exist (created automatically on first run)

## Starting the Relay

From a PowerShell window in the logged-in Windows session:

```powershell
# Default paths
pwsh scripts/windows_interactive_desktop_relay.ps1

# Custom paths
pwsh scripts/windows_interactive_desktop_relay.ps1 -InboxPath "C:\Users\antony\eos_relay\inbox" -OutboxPath "C:\Users\antony\eos_relay\outbox"
```

The relay will:
1. Create inbox/outbox directories if they don't exist
2. Start watching the inbox for JSON request files
3. Process requests as they arrive
4. Write results to the outbox
5. Move processed requests to a `processed` directory

## Stopping the Relay

Press Ctrl+C in the PowerShell window.

## Testing the Relay

### 1. Ping Test (from WSL)

```bash
cd /opt/OS
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from core.environment_bridge.windows_desktop_request_builder import build_ping_request
from eos_ai.substrate.windows_desktop_relay_client import send_request_and_wait
req = build_ping_request()
result = send_request_and_wait(req.to_dict(), dry_run=False)
print(result)
"
```

### 2. Dry Run Chrome Request (from WSL)

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from core.environment_bridge.windows_desktop_request_builder import build_w0_chrome_open_request
from eos_ai.substrate.windows_desktop_relay_client import send_request_and_wait
req = build_w0_chrome_open_request()
result = send_request_and_wait(req.to_dict(), dry_run=True)
print(result)
"
```

## Relay Directory Layout

```
~/eos_relay/
  inbox/           ← WSL worker writes requests here
  outbox/          ← Relay writes results here
  processed/       ← Relay moves handled requests here
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Relay not processing | Not running | Start relay from PowerShell |
| Timeout from WSL | Relay not started or wrong paths | Check relay is running, verify paths |
| Chrome not launching | Chrome not installed at standard path | Install Chrome or update path |
| Rejected request | Wrong launch method or application | Check request uses direct_executable |
| No pong response | Relay crashed or inbox path mismatch | Restart relay, verify inbox path |
