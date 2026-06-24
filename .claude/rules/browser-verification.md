# Browser Verification Law (NON-NEGOTIABLE)

Browser-based verification (Playwright, Chrome DevTools, any MCP browser tool)
NEVER runs on the orchestrator node. The orchestrator is headless — no display,
bundled Chromium only, no real browser.

All browser verification runs on executor-roled nodes with interactive desktop
sessions — discovered from `infra/device_registry.json` (nodes with
`role: executor` that have display capability).

## How to run browser verification from orchestrator

1. Use `browser_evidence_collector.trigger_collection(url, passes)` — it SSHs
   to the first available executor node via `_resolve_executor_ssh()`
2. Or SSH manually to an executor node's `tailscale_ip` from device_registry.json
3. NEVER call MCP Playwright tools directly from orchestrator for verification evidence

## How to detect you're on the orchestrator

If the node's role in device_registry.json is `orchestrator`, or `DISPLAY` env
var is unset, do not run browser verification locally. Delegate to an executor.

## What to use MCP Playwright for on orchestrator

ONLY for non-verification tasks: quick DOM checks during development, reading
page structure for planning. Never as verification evidence.

This law exists because a verification session ran Playwright MCP directly on
the orchestrator node (headless, bundled Chromium), producing false-positive
evidence that didn't match real browser behavior. The gate makes this
mechanically detectable and the rule makes it a session-level block.
