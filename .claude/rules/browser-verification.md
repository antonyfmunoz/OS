# Browser Verification Law (NON-NEGOTIABLE)

Browser-based verification (Playwright, Chrome DevTools, any MCP browser tool)
NEVER runs on the orchestrator node. The orchestrator is headless — no display,
bundled Chromium only, no real browser.

All browser verification runs on executor-roled nodes with interactive desktop
sessions — discovered from `infra/device_registry.json` (nodes with
`role: executor` that have display capability).

## How to run browser verification from orchestrator

1. Use `browser_evidence_collector.trigger_collection(url, passes)` — it routes
   through the mesh daemon's HTTP relay (`POST :8095/dispatch`) to the executor
   node's ShellAdapter running in the interactive desktop session (Session 1).
   Chrome opens visibly on the executor's monitor.
2. The mesh daemon must be running on the executor (Task Scheduler ONLOGON).
   If offline, `trigger_collection()` falls back to SSH with a loud warning —
   but SSH runs in Session 0 (no display), so Chrome would be invisible.
3. NEVER call MCP Playwright tools directly from orchestrator for verification evidence.
4. NEVER use raw SSH for GUI automation — SSH creates Session 0 processes.

## How to detect you're on the orchestrator

If the node's role in device_registry.json is `orchestrator`, or `DISPLAY` env
var is unset, do not run browser verification locally. Delegate to an executor.

## What to use MCP Playwright for on orchestrator

ONLY for non-verification tasks: quick DOM checks during development, reading
page structure for planning. Never as verification evidence.

## Window flickering prevention

All subprocess calls on Windows executor nodes use `CREATE_NO_WINDOW`
creationflag (`subprocess_utils.no_window_kwargs()`) to prevent CMD/PowerShell
console windows from flashing visibly during automation in the interactive session.

## Credential injection

All browser verification credentials flow through 1Password `op run`.
See `.claude/rules/credential-injection.md` for the full protocol.
`trigger_collection()` wraps the remote command with `op run --env-file=<tpl>`
on the executor side — env vars don't transit SSH or mesh dispatch.

This law exists because: (1) a verification session ran Playwright MCP directly
on the orchestrator node (headless, bundled Chromium), producing false-positive
evidence; (2) SSH dispatch ran Chrome in Session 0 (invisible, non-interactive).
The mesh daemon in Session 1 is the only path that produces real, visible,
interactive Chrome sessions matching how software actually runs.
