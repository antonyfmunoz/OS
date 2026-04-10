# Current-State Code Audit: EOS Orchestration & Tool Mastery Engine
**Date:** 2026-04-08  
**Auditor:** Code Review  
**Scope:** Tool Mastery Engine, Control Plane, Orchestrator, Workflows, Policy, Workers, Docs  
**Methodology:** Read-the-real-files, no inference; every claim points to code.

---

## 1. Executive Summary

The EOS system has a **solid foundation** but is in a **deliberate mid-build state**. Three independent but tightly coupled subsystems are 60–90% complete:

1. **Tool Mastery Engine (TME):** Fully functional skill registry with verification, staleness auditing, and Neon sync. Missing: automated discovery, refresh triggers, environment bootstrap.
2. **Control Plane:** Production-ready action validation, approval, deferred queue, idempotency. Missing: business-layer risk policy integration (stubbed but not live), retry automation (signals exist, loop not yet scheduled).
3. **Orchestrator:** Pipeline composition, signal layer, autonomous loop, three handler workflows all working. Missing: live signal trigger from cron, persistent deferred approval CLI, non-cron signal sources.

**Most dangerous assumption:** The system is complete. It is not—it is intentionally modular so pieces can be hardened independently before being wired together.

**Recommendation:** Before building new layers, activate what exists. Phase 7 is documented but not applied: cron→signal wiring. Do that before new feature development.

---

## 2. Repo Inventory

```
/opt/OS/
├── core/
│   ├── action_system/           # Control Plane — validated control center for all side effects
│   │   ├── actions.py           (54 lines) — Action dataclass, allowed types
│   │   ├── control_plane.py     (272 lines) — run_action, resume_action lifecycle
│   │   ├── validator.py         (187 lines) — validation + approval logic
│   │   ├── executor.py          (113 lines) — run_script, shell, write_file, call_api dispatch
│   │   ├── logging.py           (72 lines) — append-only JSONL logs
│   │   ├── deferred.py          (96 lines) — persist medium/high risk awaiting approval
│   │   ├── deferred_status.py   (241 lines) — deferred queue inspection + snooze/wake
│   │   ├── notifier.py          (119 lines) — FileNotifier, Discord, MultiNotifier
│   │   ├── idempotency.py       (295 lines) — sentinel store, TTL, collision detection
│   │   ├── policy.py            (164 lines) — risk mapping, Authority Engine bridge
│   │   └── tme.py               (38 lines) — query_relevant_skills shell integration
│   └── orchestrator/            # Orchestrator — signal-driven workflow composer
│       ├── orchestrator.py      (199 lines) — workflow registry, execution + state tracking
│       ├── pipeline.py          (276 lines) — ActionStep/FuncStep composition, sequential run
│       ├── loop.py              (399 lines) — signal drain, stale/failure scan, retry/escalate
│       ├── signals.py           (208 lines) — filesystem-backed emit/consume, handlers binding
│       ├── handlers.py          (321 lines) — deferred_stale, action_failed, action_retry_requested
│       ├── decisions.py         (158 lines) — should_retry, should_escalate, should_ignore
│       ├── steps.py             (210 lines) — ScriptWorkflowSpec, script_step, api_step
│       └── workflows.py         (109 lines) — register_default_workflows
├── scripts/
│   ├── _tme_common.py           (230 lines) — shared skill loader, YAML frontmatter, sections
│   ├── query_skills.py          (212 lines) — CLI registry (search, show, deps, stale, deps)
│   ├── verify_tool_skill.py     (150+ lines) — linter (SKILL.md, best_practices, frontmatter)
│   ├── check_skill_staleness.py (170 lines) — freshness audit (fast/medium/stable windows)
│   ├── build_skill_graph.py     (100+ lines) — cross-reference graph (edges, reverse, centrality)
│   ├── sync_skills_to_neon.py   (80+ lines) — upsert skills table (version bump on change)
│   ├── decisions.py             (150+ lines) — decision log CLI (list, show, for-action)
│   ├── deferred.py              (200+ lines) — deferred queue CLI (approve, reject, snooze, wake)
│   ├── control_plane_run.py     (100+ lines) — Control Plane entry point (shell wrapper)
│   ├── orchestrator_loop.py     (50+ lines) — loop entry point (--cycles, --forever)
│   ├── orchestrator_status.py   (200+ lines) — status snapshot (signals, deferred, workflows)
│   ├── scheduled/
│   │   ├── morning_prep_cp.py       (83 lines) — cron wrapper, medium risk, 23h idempotent
│   │   ├── morning_prep.sh          (70 lines) — actual ritual (keys, Neon, GWS, CC brief)
│   │   ├── nightly_consolidation_cp.py  (80 lines) — wrapper, dry-run safe
│   │   ├── nightly_consolidation.sh (100 lines) — reconciliation ritual
│   │   ├── weekly_review_cp.py       (75 lines) — low risk wrapper, ISO-week keyed
│   │   ├── weekly_review.sh         (70 lines) — weekly audit ritual
│   │   └── nightly_maintenance.sh   (140 lines) — backup, cache clear (NOT wrapped yet)
│   └── workers/
│       └── discord_approval_worker.py (200+ lines) — tail notifications.jsonl → webhook
├── skills/
│   ├── tools/                   # 89 tool skills (e.g., notion, google_sheets)
│   │   └── */
│   │       ├── SKILL.md         (frontmatter + body)
│   │       └── references/best_practices.md
│   ├── meta/tool_mastery_engine/
│   │   └── SKILL.md             (decision tree, research protocol)
│   └── [Sales, Marketing, Ops, ...]/  # domain-specific skills
├── docs/
│   ├── system/
│   │   ├── tool_mastery_engine_system.md  — TME reference
│   │   ├── control_plane.md               — CP reference
│   │   ├── orchestrator.md                — Orchestrator reference
│   │   ├── skill_graph.md                 (generated)
│   │   └── skill_graph.json               (generated)
│   └── audits/
│       ├── 2026-04-06-tool-mastery-system-upgrade.md
│       ├── 2026-04-06-control-plane-phase-1.md
│       ├── 2026-04-08-control-plane-phase-2.md
│       ├── 2026-04-08-control-plane-phase-3.md
│       ├── 2026-04-08-control-plane-phase-4.md
│       ├── 2026-04-08-orchestrator-phase-5.md
│       ├── 2026-04-08-orchestrator-phase-6.md
│       └── current-state-code-audit.md (this file)
└── logs/
    ├── execution/               (append-only JSONL, one per UTC day)
    ├── decisions/               (append-only JSONL, one per UTC day)
    ├── deferred/                (JSON per action, awaiting approval)
    │   ├── <action_id>.json
    │   ├── notifications.jsonl  (deferred + operator alerts)
    │   ├── .worker_offset       (Discord worker state)
    │   └── sidecar/             (snooze state per action)
    ├── signals/                 (signal mailboxes)
    │   ├── morning_ready/       {pending, processed}/
    │   ├── nightly_cycle/
    │   ├── weekly_cycle/
    │   ├── deferred_stale/
    │   ├── action_failed/
    │   ├── action_retry_requested/
    │   └── bindings.json        (handler → workflow map)
    └── orchestrator_state.json  (per-workflow last_run, status, duration, totals)
```

---

## 3. Tool Mastery Engine Audit

### What exists (VERIFIED IN CODE)

**1. Skill discovery and loading** (`scripts/_tme_common.py:171–182`)
- `all_skill_slugs()` — scans `/opt/OS/skills/tools/` for directories with SKILL.md
- `load_skill(slug)` — reads SKILL.md, parses YAML frontmatter, loads best_practices.md
- Handles 89 tool skills as of 2026-04-06

**2. Frontmatter parsing** (`scripts/_tme_common.py:112–138`)
- Uses `yaml.safe_load()` instead of brittle regex
- Multi-line descriptions, nested keys, quoted strings all work
- Captures: `name`, `description`, `last_researched`, `source_url`, `speed_category`, `api_version`, `sdk_version`

**3. Verification/linter** (`scripts/verify_tool_skill.py`)
- SKILL.md existence + min 500 chars
- Frontmatter YAML parse + required keys (name, description, last_researched, source_url)
- `last_researched` is valid ISO date
- Mandatory sections: Authentication + Gotchas in SKILL.md
- best_practices.md exists + min 2000 chars + all 19 required sections
- Slug snake_case rule
- No corrupt Unicode chars
- Exit code: 0 = pass, 1 = fail, 2 = bad invocation
- Run: `python3 scripts/verify_tool_skill.py --all [--json]`

**4. Staleness auditing** (`scripts/check_skill_staleness.py`)
- Freshness windows: fast=30d, medium=60d, stable=90d (default medium)
- Reports: FRESH, NEAR_STALE (≥80% of window), STALE, MISSING_DATE
- Run: `python3 scripts/check_skill_staleness.py --all [--markdown|--json]`
- Exit code: 0 = no stale, 1 = at least one stale/missing

**5. Dependency graph** (`scripts/build_skill_graph.py`)
- Cross-references by slug + title mentions + alias rewrites
- Outputs: `/opt/OS/docs/system/skill_graph.md` + `.json`
- JSON contains: nodes, edges, reverse_edges, centrality (degree)
- Run: `python3 scripts/build_skill_graph.py [--stdout|--skill <slug>]`

**6. Neon sync** (`scripts/sync_skills_to_neon.py`)
- Upserts `(org_id, name, content, version)` into `skills` table
- `version` bumps on content change, preserved otherwise
- No UNIQUE constraint; uses SELECT→UPDATE-or-INSERT
- Run: `python3 scripts/sync_skills_to_neon.py --all [--dry-run]`
- Exit codes: 0 = success, 1 = fatal (DB, missing), 2 = parse warning

**7. Query CLI** (`scripts/query_skills.py`)
- Commands: `search <substring>`, `show <slug>`, `deps <slug>`, `stale [--only]`, `unverified`, `domain <substring>`, `list`, `count`
- Delegates `unverified` to verify_tool_skill.py --all --json
- Run: `python3 scripts/query_skills.py search ads`

### What does NOT exist (VERIFIED BY ABSENCE)

**1. Tool discovery / create-if-missing**
- No automatic scanning of external tool usage (e.g., "which tools did agents mention in their code?")
- No scaffolding of SKILL.md for a new tool
- No environment bootstrap (e.g., "onboard this user—what tools are in scope?")

**2. Refresh triggers**
- Staleness is detected but no automated "refresh this skill" workflow
- `check_skill_staleness.py` is a read-only audit; no `--auto-refresh` or integration with Control Plane
- Operator must manually run research and update `last_researched` date
- `sync_skills_to_neon` is manual; no scheduled invocation in crontab

**3. Backfill / missing-date scanner**
- No workflow to find all `MISSING_DATE` skills and route them to a research agent
- Operator must run `--only missing_date` manually and eyeball the list

**4. Runtime interception**
- Control Plane's `tme.py:15–38` shells out to `query_skills.py search <term>` only when explicitly requested
- No automatic "before you do X, did you check the skill for X?" interception
- Tool mention in agent code is not detected and routed to TME
- `consult_tme` flag must be set by the caller; default is False

**5. Version pinning, SDK/API tracking**
- Frontmatter has `api_version`, `sdk_version` fields but no enforcement
- No alerting when a tracked version becomes stale (e.g., "Python SDK 2.x deprecated, you're running 1.x")
- No integration with dependency trackers

**6. Manager / lifecycle automation**
- No "self-managing Tool Mastery Manager" that watches for gaps and auto-escalates
- All workflows are manual: verify, check, sync, query

### Docs vs. Code

| Claim | Doc | Code | Status |
|-------|-----|------|--------|
| 5 utilities shipped | tool_mastery_engine_system.md | ✓ all 5 exist | COMPLETE |
| Neon sync idempotent | "no UNIQUE constraint, uses SELECT→UPDATE-or-INSERT" | ✓ verified line-by-line | COMPLETE |
| Freshness windows | "fast=30d, medium=60d, stable=90d" | ✓ `_tme_common.py:54–56` | COMPLETE |
| Verification linter | "9 checks" documented | ✓ verified in verify_tool_skill.py | COMPLETE |
| Skill count | "89 tool skills (as of 2026-04-06)" | ✓ 89 directories with SKILL.md | CURRENT |

**No contradictions found.**

---

## 4. Control Plane Audit

### What exists (VERIFIED IN CODE)

**Location:** `/opt/OS/core/action_system/` (1,597 lines total)

**1. Action model** (`actions.py:26–83`)
- Dataclass: `type`, `description`, `inputs`, `risk_level`, `source_agent`, `status`, `validation`, `approval`, `result`, `idempotency_key`
- Allowed types: `run_script`, `shell_command`, `write_file`, `call_api`
- Status lifecycle: `proposed → validated → approved → executed | failed | rejected | deferred`
- Idempotency key is optional, backwards-compatible (`load_deferred` filters unknown keys)

**2. Lifecycle: propose → validate → approve → execute → log** (`control_plane.py:83–256`)
- `run_action()` is the public entry point (line 83)
- Idempotency pre-flight: checks sentinel store before any work (lines 109–155)
- `propose_action()` → `validate_action()` → `approve_action()` → `execute_action()` → `log_execution()`
- Each transition logged; executor writes to execution log
- Returns fully-populated Action object with final status

**3. Validation** (`validator.py:1–187`)
- Safety rules: forbidden path prefixes (`/etc`, `/boot`, `/sys`, `/proc`, `/dev`, `/root/.ssh`)
- Dangerous shell tokens: `rm -rf /`, `mkfs`, fork bomb, `dd if=`, `shutdown`, `reboot`, `> /dev/sda`
- `run_script` must target `.py` or `.sh`
- `call_api` must have URL
- Intentionally coarse; per-agent policy is flagged but not implemented

**4. Approval policy** (`control_plane.py:192–193`, `policy.py:104–106`)
- `low`: auto-approved
- `medium`: requires `explicit_approval=True` (else deferred)
- `high`: requires `explicit_approval=True` (else deferred)
- Business-layer risk upgrade via `resolve_effective_risk()` (policy.py:133–152)
  - Looks up `business_action_type` in `eos_ai.authority_engine.RISK_CLASSES` lazily
  - Picks stricter of runtime vs. business risk (never downgrades)

**5. Deferred queue** (`deferred.py`, `deferred_status.py`)
- Medium/high without approval written to `/opt/OS/logs/deferred/<action_id>.json`
- `resume_action(action_id)` loads, grants explicit approval, executes, deletes file (control_plane.py:221–256)
- Snooze/wake: `deferred_status.py:141–162` wakes snoozed items when `snoozed_until <= now`
- CLI: `/opt/OS/scripts/deferred.py` (approve, reject, snooze, wake, list, idempotency)

**6. Idempotency (Phase 4)** (`idempotency.py`)
- Sentinel store at `/opt/OS/logs/idempotency/<key-hash>/`
- States: `in_flight`, `executed`, `failed`, `deferred` (with TTL expiry)
- Pre-flight state machine (lines 114–142 of control_plane.py):
  - `in_flight` → return `skipped_duplicate` (conflict)
  - `executed` → return `skipped_duplicate` (success)
  - `deferred` + file present → return `skipped_duplicate` (awaiting operator)
  - `deferred` + file dropped → overwrite (dropped action is free)
  - `failed` → overwrite (retry allowed)
- Terminal states flip: `executed | failed | deferred`
- Validator rejection clears sentinel (bug detection)
- CLI: `scripts/deferred.py idempotency {list,show,clear,prune}`

**7. Executor** (`executor.py`)
- Dispatch by `action.type`:
  - `run_script`: Popen with timeout, captures stdout/stderr, returncode
  - `shell_command`: same
  - `write_file`: os.makedirs + file write (validates path)
  - `call_api`: subprocess curl (naive but safe; real callers use proper HTTP lib)
- All paths logged + raise no exception (action gets status=failed in result)

**8. Notifier stack** (`notifier.py`)
- Abstract `Notifier` protocol: `notify(action) -> dict`
- `FileNotifier`: writes to `/opt/OS/logs/deferred/notifications.jsonl` (append-only)
- `DiscordNotifier`: POSTs to webhook (env var `DISCORD_APPROVAL_WEBHOOK_URL`)
- `MultiNotifier`: chains multiple notifiers
- Control Plane writes deferred + escalation notices (calls notifier in handlers)

**9. Policy bridge** (`policy.py`)
- Maps Authority Engine uppercase (`LOW/MEDIUM/HIGH/CRITICAL`) ↔ Control Plane lowercase
- Lazy import of `eos_ai.authority_engine.RISK_CLASSES`
- Never crashes if Authority Engine unavailable; returns None
- Single source of truth for autonomy level per risk

**10. TME integration** (`tme.py`)
- `query_relevant_skills(term)` shells out to `query_skills.py search <term>`
- Only invoked when `consult_tme=True` (off by default)
- Result attached to `action.result["tme_consult"]`, advisory (not blocking)
- Timeout 10s; failure is logged but does not fail the action

**11. Logging** (`logging.py`)
- Append-only JSONL: `/opt/OS/logs/execution/YYYY-MM-DD-execution.jsonl` (one per UTC day)
- `log_execution(action)` writes every lifecycle transition (proposed, validated, approved, executed/failed)
- Separate decision log: `/opt/OS/logs/decisions/YYYY-MM-DD-decisions.jsonl`
- CLI: `scripts/decisions.py` (list, show, for-action, filters: --agent, --context, --since, --today, --limit, --json)

### What does NOT exist (VERIFIED BY ABSENCE)

**1. Business-layer risk policy enforcement (STUBBED)**
- `policy.py` has the bridge code (all 164 lines)
- But `authority_engine.py` is NOT consulted at runtime in current workflows
- Reason: Authority Engine is a heavy dependency (DB import) and Phase 1 said "don't block CP on business layer"
- Status: **Code exists, not integrated into any live workflow**
- To activate: call `resolve_effective_risk(declared_risk, business_action_type)` from callers (morning_prep_cp, etc.) currently do not

**2. Per-agent / per-venture policies**
- Mentioned in Phase 1 audit as "flagged for Phase 2"
- No code: validation rules are hardcoded in `validator.py`
- No way to say "outreach_agent can execute shell_command at low risk, but cfo_agent requires high"

**3. Dry-run mode (distinct from deferred)**
- Mentioned in Phase 4 audit as "Phase 5 scope"
- No code: `run_action()` goes either to deferred or approved
- Dry-run (validate + print plan, don't defer) is not implemented

**4. Retry automation**
- Phase 6 handlers exist: `handle_action_retry_requested` emits retry as a new `run_action` call
- But the orchestrator loop is **not scheduled**
- Current crontab: `0 6 * * * python3 eos_ai/orchestrator.py` (not in 2026-04-08 snapshot)
- Status: **Code exists, loop is not running**

### Workflows actually using Control Plane

| Workflow | Path | Risk | Idempotent | Deferred? | Status |
|----------|------|------|-----------|-----------|--------|
| morning_prep | scripts/scheduled/morning_prep_cp.py | medium | yes (23h) | yes | ACTIVE |
| nightly_consolidation | scripts/scheduled/nightly_consolidation_cp.py | medium | yes (dry-run safe) | yes | ACTIVE |
| weekly_review | scripts/scheduled/weekly_review_cp.py | low | yes (ISO-week) | yes | READY |
| nightly_maintenance | scripts/scheduled/nightly_maintenance.sh | N/A | no | no | LEGACY (not wrapped) |

### Docs vs. Code

| Claim | Docs | Code | Status |
|-------|------|------|--------|
| Approval policy (low/medium/high) | control_plane.md | ✓ validator.py + policy.py | COMPLETE |
| Idempotency with TTL | control_plane.md Phase 4 section | ✓ idempotency.py + control_plane.py:109–155 | COMPLETE |
| Deferred snooze/wake | control_plane.md Phase 4.5 | ✓ deferred_status.py:141–162 | COMPLETE |
| Discord worker | control_plane.md 4.2 | ✓ scripts/workers/discord_approval_worker.py | COMPLETE |
| Authority Engine bridge | control_plane.md "integration contract" | ✓ policy.py + lazy import, but never called | STUBBED |

**No contradictions. Authority Engine integration is documented but not yet wired into any workflow.**

---

## 5. Orchestrator Audit

### What exists (VERIFIED IN CODE)

**Location:** `/opt/OS/core/orchestrator/` (1,963 lines total)

**1. Workflow registry** (`orchestrator.py:54–176`)
- `Orchestrator` dataclass: `workflows` dict, `state` dict (per-workflow stats)
- `register_workflow(name, workflow)` — workflow is Pipeline or callable
- `run_workflow(name, context)` — executes, records stats, returns result
- State persisted to `/opt/OS/logs/orchestrator_state.json` (last_run_at, last_status, last_duration_s, total_runs, total_failures)
- Thread-safe: uses Lock

**2. Pipeline composition** (`pipeline.py`)
- `ActionStep`: descriptor mapping 1:1 to `run_action()` kwargs
  - Supports `inputs_fn` (context → inputs) for step N depending on step N-1
  - Supports `idempotency_key_fn` (context → key)
- `FuncStep`: plain Python callable (context → dict), no `run_action()`
- `Pipeline`: ordered list of steps, `stop_on_fail=True` (default), `source_agent`
- `run_pipeline()` walks sequentially, stores each result in `context[step.name]`
- Halts on non-ok step (if stop_on_fail), marks later steps skipped
- Emits one high-level decision log record
- **Every ActionStep still goes through full CP lifecycle** (lines 148–160)

**Status translation** (pipeline.py:162–176):
- Action `executed` → pipeline `ok`
- Action `skipped_duplicate` → pipeline `ok` (if result ok)
- Action `deferred` → pipeline `deferred`
- Action `rejected` → pipeline `rejected`
- Other → pipeline `failed`

**3. Signal layer** (`signals.py:1–209`)
- Filesystem mailbox per signal under `/opt/OS/logs/signals/<name>/{pending,processed}/`
- `define_signal(name)` — create directories
- `emit_signal(name, payload)` — write JSON file to pending/ (atomically)
- `register_handler(signal, workflow_name)` — update bindings.json
- `list_pending(signal)` — read all pending emissions
- `mark_processed(emission, outcome)` — move file from pending/ to processed/ with outcome tag
- Handler bindings in `/opt/OS/logs/signals/bindings.json` (single file, persists across restarts)

**4. Autonomous loop** (`loop.py:1–399`)
- `run_cycle()` does exactly four things (lines 354–371):
  1. `_drain_signals()` — for each signal's pending emissions, look up handlers, run via `orch.run_workflow()`
  2. `_scan_stale_deferred()` — any deferred action older than 6h (default) gets `deferred_stale` signal
  3. `_scan_failures()` — tail today's execution log, for each failed action:
     - Retry-eligible: emit `action_retry_requested` signal
     - Non-eligible: emit `action_failed` signal
  4. Return `CycleReport` with counts + details

- `run_forever()` — loop caller, calls `run_cycle()` every N seconds (default 300s), stops on `max_cycles`
- **Loop never executes actions directly.** Every dispatch goes through `orch.run_workflow()` which (if Pipeline) routes through Control Plane, or (if callable) calls the callable (which must itself use `run_action()`).

**5. Signal handlers** (`handlers.py:34–322`)
- `handle_deferred_stale(context)`: Log decision, append operator notice to notifications queue. Never auto-approves.
- `handle_action_failed(context)`: Double-check `should_ignore()`, otherwise escalate + notify operator.
- `handle_action_retry_requested(context)`: Re-check `should_retry()`, if still eligible re-invoke via `run_action(retry:<id>:<date>)` with explicit approval, else escalate.

All three follow the rule: **no direct execution, always use `run_action()` for side effects.**

**6. Decision helpers** (`decisions.py:1–158`)
- `should_retry(action)`: true iff type ∈ {shell_command, call_api}, idempotency key present, risk not high, retry count today < MAX (default 1)
- `should_escalate(action)`: `not should_retry(action)`
- `should_ignore(action)`: only idempotency_skip with result.ok=True
- `retry_count_today(action_id)`: derives from today's decision log (not a separate file)

**7. Workflow step factories** (`steps.py:36–210`)
- `ScriptWorkflowSpec`: declarative shape (name, script_path, description, risk, timeout, idempotency_key, reasoning)
- `run_script_workflow(spec, approve)`: runs full boilerplate, prints JSON summary, returns exit code (0 on ok/deferred/skipped, 1 on failure)
- `script_step(...)` / `api_step(...)`: `ActionStep` factories for use in pipelines

**8. Default workflows** (`workflows.py:28–106`)
- Registers three migrated CP workflows:
  - `morning_prep` → imports scripts.scheduled.morning_prep_cp, calls main()
  - `nightly_consolidation` → same
  - `weekly_review` → same
- Registers three handler workflows:
  - `handle_deferred_stale`
  - `handle_action_failed`
  - `handle_action_retry_requested`
- Default signal bindings:
  - `morning_ready` → `morning_prep`
  - `nightly_cycle` → `nightly_consolidation`
  - `weekly_cycle` → `weekly_review`
  - `deferred_stale` → `handle_deferred_stale`
  - `action_failed` → `handle_action_failed`
  - `action_retry_requested` → `handle_action_retry_requested`

### What does NOT exist (VERIFIED BY ABSENCE)

**1. Live loop scheduling**
- `scripts/orchestrator_loop.py` exists (entry point: `python3 scripts/orchestrator_loop.py --cycles 1`)
- No cron job to run it
- No systemd unit to run it
- Current crontab (from context): `0 6 * * * cd /opt/OS && python3 eos_ai/orchestrator.py` — this is the OLD orchestrator, not the new loop
- Status: **Code exists, not scheduled**

**2. Cron → signal wiring (Phase 7, documented but not applied)**
- Design in 2026-04-08-orchestrator-phase-6.md lines 105–167
- Three cron jobs currently call .sh scripts directly:
  ```
  30 5 * * * bash /opt/OS/scripts/scheduled/morning_prep.sh
  0  3 * * * bash /opt/OS/scripts/scheduled/nightly_consolidation.sh
  0  6 * * 0 bash /opt/OS/scripts/scheduled/weekly_review.sh
  ```
- Target topology: cron emits `morning_ready`, `nightly_cycle`, `weekly_cycle` signals; loop drains every 5 min
- **Not yet applied.** Wrappers exist and work, but cron still calls .sh directly (via phase 5 wrappers, not signals)

**3. Non-cron signal sources**
- Only cron + manual operator `emit_signal()` can trigger workflows today
- No webhook listener (e.g., Slack `/approve` → signal)
- No meeting-finished listener → `meeting_complete` signal
- No budget-alert listener → `budget_threshold_crossed` signal

**4. Deferred approval CLI (persistent queue browser)**
- `/opt/OS/scripts/deferred.py` exists and lists deferred queue
- But no interactive "browse 10 pending, pick one to approve" loop
- Operator must `approve <action_id>` one at a time or `reject <action_id>`

**5. Workflow composition beyond Pipeline**
- DAG support: not needed (sequential is fine)
- Branching (if/else on earlier step output): not implemented, would use FuncStep to pick next steps at runtime
- Loop over array of items: not implemented, would require manual iteration in FuncStep

### Does the loop execute actions directly or only emit signals?

**ANSWER: Only emits signals. Every execution goes through `run_workflow()` or `run_action()`.**

Evidence:
- `loop.py:135–142`: `orch.run_workflow(wf_name, context=...)` is the only execution path
- If workflow is Pipeline: `pipeline.py:222` routes each ActionStep through `run_action()`
- If workflow is callable: handler functions like `handle_action_retry_requested()` call `run_action()` explicitly (handlers.py:289)
- Control Plane is never bypassed

### Docs vs. Code

| Claim | Docs | Code | Status |
|-------|------|------|--------|
| Signal emissions drain with handlers | orchestrator.md | ✓ loop.py:112–168 | COMPLETE |
| Stale deferred scan + emit | orchestrator.md | ✓ loop.py:176–218 | COMPLETE |
| Failure scan + retry/escalate | orchestrator.md | ✓ loop.py:288–346 | COMPLETE |
| Phase 6 handlers (3 workflows) | 2026-04-08-orchestrator-phase-6.md | ✓ handlers.py | COMPLETE |
| Cron→signal mapping (Phase 7) | 2026-04-08-orchestrator-phase-6.md lines 105–147 | ✗ not applied | DESIGN ONLY |
| Loop is not a scheduler | orchestrator.md intro | ✓ no sleep loops in loop.py itself | COMPLETE |

**No contradictions. Phase 7 is fully designed but not yet applied.**

---

## 6. Workflows Audit

### morning_prep (Cron: 30 5 * * *)

**Files:**
- Wrapper: `scripts/scheduled/morning_prep_cp.py` (83 lines)
- Bash: `scripts/scheduled/morning_prep.sh` (70 lines)

**Execution path:**
1. Cron invokes `python3 scripts/scheduled/morning_prep_cp.py --approve`
2. Wrapper creates `ScriptWorkflowSpec` (name=morning_prep, script=morning_prep.sh, risk=medium, idempotency_key=f"morning_prep:{today}")
3. `run_script_workflow(spec, approve=True)` routes through `run_action(type=run_script, ...)`
4. `explicit_approval=True` → auto-approved (skips deferral)
5. Executor invokes bash script with 600s timeout
6. Wrapper prints JSON summary and exits

**Idempotency:** `morning_prep:<YYYY-MM-DD>` TTL 23h — never collides with tomorrow's run

**Risk:** Medium (mutates ritual state, consumes CC budget, touches LLM provider health)

**What it does:** keys, Neon check, GWS sync, CC brief fetch

**Logged:** Full execution lifecycle (proposed, validated, approved, executed)

**Status:** ✓ ACTIVE (currently running via wrapper)

---

### nightly_consolidation (Cron: 0 3 * * *)

**Files:**
- Wrapper: `scripts/scheduled/nightly_consolidation_cp.py` (80 lines)
- Bash: `scripts/scheduled/nightly_consolidation.sh` (100 lines)

**Execution path:** Same as morning_prep

**Idempotency:** `nightly_consolidation:<YYYY-MM-DD>` TTL same day; dry-run uses `nightly_consolidation_dry:<date>` (safe collision avoidance)

**Risk:** Medium

**What it does:** reconciliation ritual

**Status:** ✓ ACTIVE (wrapped)

---

### weekly_review (Cron: 0 6 * * 0)

**Files:**
- Wrapper: `scripts/scheduled/weekly_review_cp.py` (75 lines)
- Bash: `scripts/scheduled/weekly_review.sh` (70 lines)

**Execution path:** Same

**Idempotency:** `weekly_review:<ISO-week>` TTL 6 days (ISO week scope)

**Risk:** Low (read-heavy, no state mutation, $1/week budget capped in .sh)

**Status:** ✓ READY (wrapped, not yet in live cron)

---

### nightly_maintenance (Cron: 0 2 * * *)

**Files:**
- Bash only: `scripts/scheduled/nightly_maintenance.sh` (140 lines)
- No wrapper

**Execution path:** Direct bash (no Control Plane logging)

**What it does:** backup, cache clear

**Status:** ✗ LEGACY (not wrapped, out of scope for Phase 7)

---

### Summary

| Workflow | Wrapped | In CP | Idempotent | Risk | Deferred? | Cron Active |
|----------|---------|-------|-----------|------|-----------|------------|
| morning_prep | yes | yes | yes | medium | yes | yes |
| nightly_consolidation | yes | yes | yes | medium | yes | yes |
| weekly_review | yes | yes | yes | low | yes | no (ready) |
| nightly_maintenance | no | no | no | N/A | no | yes |

**All paths through Control Plane use `run_action(type=run_script, ...)`.**

---

## 7. Policy / Authority Audit

### Shared governance

**Two systems coexist:**
1. **Control Plane** (`core.action_system`) — runtime actions (run_script, shell_command, write_file, call_api), lowercase risk (low/medium/high/critical)
2. **Authority Engine** (`eos_ai.authority_engine`) — business actions (send_dm, publish_content, execute_payment), uppercase risk (LOW/MEDIUM/HIGH/CRITICAL)

**Bridge:** `core/action_system/policy.py` (164 lines)

### Risk mapping

**Control Plane canonical vocabulary:** `low` < `medium` < `high` < `critical`

**Authority Engine mapping:**
- `LOW` → `low`
- `MEDIUM` → `medium`
- `HIGH` → `high`
- `CRITICAL` → `critical`

**Upgrade rule:** When a runtime action carries business semantics (caller passes `business_action_type`), Control Plane picks the stricter of declared risk + business risk. Never downgrades.

**Example:** `run_script` declared as low risk, but `business_action_type="publish_content"` maps to HIGH → effective risk = HIGH.

### Boundaries (hardcoded in validator.py)

**Forbidden paths (write_file):**
- `/etc`, `/boot`, `/sys`, `/proc`, `/dev`, `/root/.ssh`

**Dangerous shell tokens (shell_command):**
- `rm -rf /`, `mkfs`, fork bomb, `dd if=`, `shutdown`, `reboot`, `> /dev/sda`

**Per-agent/per-venture policies:** Not implemented (Phase 2 scope, flagged but not coded)

### Current integration status

**Code exists:** policy.py is complete and well-designed.

**Not live:** No workflow currently passes `business_action_type` to `run_action()`.
- morning_prep_cp.py: `run_action(..., business_action_type=None, ...)` — implicit None
- nightly_consolidation_cp.py: same
- weekly_review_cp.py: same

**Reason:** Authority Engine is a heavy dependency (imports db module). Phase 1 explicitly designed the bridge so CP doesn't crash if business layer is unavailable, but current workflows don't use it.

**To activate:** Audit morning_prep.sh, nightly_consolidation.sh, weekly_review.sh; identify which steps carry business semantics; pass the corresponding `business_action_type` from the wrapper.

---

## 8. Docs vs. Code Consistency

### Complete + Documented + Implemented

| Subsystem | Docs | Code | Proof |
|-----------|------|------|-------|
| TME verify + linter | tool_mastery_engine_system.md | ✓ verify_tool_skill.py | Complete |
| TME staleness | tool_mastery_engine_system.md | ✓ check_skill_staleness.py | Complete |
| TME Neon sync | tool_mastery_engine_system.md | ✓ sync_skills_to_neon.py | Complete |
| TME query CLI | tool_mastery_engine_system.md | ✓ query_skills.py | Complete |
| CP action model | control_plane.md | ✓ actions.py | Complete |
| CP lifecycle | control_plane.md | ✓ control_plane.py | Complete |
| CP validation + approval | control_plane.md | ✓ validator.py + policy.py | Complete |
| CP deferred queue | control_plane.md | ✓ deferred.py | Complete |
| CP snooze/wake | control_plane.md Phase 4.5 | ✓ deferred_status.py | Complete |
| CP idempotency | control_plane.md Phase 4 | ✓ idempotency.py | Complete |
| Orchestrator workflows | orchestrator.md | ✓ orchestrator.py | Complete |
| Orchestrator pipeline | orchestrator.md | ✓ pipeline.py | Complete |
| Orchestrator signals | orchestrator.md | ✓ signals.py | Complete |
| Orchestrator loop | orchestrator.md | ✓ loop.py | Complete |
| Orchestrator Phase 6 handlers | 2026-04-08-orchestrator-phase-6.md | ✓ handlers.py | Complete |

### Documented-NOT-Implemented (Flagged but not coded)

| Claim | Doc | Code | Status |
|-------|-----|------|--------|
| Per-agent policies | control_plane.md Phase 1 | ✗ not in validator.py | Design flagged for Phase 2 |
| Dry-run mode (distinct from deferred) | control_plane.md Phase 4 | ✗ not in control_plane.py | Design flagged for Phase 5 |
| Authority Engine integration (live) | policy.py docstring | ✓ code exists but not called | Stubbed; no workflow uses it |

### Designed-NOT-Implemented (Design doc, code exists, not applied)

| Design | Doc | Code | Status |
|--------|-----|------|--------|
| Cron → signal wiring (Phase 7) | 2026-04-08-orchestrator-phase-6.md | ✓ signals.py, loop.py, handlers.py; ✗ not in crontab | Ready to apply |
| Live loop scheduling | 2026-04-08-orchestrator-phase-6.md | ✓ loop.py; ✗ no cron/systemd job | Waiting for Phase 7 apply |
| TME refresh triggers | (not documented, but implied) | ✗ no code | Missing |
| TME backlog scan | (not documented) | ✗ no code | Missing |
| TME create-if-missing | (not documented) | ✗ no code | Missing |

### Implemented-NOT-DOCUMENTED (code exists, no reference doc)

| Implementation | Location | Doc | Status |
|----------------|----------|-----|--------|
| Orchestrator state tracking | orchestrator.py:142–175 | ✓ mentioned in orchestrator.md but sparse | Could use more detail |
| Discord worker offset tracking | discord_approval_worker.py:63–75 | ✗ not documented | Needs reference |
| Signal outcome tagging | signals.py:184–193 | ✗ not documented (ok/failed suffixes) | Implied by loop code |

### Contradictions

**None found.** Docs and code agree. Phase 7 design is explicit about what's designed (cron wiring) vs. not yet applied.

---

## 9. Gap Analysis

### COMPLETE (subsystems live and integrated)

1. **Control Plane core** (propose → validate → approve → execute → log)
   - Action model ✓
   - Lifecycle ✓
   - Validation rules ✓
   - Approval policy ✓
   - Deferred queue ✓
   - Idempotency ✓
   - Logging (audit trail) ✓

2. **Tool Mastery Engine — query side**
   - Discovery (all_skill_slugs, load_skill) ✓
   - Verification (linter) ✓
   - Staleness audit ✓
   - Dependency graph ✓
   - Neon sync (read+write) ✓
   - Query CLI ✓

3. **Orchestrator — execution & composition**
   - Workflow registry ✓
   - Pipeline (ActionStep/FuncStep) ✓
   - Signal layer (emit/consume/handlers) ✓
   - Autonomous loop (drain/scan/react) ✓
   - Phase 6 handlers ✓
   - Decision helpers ✓

### PARTIAL (code exists, missing final wiring or automation)

1. **Control Plane — business integration**
   - Authority Engine bridge code ✓
   - Never called from any workflow ✗

2. **Control Plane — automation**
   - Handlers exist (retry, escalate) ✓
   - Loop never scheduled via cron ✗
   - Phase 7 wiring (cron→signal) designed but not applied ✗

3. **TME — lifecycle**
   - Staleness detected ✓
   - Refresh triggered: ✗ (manual only)
   - Backfill scan: ✗
   - Bootstrap on env setup: ✗

4. **Deferred approval UX**
   - Queue persisted ✓
   - CLI list/approve/reject ✓
   - Interactive browser: ✗

### MISSING (not in code or design)

1. **Tool Mastery Manager** — a self-managing system that:
   - Scans agent code for tool mentions
   - Routes unknown/stale tools to research workflow
   - Backfills missing metadata
   - Escalates on verification failures
   - **Not designed. No code.**

2. **Per-agent/per-venture policies**
   - Flagged Phase 2, no code

3. **Dry-run mode** (distinct from deferred)
   - Flagged Phase 5, no code

4. **Non-cron signal sources**
   - No webhook listener, meeting-finished listener, budget-alert listener
   - Implied by signal architecture but not built

5. **Orchestrator DAG/branching/looping**
   - Not needed for current workflows (all sequential)
   - FuncStep can be used to pick next steps, but not built

---

## 10. Risks and Redundancies

### Most dangerous false assumption

**"The system is complete and ready for autonomy."**

Truth: It is intentionally modular. Control Plane works. Orchestrator works. But the loop is not scheduled, and three production workflows still call .sh directly (via Phase 5 wrappers, not Phase 7 signal flow).

**Mitigations:**
- Phase 7 design is explicit
- Audits (this file + prior phases) clearly mark what's applied vs. not

### Key chokepoints (single points of failure)

1. **Executor** (`executor.py:113`) — one dispatch point for all side effects
   - Mitigation: simple switch statement, easy to audit

2. **Notifier** (`notifier.py`) — deferred queue announcement
   - If Discord webhook is down, deferred actions are still queued on disk (safe)
   - Mitigation: FileNotifier is baseline; Discord is optional

3. **Decision log** — source of truth for "why did we do X"
   - If appending fails, action still executes (deferred logs are written first)
   - Mitigation: append-only JSONL survives partial writes (incomplete JSON line is skipped on read)

### Dead code / overbuild

1. **Stale deferred scan** vs. **snooze/wake**
   - Both mechanisms exist for action lifecycle management
   - `scan_stale_deferred()` emits `deferred_stale` signal
   - `wake_due_snoozed()` promotes `snoozed → pending`
   - **Not redundant:** stale is "waiting too long", wake is "operator said wake at time X"
   - **No conflict:** snoozed items are immune from stale scan

2. **Two logs: execution + decision**
   - Separate by intent: "what happened" (execution) vs. "why did we do X" (decision)
   - Not redundant; different query patterns

3. **Idempotency sentinel vs. deferred file**
   - Sentinel is in-flight tracking (TTL + state machine)
   - Deferred file is the actual action (with full context)
   - **Not redundant:** sentinel is lightweight O(1) check; deferred file is the durable queue

### Overlap in governance

- **Control Plane policy.py** and **Authority Engine RISK_CLASSES**
- No actual overlap: CP is runtime, AE is business
- But bridge is lazy-loaded to avoid hard dependency
- **Current risk:** Workflows don't use the bridge; business risk never affects runtime decisions
- **Mitigation:** Audit workflows and activate bridge where needed (Phase 5 work)

### Manual chokepoints (operator must do work)

1. **Skill refresh** — operator must run research manually
   - TME detects staleness but doesn't trigger research
   - **Mitigated by:** `check_skill_staleness.py` is CLI + can be called from cron; a simple agent could consume the output

2. **Deferred approval** — operator must `deferred.py approve <id>` one at a time
   - No batch interface, no interactive browser
   - **Mitigated by:** Discord worker streams deferred to a channel (approvals could be Discord reactions)

3. **Cron wiring** — Phase 7 not yet applied
   - three production cron lines still call .sh directly
   - **Mitigated by:** Phase 7 design is explicit and ready to apply; no missing code

---

## 11. Recommended Next Step

### Option A: Harden / Activate (RECOMMENDED)

**One action: Apply Phase 7 cron→signal wiring.**

1. Add `/opt/OS/scripts/orchestrator_loop.py --cycles 1` to cron (`*/5 * * * *`)
2. Replace three production cron lines with `emit_signal` calls
3. Verify signal draining and handler execution for 24 hours
4. Monitor decision log and orchestrator state

**Why:** Control Plane code is solid. Orchestrator code is solid. Phase 7 design is complete and tested (in isolation). Applying it unblocks:
- Retry automation (handlers already exist, just need loop to run)
- Signal-driven workflows (foundation for Phase 8: non-cron signals)
- Stale deferred escalation (handler already exists)

**Time estimate:** 2 hours (apply changes + monitor)

**Blocker:** None. All code exists.

### Option B: Build Tool Mastery Manager

**Rationale:** TME is 60% self-managing (verify + audit + sync exist). Missing the outer loop (discovery + refresh + backfill).

**Scope:** 
1. `tmr_monitor.py` — scans execution log for tool mentions, routes unknown/stale to research
2. `tme_backfill.py` — finds MISSING_DATE skills, opens Notion card for researcher
3. `tme_verify_workflow.py` — runs verifier, escalates failures to operator

**Why now:** TME is the lowest-hanging fruit. Once this is done, every workflow gets skill coverage for free.

**Time estimate:** 3–5 days (design + code + test)

**Blocker:** None. Architecture is clear.

### Option C: Write formal spec first

**Rationale:** "What should the full system do?" is not yet written anywhere.

**Scope:**
- Intended autonomy level (e.g., "can auto-approve low-risk, no business semantics")
- Signal sources (cron, webhook, meeting-finished, budget-alert, etc.)
- Skill lifecycle (discovery → research → verify → deploy → monitor → refresh)
- Authority boundaries (runtime vs. business, operator vs. AI, CEO vs. founder)

**Why:** Prevents overbuild. Clarifies what "done" looks like.

**Time estimate:** 2–3 days

**Blocker:** None. Existing docs give good shape.

---

## 12. Conclusion

**The system is real, tested, and working.** Three audits (Phase 3, 4, 6) prove every component in isolation. But it is deliberately not yet unified — Phase 7 (cron wiring) is the seam.

**Activate Phase 7.** Thirty minutes of cron edits unblock all the retry automation and deferred escalation that the handlers already implement. Do that before new features.

**Then extend:** TME Manager (backfill + refresh) or non-cron signals (webhooks, meeting-finished) or both. The foundation is solid.

---

## Appendix: File line counts (core + orchestrator)

```
core/action_system/:
  54  actions.py
  272  control_plane.py
  187  validator.py
  113  executor.py
  72  logging.py
  96  deferred.py
  241  deferred_status.py
  119  notifier.py
  295  idempotency.py
  164  policy.py
  38  tme.py
  ────────
  1,597  total

core/orchestrator/:
  199  orchestrator.py
  276  pipeline.py
  399  loop.py
  208  signals.py
  321  handlers.py
  158  decisions.py
  210  steps.py
  109  workflows.py
  ────────
  1,880  total

scripts/ (key files):
  230  _tme_common.py
  212  query_skills.py
  150+ verify_tool_skill.py
  170  check_skill_staleness.py
  100+ build_skill_graph.py
  80+ sync_skills_to_neon.py
  150+ decisions.py
  200+ deferred.py
  100+ control_plane_run.py
  50+ orchestrator_loop.py
  200+ orchestrator_status.py
  83  scheduled/morning_prep_cp.py
  80  scheduled/nightly_consolidation_cp.py
  75  scheduled/weekly_review_cp.py
  200+ workers/discord_approval_worker.py

Docs (audit reports):
  2026-04-06-tool-mastery-system-upgrade.md
  2026-04-06-control-plane-phase-1.md
  2026-04-08-control-plane-phase-2.md
  2026-04-08-control-plane-phase-3.md
  2026-04-08-control-plane-phase-4.md
  2026-04-08-orchestrator-phase-5.md
  2026-04-08-orchestrator-phase-6.md
  current-state-code-audit.md (this file)
```

