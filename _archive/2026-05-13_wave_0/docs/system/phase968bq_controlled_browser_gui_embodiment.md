# Phase 96.8BQ — Controlled Browser and GUI Embodiment

> Date: 2026-05-09
> Status: COMPLETE
> Tests: 91/91 pass
> Modules: 10 created

---

## What This Phase Built

Operationalized governed browser and GUI interaction through the canonical
substrate runtime. 10 modules that embody controlled browser navigation,
GUI inspection, and visible actuation — all under allowlist-based governance.

Same architectural pattern as 96.8BP (workstation embodiment):
contracts → modes → governed adapter → observability → continuity →
replay → orchestrator → engine.

New dimension: **navigation scope** — browser modes constrain not just
what actions can execute, but where navigation can go.

---

## Architecture

```
BrowserGUIEmbodimentEngine (apex)
  ├── BrowserExecutionOrchestrator (pipeline)
  │     ├── GovernedBrowserAdapter (allowlist browser)
  │     ├── VisibleGUIAdapter (governed GUI)
  │     ├── BrowserObservabilityPipeline (telemetry)
  │     └── BrowserContinuityBridge (lineage)
  ├── BrowserReplayValidator (determinism)
  └── BrowserOperationalModes (4 modes)
```

---

## Modules

| Module | File | Purpose |
|--------|------|---------|
| Browser/GUI Contracts | `browser_gui_contracts_v1.py` | 8 contracts: BrowserState, Session, CapabilityReq, ExecRequest, ExecResult, GUIState, VisibleActuationEvent, OperationalSnapshot |
| Browser Operational Modes | `browser_operational_modes_v1.py` | 4 modes with navigation scope, action allowlists, URL classification |
| Governed Browser Adapter | `governed_browser_adapter_v1.py` | 5-rule evaluation, 33+ blocked URL patterns, 9 blocked domains |
| Visible GUI Adapter | `visible_gui_adapter_v1.py` | 14 blocked GUI actions, display/window inspection, screenshot |
| Browser Observability | `browser_observability_pipeline_v1.py` | Execution records, denials, metrics, actuation log (4 JSONL files) |
| Browser Continuity Bridge | `browser_continuity_bridge_v1.py` | Session lineage, execution tracking, mode transitions, state bridging |
| Browser Replay Validator | `browser_replay_validator_v1.py` | Decision path replay, 4 determinism checks per record |
| Browser Execution Orchestrator | `browser_execution_orchestrator_v1.py` | Pipeline: governance → adapter routing → observability → continuity |
| Browser/GUI Embodiment Engine | `browser_gui_embodiment_engine_v1.py` | Central orchestrator, 6 commands, browser+GUI state |
| Test Suite | `test_controlled_browser_gui_embodiment_v1.py` | 91 tests across 9 classes |

All files in `core/workstation/` except test suite in `tests/`.

---

## Contracts (browser_gui_contracts_v1.py)

### Enums

| Enum | Values |
|------|--------|
| BrowserActionType | inspect_tabs, inspect_url, inspect_dom, navigate, scroll, screenshot, document_inspect, window_inspect, window_focus, ui_state_inspect |
| BrowserActionVerdict | approved, denied, escalated |
| BrowserExecutionOutcome | success, denied, failed, timeout, not_available |
| BrowserOperationalMode | inspection, research, internal_navigation, restricted_execution |
| NavigationScope | none, local_only, internal_only, approved_external |
| GUIWindowState | normal, maximized, minimized, fullscreen, hidden |

### Data Shapes

- **BrowserState** — browser_type, is_running, active_tabs, current_url, pid, operational_mode, navigation_scope
- **BrowserSession** — tab_index, url, title, is_active, domain; deterministic ID from tab_index:url
- **BrowserCapabilityRequest** — action_type, target_url, target_selector, operational_mode
- **BrowserExecutionRequest** — full request with action_type, target_url, selector, scroll, screenshot, adapter, risk, governance, timeout
- **BrowserExecutionResult** — outcome, url_before/after, dom_summary, screenshot_path/hash, result_data, succeeded property
- **GUIState** — desktop_session_active, display_available, active_window_title/pid, window_state, visible_windows
- **VisibleActuationEvent** — action_type, target, url, governance_verdict/rules, outcome, visibility_confirmed, screenshot_path
- **BrowserOperationalSnapshot** — composed snapshot of browser_state + gui_state + sessions + events + counters

---

## Browser Operational Modes (browser_operational_modes_v1.py)

| Mode | Actions | Navigation Scope | Screenshot Required | Timeout |
|------|---------|------------------|--------------------:|---------|
| inspection | inspect_tabs, inspect_url, inspect_dom, window_inspect, ui_state_inspect, screenshot | none | No | 10s |
| research | inspection + document_inspect | approved_external | No | 20s |
| internal_navigation | research + navigate, scroll, window_focus | internal_only | Yes | 30s |
| restricted_execution | navigation actions | internal_only | Yes | 60s |

### Navigation Scope Rules

| Scope | Allowed URLs |
|-------|--------------|
| none | No navigation |
| local_only | localhost, 127.0.0.1, 0.0.0.0, file:// |
| internal_only | local + 100.x (Tailscale), 10.x, 192.168.x |
| approved_external | internal + github.com, docs.python.org, developer.mozilla.org, stackoverflow.com, pypi.org, npmjs.com |

---

## Governance Rules

### Structural URL Blocklist (33+ patterns, NEVER navigable)

```
/login, /signin, /sign-in, /sign_in, /auth, /oauth, /sso, /callback,
/authorize, /token, /checkout, /payment, /pay, /billing, /purchase,
/subscribe, /settings, /account, /profile/edit, /password,
/reset-password, /change-password, /delete-account, /deactivate,
/compose, /new-post, /create-post, /send-message, /upload, /download,
/export, /admin, /dashboard/admin
```

### Structural Domain Blocklist (9 domains, NEVER navigable)

```
accounts.google.com, login.microsoftonline.com, auth0.com,
login.live.com, appleid.apple.com, paypal.com, stripe.com,
venmo.com, cashapp.com
```

### Blocked GUI Actions (14 actions, NEVER executable)

```
close_window, kill_process, resize_window, move_window, minimize_all,
clipboard_write, clipboard_read, keystroke_inject, mouse_click,
mouse_move, drag_drop, desktop_switch, logout, lock_screen
```

### 5-Rule Evaluation Order (GovernedBrowserAdapter)

1. **BLOCKED_DOMAIN** — structural domain check
2. **BLOCKED_URL_PATTERN** — structural URL path check
3. **MODE_ACTION_DENIED** — action type not in mode allowlist
4. **NAVIGATION_SCOPE_DENIED** — URL outside navigation scope (navigate only)
5. **BROWSER_ALLOWLIST_APPROVED** — all checks passed

Double governance for NAVIGATE: both the action type AND the URL must pass.

---

## Test Results

```
91 passed in 0.73s
```

| Test Class | Count | What It Proves |
|------------|------:|----------------|
| TestContracts | 12 | Deterministic IDs, content hashes, serialization, enum coverage |
| TestBrowserModes | 14 | Mode action allowlists, navigation scope, URL classification |
| TestGovernedBrowserAdapter | 20 | URL blocking, domain blocking, mode gating, scope enforcement, risk classification |
| TestVisibleGUIAdapter | 7 | Blocked actions, mode enforcement, GUI state capture |
| TestBrowserObservability | 4 | Record persistence, denial tracking, actuation logging, stats |
| TestBrowserContinuityBridge | 8 | Session lifecycle, execution bridging, mode transitions, snapshots |
| TestBrowserReplayValidator | 6 | Governance verdict replay, risk replay, routing replay, session replay |
| TestBrowserExecutionOrchestrator | 5 | Denied execution, approved execution, GUI routing, stats |
| TestBrowserGUIEmbodimentEngine | 15 | Initialization, command dispatch, mode setting, browser+GUI state |

---

## Constraints Met

| Constraint | Status |
|------------|--------|
| No autonomous browsing agents | YES — all actions require explicit request |
| No unrestricted browser automation | YES — allowlist-only execution |
| No hidden navigation | YES — all navigation produces VisibleActuationEvent |
| No external account mutation | YES — login/auth/settings URLs structurally blocked |
| No governance bypass | YES — 5-rule evaluation, no override path |
| No weakened replay determinism | YES — 4 replay checks per record, session-level proof |
| No parallel GUI execution paths | YES — single-adapter routing |
| No uncontrolled CU recursion | YES — no recursive loops in orchestrator |

---

## Persistence Layout

```
data/runtime/browser_observability/
  browser_records.jsonl        — all execution records
  browser_denials.jsonl        — denied executions
  browser_metrics.jsonl        — action/outcome/latency metrics
  visible_actuation_log.jsonl  — visible actuation events

data/runtime/browser_continuity/
  browser_continuity_events.jsonl     — session lifecycle events
  browser_execution_lineage.jsonl     — execution tracking
  browser_continuity_snapshot.json    — latest state snapshot

data/runtime/browser_replay_proofs/
  browser_replay_proof_*.json  — determinism proof files
```

---

## Relationship to 96.8BP

This phase mirrors 96.8BP (workstation embodiment) exactly in architecture:

| 96.8BP (Workstation) | 96.8BQ (Browser/GUI) |
|---------------------|----------------------|
| WorkstationContracts | BrowserGUIContracts |
| OperationalModes (4 shell modes) | BrowserOperationalModes (4 browser modes) |
| GovernedShellAdapter | GovernedBrowserAdapter + VisibleGUIAdapter |
| TmuxOperationalAdapter | (navigation scope replaces tmux dimension) |
| WorkstationStateRegistry | (browser/GUI state in engine) |
| WorkstationObservabilityPipeline | BrowserObservabilityPipeline |
| WorkstationContinuityBridge | BrowserContinuityBridge |
| WorkstationReplayValidator | BrowserReplayValidator |
| WorkstationExecutionOrchestrator | BrowserExecutionOrchestrator |
| WorkstationEmbodimentEngine | BrowserGUIEmbodimentEngine |

New dimensions in 96.8BQ not present in 96.8BP:
- **NavigationScope** — where the browser can go (none/local/internal/approved_external)
- **Double governance** — action type AND URL destination both evaluated
- **Structural domain blocklist** — payment, auth, SSO providers blocked at domain level
- **Visible actuation events** — every action produces auditable actuation record
- **GUI adapter split** — separate adapter for window management vs. browser navigation
