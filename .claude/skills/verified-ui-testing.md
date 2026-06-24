---
name: verified-ui-testing
description: "Use after any deployed software change with a UI or API surface — web apps, SaaS, cockpit, agent UIs, any browser-accessible system. Loops browser + devtools + logs until confirmed with proof."
allowed-tools: Bash, Read, Write
---

# Verified Software Testing Protocol

## When to use

After ANY deployed change to ANY software with a user-facing
surface. Not just cockpit — any web app, any SaaS product,
any API with a frontend, any agent that operates through a UI.

Applies to:
- Web application features (React, Vue, any framework)
- SaaS product changes (Initiate Arena, any client product)
- Cockpit/Meta IDE/admin panels
- Agent behavior visible in any UI
- API changes that affect what users see
- Auth flows, payment flows, onboarding flows
- Any deployed service with browser-accessible output

Does NOT apply to:
- Pure library/SDK changes with no deployed surface
- CLI tools (use shell-based verification instead)
- Database migrations (use query-based verification)

## Philosophy

Code that passes tests is correct code.
Code confirmed in a real browser is working software.
These are not the same thing.

No change is done until a real browser confirms it works.
Not once — three times. Not just visually — with network
proof, console proof, and server log proof.
Loop until all layers confirm. Ship proof, not promises.

## The Loop

Every verification pass has 4 layers. All 4 must pass.
If any layer fails, diagnose, fix, and restart the loop
from pass 1. Partial progress does not carry forward.

```
┌─────────────────────────────────────────────┐
│  PASS N (repeat 3x with fresh page loads)   │
│                                             │
│  1. BROWSER — Playwright MCP                │
│     Navigate → wait for target element →    │
│     snapshot → confirm expected DOM state    │
│                                             │
│  2. NETWORK — Chrome DevTools MCP           │
│     list_network_requests → filter API      │
│     calls → confirm 200s, no errors         │
│                                             │
│  3. CONSOLE — Chrome DevTools MCP           │
│     list_console_messages(types:["error"])   │
│     → zero errors from application code     │
│                                             │
│  4. SERVER LOGS — Bash                      │
│     Check logs of backing service →         │
│     no crashes, no auth failures,           │
│     no unhandled exceptions                 │
│                                             │
│  ALL 4 PASS? → next pass                    │
│  ANY FAIL?   → diagnose → fix → pass 1     │
└─────────────────────────────────────────────┘

3 consecutive full passes = CONFIRMED
```

## Before starting

0. **Verify you are NOT on the orchestrator node** — if the current
   node's role is `orchestrator` (check `infra/device_registry.json`)
   or `DISPLAY` env var is unset, delegate browser work to an executor
   node via SSH or `browser_evidence_collector.trigger_collection()`.
   Never run MCP Playwright directly on the orchestrator for
   verification evidence. See `.claude/rules/browser-verification.md`.
1. **Deploy the change** to its target environment
   - Docker services: `docker restart <container>`
   - Fly.io apps: deployment script or `flyctl deploy`
   - Vercel/Netlify: push triggers deploy
   - Local dev server: restart if needed
2. **Verify service health** — hit any endpoint, confirm
   non-timeout response (even 401/404 = alive)
3. **Identify the 4-layer targets**:
   - URL to load
   - DOM elements that prove the feature works
   - API endpoints the feature calls
   - Which server/container produces the logs

## Pass execution (repeat 3x)

### Layer 1: Browser (Playwright MCP)
```
browser_navigate → target URL
browser_wait_for → key element text or selector
browser_snapshot → capture full or targeted DOM state
```
Confirm the SPECIFIC elements the change affects.
Not "page loaded" — the exact component, text, data,
or interaction that the change introduced or fixed.

For interactive features, also:
```
browser_click → trigger the interaction
browser_snapshot → confirm the result
```

### Layer 2: Network (Chrome DevTools MCP)
```
list_network_requests(resourceTypes: ["fetch", "xhr"])
```
Confirm:
- API calls to relevant endpoints returned 200
- No 401 (auth failure), 403 (forbidden), 499 (timeout),
  5xx (server error)
- Response bodies are non-empty when data is expected
- No unexpected redirects

### Layer 3: Console (Chrome DevTools MCP)
```
list_console_messages(types: ["error"])
```
Confirm:
- Zero errors from application code
- Ignore known noise (third-party scripts, browser
  extensions, favicon 404s)
- Any NEW error related to the change = fail the pass

### Layer 4: Server Log Reconciliation (Bash)

Three sub-checks building the full picture. Every browser action must
have a matching server trace. Every server error must be browser-visible.

**4a. Standalone log scan**:
```bash
docker logs <container> --tail 100 --since 2m
```
- No unhandled tracebacks
- No auth/permission failures
- No connection timeouts

**4b. Network → Log cross-reference** (bidirectional):
For each API request captured in Layer 2:
1. Extract endpoint, method, status, timestamp
2. Search server logs for matching request within ±5s
3. Compare: network status code == server logged status code
4. Check for ERROR/WARNING between request start and response
5. Record: {endpoint, method, network_status, log_status, status_match,
   log_clean, latency_ms}

**4c. Orphan detection** (logs → network):
Scan server logs for ERROR/WARNING/Traceback lines that do NOT match
any browser network request. These are silent failures — the server
is breaking but the user sees nothing wrong.

**4d. Action → Trace reconciliation**:
For each browser action taken in Layer 1 (navigate, click, submit):
1. Identify the expected server-side effect (GET for navigate, POST for submit)
2. Verify the server processed it (log entry exists)
3. Verify the server result matches what the browser showed

Reconciliation score = (matched_actions / total_actions).
Must be ≥ 0.8 to pass. Below that = something is broken between
browser and server that the individual layers missed.

Pass verdicts:
- Network 200 + server 200 + clean log = PASS
- Network 200 + server error = SILENT FAILURE (blocks pass)
- Server error with no browser request = ORPHAN (blocks pass)
- Browser shows success + server never logged it = DATA INTEGRITY (blocks pass)
- Reconciliation < 80% = INCOMPLETE PICTURE (blocks pass)

Use `collect_log_reconciliation()` from `browser_evidence_collector.py`
for programmatic reconciliation, or perform the checks manually via
docker logs + grep.

## After 3 passes — generate proof

```
VERIFIED SOFTWARE TEST — <feature name>
Date: YYYY-MM-DD
App: <application name>
Commit: <hash>
Target: <URL / component / feature>

Pass 1: ✓ Browser ✓ Network ✓ Console ✓ Logs
Pass 2: ✓ Browser ✓ Network ✓ Console ✓ Logs
Pass 3: ✓ Browser ✓ Network ✓ Console ✓ Logs

Evidence:
- DOM: <what was confirmed in snapshot>
- API: <which endpoints, status codes>
- Console: <error count>
- Logs: <service name, clean / issues>

RESULT: CONFIRMED
```

This proof is required before claiming any UI/web change
is complete. No proof = not done.

## Common failure patterns

### Service not responding
```bash
# Check if process is running
ps aux | grep <process>
# Check if port is bound
ss -tlnp | grep <port>
# Check for connection pile-up
ss -tnp | grep <port> | grep -c CLOSE-WAIT
# If stale connections > 10 → restart
```

### Auth not ready on page load
Frontend fires API calls before auth token is available.
Fix: gate data fetching on auth-confirmed state, not
on component mount or initial render.

### 200 but empty data
Backend returns empty response — verify the data source
independently (database query, file check, upstream API).

### Works on refresh but not first load
Race condition between auth initialization and data fetch.
Or: localStorage cache masking a broken first-load path.
Clear storage and test cold load specifically.

### Works locally but not deployed
Environment delta — check env vars, CORS config, proxy
rules, SSL termination, CDN caching.

## Gotchas

- The orchestrator node has no display — Playwright MCP uses bundled
  headless Chromium there, not a real browser. Evidence from the
  orchestrator is invalid. Always delegate to an executor node.
- Node selection is role-based via device_registry.json, not
  hardcoded device names. Any executor-roled node with a display
  session is eligible for browser verification.
- Playwright MCP and Chrome DevTools MCP may run in
  separate browser contexts. Use Playwright for DOM
  state, DevTools for network/console inspection.
- localStorage/sessionStorage can mask broken APIs —
  "working" UI might show cached data. Verify network
  tab shows fresh responses, not cache hits.
- After service restart, wait for startup to complete
  before testing. Large apps need 10-30s.
- Third-party script errors (analytics, auth providers,
  ad scripts) are noise — only flag errors from YOUR code.
- If the app uses SSR, first-load DOM may differ from
  client-hydrated DOM. Test both states.
- Service workers can serve stale content. Hard refresh
  or disable service worker during testing.
- Log reconciliation catches silent failures that pass
  individual layers. A 200 response with a server-side
  traceback is a bug — reconciliation catches it.

## Integration with Engineering Execution Loop

When building through chat and Meta IDE via WorkPackets, this
protocol runs automatically during the `VALIDATING` phase.

### Automatic triggering
`BrowserVerificationGate` (`substrate/meta_ide/browser_verification_gate.py`)
determines if verification is required based on:
- `playwright_enabled=True` on any WorkPacket
- Artifact file paths matching UI patterns (`.tsx`, `.vue`,
  `components/`, `panels/`, `pages/`, etc.)
- `proof_requirements` including `"browser"` or `"ui"`

### How it works in the loop
1. Engineering session executes all task waves
2. Session transitions to `VALIDATING`
3. Artifact validation runs (existence, content hash)
4. Browser verification gate checks if UI evidence required
5. If required and evidence missing → session stays `VALIDATING`
6. Executing agent collects 4-layer evidence via MCP tools
7. Agent submits evidence via `submit_browser_evidence()`
8. Gate validates: 3 consecutive passes all green → `AWAITING_REVIEW`
9. If any pass fails → stays `VALIDATING`, agent loops

### Evidence format agents must produce
```json
{
  "passes": [
    {
      "pass_number": 1,
      "browser_check": {
        "elements_confirmed": ["sidebar loaded", "tree has 20 entries"],
        "snapshot_summary": "DOM snapshot shows file tree populated",
        "passed": true
      },
      "network_check": {
        "endpoints_checked": [
          {"url": "/api/bootstrap", "status": 200},
          {"url": "/api/browse", "status": 200}
        ],
        "error_count": 0,
        "passed": true
      },
      "console_check": {
        "app_error_count": 0,
        "app_errors": [],
        "ignored_errors": 2,
        "passed": true
      },
      "log_check": {
        "service_name": "os-operator",
        "log_lines_checked": 100,
        "tracebacks_found": 0,
        "auth_failures": 0,
        "timeouts": 0,
        "cross_references": [
          {"endpoint": "/api/bootstrap", "http_method": "GET",
           "network_status": 200, "log_entry_found": true,
           "log_status": 200, "log_clean": true, "status_match": true}
        ],
        "unmatched_network_requests": 0,
        "unmatched_log_errors": 0,
        "orphan_server_errors": [],
        "action_traces": [],
        "reconciliation_score": 1.0,
        "passed": true
      }
    }
  ]
}
```

### When working outside the engineering loop
For ad-hoc fixes, hotfixes, or work not routed through
WorkPackets, invoke this skill manually and follow the
protocol directly. The evidence format is the same —
structure your verification the same way so proof is
consistent whether automated or manual.

## What this replaces

- "I deployed it, should be working" (no verification)
- Single page load checks (fluke-prone)
- Screenshot-only validation (misses network/log layer)
- "Tests pass" without browser confirmation
  (tests verify code correctness, not feature correctness)
- Manual QA without structured proof
