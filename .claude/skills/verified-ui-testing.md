---
name: verified-ui-testing
description: "Use when any cockpit UI change, agent behavior, or Meta IDE feature needs production verification — loops browser + devtools + logs until confirmed with proof."
allowed-tools: Bash, Read, Write
---

# Verified UI Testing Protocol

## When to use

After ANY change that affects what the operator sees or
what an agent does through the cockpit. This includes:
- Cockpit UI changes (panels, components, stores, API routes)
- Agent behavior changes visible in cockpit
- Meta IDE features (file trees, editor, terminals, sessions)
- Any deployed frontend or backend change that has a UI surface

## Philosophy

No change is done until a real browser confirms it works.
Not once — three times. Not just visually — with network
proof, console proof, and server log proof.
Loop until all layers confirm. Ship proof, not promises.

## The Loop

Every verification pass has 4 layers. All 4 must pass.
If any layer fails, diagnose, fix, and restart the loop.

```
┌─────────────────────────────────────────────┐
│  PASS N (repeat 3x with fresh page loads)   │
│                                             │
│  1. BROWSER — Playwright snapshot           │
│     Navigate → wait for target element →    │
│     snapshot → confirm expected DOM state    │
│                                             │
│  2. NETWORK — Chrome DevTools               │
│     list_network_requests → filter API      │
│     calls → confirm 200s, no 401/499/5xx    │
│                                             │
│  3. CONSOLE — Chrome DevTools               │
│     list_console_messages(types:["error"])   │
│     → confirm zero errors related to the    │
│     changed feature                         │
│                                             │
│  4. SERVER LOGS — Bash                      │
│     docker logs <container> --tail 50       │
│     → confirm no tracebacks, no auth        │
│     failures, no timeouts on relevant       │
│     endpoints                               │
│                                             │
│  ALL 4 PASS? → next pass                    │
│  ANY FAIL?   → diagnose → fix → restart     │
└─────────────────────────────────────────────┘

3 consecutive full passes = CONFIRMED
```

## Execution

### Before starting
1. Deploy the change (cockpit: `bash cockpit/deploy.sh`,
   backend: `docker restart <container>`)
2. Wait for service health — curl the relevant endpoint,
   confirm non-timeout response
3. If cockpit deploy, verify SSH tunnel is forwarding:
   `flyctl ssh console --app umh-cockpit -C "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8091/api/umh/bootstrap"`
   Must return 401 (auth required = alive)

### Pass execution (repeat 3x)

#### Layer 1: Browser (Playwright MCP)
```
browser_navigate → target URL
browser_wait_for → key element text
browser_snapshot → capture DOM state
```
Confirm: expected elements present, correct text,
correct structure. Not "page loaded" — the SPECIFIC
elements the change affects.

#### Layer 2: Network (Chrome DevTools MCP)
```
list_network_requests(resourceTypes: ["fetch", "xhr"])
```
Confirm:
- All API calls to changed endpoints returned 200
- No 401 (auth failure), 499 (timeout), 5xx (server error)
- Response sizes are non-zero (not empty arrays when data expected)

#### Layer 3: Console (Chrome DevTools MCP)
```
list_console_messages(types: ["error"])
```
Confirm:
- Zero errors related to the changed feature
- Ignore known noise (third-party scripts, favicon, etc.)
- Any new error = investigate before continuing

#### Layer 4: Server Logs (Bash)
```bash
docker logs <container> --tail 50 --since 2m
```
Confirm:
- No Python tracebacks
- No auth failures on relevant endpoints
- No connection timeouts
- Clean request/response cycle for the tested feature

### After 3 passes

#### Generate proof
Write a proof summary to the conversation:
```
VERIFIED UI TEST — <feature name>
Date: YYYY-MM-DD
Commit: <hash>
Target: <URL / panel / component>

Pass 1: ✓ Browser ✓ Network ✓ Console ✓ Logs
Pass 2: ✓ Browser ✓ Network ✓ Console ✓ Logs
Pass 3: ✓ Browser ✓ Network ✓ Console ✓ Logs

Evidence:
- DOM: <what was confirmed in snapshot>
- API: <which endpoints returned 200>
- Console: <error count = 0>
- Logs: <container, clean>

RESULT: CONFIRMED
```

## Failure patterns and fixes

### Tunnel down (499s on all API calls)
```bash
# Check VPS operator API
curl -s -m 5 http://localhost:8091/api/umh/bootstrap
# If timeout → restart container
docker restart os-operator
# Wait 15s, re-verify
```

### Auth race (401 on first load, works on refresh)
The change didn't properly gate on `bootstrapLoaded`.
Check the component's useEffect dependencies.

### Empty data (200 but no entries)
Backend returns empty — check the data source:
```bash
# VPS file tree
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from substrate.workstation.file_browser import browse_directory
print(len(browse_directory('/')))
"
# Beast SSH
ssh "antonys beast pc@100.74.199.102" "powershell -c 'Get-ChildItem C:\ | Select Name'"
```

### Stale connections (docker-proxy CLOSE_WAIT pile-up)
```bash
ss -tnp | grep <port> | grep CLOSE-WAIT | wc -l
# If > 10 → restart container
docker restart <container>
```

## What this replaces

This protocol replaces:
- "I deployed it, should be working" (no verification)
- Single page load checks (fluke-prone)
- Screenshot-only validation (misses network/log issues)
- "Tests pass" without browser confirmation
  (tests verify code correctness, not feature correctness)

## Gotchas

- Playwright MCP and Chrome DevTools MCP are separate
  browser contexts — Playwright for DOM, DevTools for
  network/console. Use both.
- localStorage caches old data — a "working" page might
  be showing stale cached trees. Check network tab to
  confirm fresh API responses, not cache hits.
- SSH tunnel from Fly container can appear connected
  (process running, Tailscale up) but not forward traffic.
  Always verify with curl from inside the container.
- After operator API restart, wait 15s before testing —
  uvicorn + FastAPI startup takes time with large apps.
- Console errors from Clerk/third-party scripts are noise.
  Only flag errors from the app's own code.
