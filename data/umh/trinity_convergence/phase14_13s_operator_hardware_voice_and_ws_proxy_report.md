# Phase 14.13S — Operator Hardware Voice Trial + WebSocket Proxy Fix

**Date:** 2026-06-08
**Status:** PARTIAL — WebSocket proxy fixed and verified; hardware voice trial requires human operator

---

## Summary

Phase 14.13S fixes the main cockpit WebSocket connection that was failing due to a `Sec-WebSocket-Protocol` header mismatch between the browser client and the nginx reverse proxy. The fix is two-part: nginx now forwards the subprotocol header, and the server only echoes it when the client actually sent one. Hardware voice trials (Workcells A and B) require a human operator with a physical microphone.

---

## Workcell Results

### Workcell A — Real Hardware Voice Trial
**Status:** PENDING OPERATOR

Six test commands defined:
1. "DEX what is UMH" — conversation handler
2. "What am I looking at" — view context awareness
3. "Open Spotify" — Beast mesh relay
4. "Show Docker containers" — VPS catalog execution
5. "Start my workday" — multi-node startup sequence
6. "Message him on Instagram" — governance block (high-risk external)

All six commands verified working via text input in Phase 14.13Q/R. Real microphone capture requires a human operator with browser microphone access on HTTPS (universalmetaharness.tech) or localhost.

**Blocker:** No physical microphone available in headless/CI environment.

### Workcell B — TTS Cancel/Interruption Trial
**Status:** PENDING OPERATOR

Test scenario: Ask a long question, wait for DEX to speak, then interrupt with "Stop. Open Spotify." while TTS is playing.

Code is in place:
- `voice-controller.ts`: VAD-based interruption — detects voice during TTS → `cancelTts()` → state transitions to listening
- `voice-ws.ts`: `cancelTts()` clears audio queue, pauses current audio, sends `tts_cancel` to server
- Server-side TTS cancel handler in voice_server.py

**Blocker:** Requires real audio output (TTS) and real microphone input (interruption detection).

### Workcell C — WebSocket Proxy Fix
**Status:** SHIPPED

**Root cause:** nginx reverse proxy in `cockpit/nginx.conf.template` did not forward the `Sec-WebSocket-Protocol` header to the backend. The client sent `bearer.<token>` as a WebSocket subprotocol, nginx stripped it during proxy, but the server extracted the token from the `?token=` query param (injected by nginx) and echoed back `Sec-WebSocket-Protocol: bearer.<token>` in the response. The browser rejected per RFC 6455: "Response must not include 'Sec-WebSocket-Protocol' header if not present in request."

**Two-part fix:**

1. **nginx.conf.template** — Added `proxy_set_header Sec-WebSocket-Protocol $http_sec_websocket_protocol;` to forward the client's subprotocol header to the backend.

2. **transports/api/cockpit.py** — Extracted `_extract_ws_subprotocol()` to return the raw protocol string from the header (or None if absent). The `cockpit_ws()` handler now only echoes the subprotocol when the client actually sent it via the header, not when the token came from the query param fallback.

**Verification:**
- Cockpit deployed via `bash cockpit/deploy.sh` (deploy gate passed)
- Playwright browser test on `https://universalmetaharness.tech/`:
  - WS indicator dot: `rgb(0, 255, 136)` (green = connected)
  - Live pulse data streaming: CPU values changing in real-time (55% → 35% → 30%)
  - Zero `Sec-WebSocket-Protocol` errors in browser console
  - Status bar shows: Online, nodes 2/2, mesh:4, ws connected
- os-operator container restarted for server-side fix

### Workcell D — Seal Report
**Status:** THIS DOCUMENT

---

## Files Changed

| File | Change |
|---|---|
| `cockpit/nginx.conf.template` | Added `Sec-WebSocket-Protocol` header forwarding in WS proxy block |
| `transports/api/cockpit.py` | New `_extract_ws_subprotocol()` — only echo subprotocol when client sent it via header |

---

## Commits

| Hash | Message |
|---|---|
| `8be4fee2` | fix: WebSocket Sec-WebSocket-Protocol handshake — nginx forwarding + server echo guard |

---

## Verification Evidence

```
Status bar (live cockpit):
  Online | cpu 30% | ram 42% | disk 65% | nodes 2/2 | mesh:4 | ws ● (green)

WS indicator color: rgb(0, 255, 136) — connected
Console errors: 51 total — all 403s from unauthenticated API polling, zero WS errors

Deploy gate:
  ✓ nginx.conf.template matches main
  ✓ Dockerfile matches main
  ✓ start.sh matches main
  ✓ X-API-Key injection present
```

---

## Verdict Criteria Assessment

| Criterion | Status |
|---|---|
| Real mic capture + transcript routing | PENDING OPERATOR |
| DEX speaks back (TTS) | PENDING OPERATOR |
| Interruption works | PENDING OPERATOR |
| All nodes work by voice | PENDING OPERATOR (text-verified in 14.13Q/R) |
| Governance holds | VERIFIED (14.13Q: 34/34 classifications, 8/8 blocks) |
| WS connects cleanly | SHIPPED — green indicator, live data, zero protocol errors |

---

## Final Verdict

**PARTIAL** — WebSocket proxy fix shipped and verified in production. The `Sec-WebSocket-Protocol` mismatch that caused reconnect loops is permanently resolved. Hardware voice trials (Workcells A and B) require a human operator with a physical microphone on a browser with HTTPS access. All voice code is deployed and ready for operator testing.

The system is architecturally complete for voice operation. What remains is a human field trial — no code changes needed, only operator verification with real audio hardware.
