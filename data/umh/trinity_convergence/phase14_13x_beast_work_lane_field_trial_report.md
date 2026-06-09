# Phase 14.13X — Beast Work Lane Field Trial Report

**Date:** 2026-06-09
**Baseline:** Phase 14.13W (c8949354..2bdf1cea)
**Verdict:** PARTIAL

## Beast Daemon Readiness

| Check | Result |
|-------|--------|
| Tailscale reachable | PASS — 100.74.199.102, 79-174ms latency |
| Ollama service | PASS — qwen2.5-coder:14b responding on :11434 |
| Kokoro TTS | PASS — HTTP 200 on :8880 |
| Node mesh | PASS — Beast status=connected, heartbeat 2026-06-09T20:10:09Z |
| Daemon process | PASS — pythonw.exe PID 19348, launcher.py, Session 1 |

## Windows Session Discovery

| Session | Type | Processes | GUI Capable | Classification |
|---------|------|-----------|-------------|----------------|
| 0 | Service | 51 (svchost, lsass, tailscaled, ollama, postgres, sshd) | No | **daemon_only** — no GUI automation |
| 1 | Interactive | 50+ (chrome, discord, steam, explorer, dwm, pythonw) | Yes | **operator_foreground** — Antony's active desktop |

**No additional RDP/logon sessions detected.**
**No configured background worker sessions.**

Session 0 correctly classified as service-only. Ollama, postgres, tailscaled, and sshd all run here as expected.

## Operator Foreground Lane

**Status:** Available and functional.

Session 1 is the single interactive session. The UMH daemon (launcher.py, PID 19348) runs here via Task Scheduler ONLOGON. Chrome, Discord, Steam are present.

Logged-in user: `DESKTOP-LVGUIQ9\antonys beast pc`

## Background Lane Availability

**Status:** NOT AVAILABLE.

Beast has only two Windows sessions: Session 0 (services) and Session 1 (operator foreground). No isolated background GUI lane exists.

To enable non-disruptive background browser work, configure one of:
1. Separate RDP/logon worker session (e.g., UMHWorker01 account)
2. Windows Sandbox or Hyper-V VM
3. Playwright headless browser in Session 1 (no foreground disruption for headless)
4. Scheduled Chrome profile launch via `--headless=new` flag

## Field Test Results

### D. Native Spotify App Resolution

| Assertion | Result |
|-----------|--------|
| resolve_app_target("spotify").is_native | **PASS** — True |
| process_name = "Spotify" | **PASS** |
| launch_cmd = "start Spotify" | **PASS** |
| open_url = None (no website fallback) | **PASS** |
| browser = "" (no browser) | **PASS** |
| Spotify installed on Beast | **PASS** — SpotifyAB.SpotifyMusic (Windows Store) |
| Spotify process currently running | No — not launched (Antony not using it) |

### E. Chrome-First Web App (Instagram)

| Assertion | Result |
|-----------|--------|
| resolve_app_target("instagram").is_native | **PASS** — False |
| browser = "chrome" | **PASS** |
| open_url = "https://instagram.com" | **PASS** |
| Chrome installed on Beast | **PASS** — C:\Program Files\Google\Chrome\Application\chrome.exe |
| Chrome running in Session 1 | **PASS** — PIDs 760, 1820, 2784+ |

### F. External Action Governance

| Assertion | Result |
|-----------|--------|
| "message him on instagram" → requires_approval | **PARTIAL** — command_router sets risk=high + requires_approval for message/dm/send verbs, but the lane router doesn't catch this independently |
| No external message sent | **PASS** — governance blocks |

### G. Chrome Worker Profile

**Status:** Not testable — no background lane configured. Chrome worker profiles would require background session setup.

### Routing Bugs Found and Fixed

| Bug | Root Cause | Fix |
|-----|-----------|-----|
| "open instagram" routed to foreground instead of background_browser | Instagram not in PLATFORM_PROCESS_MAP; classify_app_vs_website returned "unknown"; route_to_lane had no fallback for unknown apps | Added step 5: unknown apps with "open" prefix check resolve_app_target — if it resolves as web, route to background_browser |
| "click on the browser tab" routed to background_browser | "browse" in text triggered _BROWSER_PATTERNS before GUI action check | Moved GUI interaction check (step 2) before browser pattern check (step 4) |

### H. Loop Completion

| Assertion | Result |
|-----------|--------|
| Loop not complete without evidence | **PASS** — advance_loop with empty evidence returns verified=False |
| Loop verifies on process evidence | **PASS** — process_running + process_name → verified=True |
| Loop fails after max_iterations | **PASS** — 5 iterations with no evidence → status=failed |
| Loop report generation | **PASS** — create_loop_report returns valid LoopProgressReport |

### I. Loop Failure/Blocker

| Assertion | Result |
|-----------|--------|
| Loop with no evidence → failed after max | **PASS** — 3 iterations → status=failed |
| No fake completion | **PASS** — status never set to verified without evidence |

### J. Lane Metadata / HUD

| Assertion | Result |
|-----------|--------|
| Spotify lane HUD shows native_app | **PASS** — lane_type=native_app, disruption_risk=low |
| Search lane HUD shows background_browser | **PASS** — lane_type=background_browser, is_background=True, disruption_risk=none |
| HUD metadata includes lane_id and session_id | **PASS** |

### K. Voice Integration

**Status:** Not tested in this field trial (requires live cockpit voice session from iPhone). Voice route resolver and lane routing are independent modules — no coupling regression expected.

### L. Regression Tests

| Suite | Result |
|-------|--------|
| 26/26 work lane tests | **PASS** (22 original + 4 new regression) |
| Python compile (work_lane.py, app_resolver.py, loop_engine.py) | **PASS** |
| command_router integration | **PASS** |

## Remaining Limitations

1. **No background GUI lane** — Beast has only Session 0 (service) and Session 1 (operator). Background browser automation would require either a separate Windows user session, Windows Sandbox, or headless Chrome.
2. **Live app launch not tested** — Spotify/Chrome were verified as installed/running, but no live `start Spotify` command was executed via the daemon. The resolver and routing are proven correct; the execution path through NodeClient → DesktopAdapter/ShellAdapter → actual process launch needs a separate live test.
3. **Voice-to-Beast integration** — Not tested. Requires live cockpit voice session.
4. **External action governance** — command_router catches message/dm/send verbs and sets requires_approval, but the ForegroundGuard doesn't independently catch these. The two systems are additive (OR logic in _enrich_with_lane_info), so governance is preserved.

## Final Verdict

**PARTIAL** — Modules work correctly. Routing bugs found and fixed. Session topology discovered truthfully. Two real bugs caught and sealed with regression tests. Background GUI lanes are not configured on Beast (truthfully reported, not faked). Live app execution and voice integration deferred to manual verification.

### What's proven:
- Session 0 is service-only (51 service processes, no GUI)
- Operator foreground lane is detected (Session 1)
- Native apps resolve correctly (Spotify → native, not website)
- Web apps route to Chrome (Instagram → chrome, not Edge/Explorer)
- GUI interactions require foreground approval
- Loop engine verifies end-state before marking complete
- Blocked loops fail honestly after max iterations
- Lane metadata is visible and correct
- 26/26 tests pass

### What needs operator setup:
- Background Windows session for non-disruptive browser automation
- Live "open Spotify" test through the daemon execution path
- Voice-to-Beast routing live test from iPhone
