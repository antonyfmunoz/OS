---
type: codewiki-inventory
dir: scripts
source_sha: 0312cc4e33802424a5a6a5c1807dcd0097e63208
---

# `scripts/` — File Inventory

**Files:** 215 regular + 0 symlinks · **Bytes:** 9,987,420

[Narrative page](../dirs/scripts.md)


## scripts/ (root)

| Path | Lines | Purpose |
|---|---|---|
| `scripts/.env.beast.tpl` | 3 | 1Password op-run env template for Beast node credentials |
| `scripts/.env.gws.tpl` | 7 | Google Workspace provider-token op template (WP-P4-PROVIDER-TOKEN-VAULTING-001) |
| `scripts/__init__.py` | 0 | package marker (empty) |
| `scripts/_tme_common.py` | 236 | Shared helpers for Tool Mastery Engine system scripts. |
| `scripts/agent_executor.log` | — | runtime log of agent executor runs (should live in logs/) |
| `scripts/agent_task_executor.py` | 339 | Agent Task Executor — polls the tasks table for |
| `scripts/auto_report_dispatch.py` | 165 | Stop hook: auto-dispatch a report to cockpit chat and Discord |
| `scripts/backup.sh` | 29 | EOS Daily Backup |
| `scripts/bis_context.py` | 87 | BIS context injector — prints active venture context from VENTURES_JSON. |
| `scripts/browser_gate_collector.py` | 684 | Browser Gate Collector — runs ON Beast with real display. |
| `scripts/browser_intent_loop_proof.py` | 365 | P4S-31C — deployed Cockpit Chat intent-loop browser proof. |
| `scripts/build_notion_databases.py` | 116 | Create the 9 databases that failed in the first build pass. |
| `scripts/build_notion_workspace.py` | 713 | Build EOS Notion Workspace |
| `scripts/build_palace.py` | 484 | build_palace.py — Generates the EOS memory palace from the graph. |
| `scripts/build_skill_graph.py` | 220 | build_skill_graph.py — Tool Mastery Engine skill dependency graph. |
| `scripts/c29_class_b_runner.py` | 1,266 | C29 Class B Controlled Runner -- Playwright automation harness. |
| `scripts/c29_run_beast.py` | 44 | Beast launcher for C29 Class B Runner. |
| `scripts/c29_thesis_run_beast.py` | 45 | Beast launcher for C29.5 Thesis Validation Runner. |
| `scripts/c29_thesis_runner.py` | 1,413 | C29.5 Thesis Validation Runner — direct thesis-dimension testing. |
| `scripts/calendar_invite_handler.py` | 348 | Calendar Invite Handler — polls for pending invites every 15 mins. |
| `scripts/call_prep.py` | 442 | Call Prep — runs every 15 minutes via cron. |
| `scripts/check_cpu_gate.py` | 150 | Pre-commit gate: block raw subprocess usage in substrate/ and organism/. |
| `scripts/check_credential_injection.py` | 172 | Pre-commit gate: block plaintext credential patterns in code. |
| `scripts/check_dependency_direction.py` | 401 | Pre-commit gate: blocks commits that violate UMH architecture dependency direction. |
| `scripts/check_instance_leak.py` | 265 | Pre-commit gate: blocks commits that leak instance-specific values into substrate code. |
| `scripts/check_mesh_relay_firewall.py` | 144 | Check mesh relay firewall state for correctness and safety. |
| `scripts/check_ontology_homes.py` | 276 | Pre-commit gate: enforce the ontology-home map (WP-P3 ontology consolidation). |
| `scripts/check_ontology_layers.py` | 306 | Pre-commit gate: enforces the ontology/metamodel layer contract (WP-P3-001). |
| `scripts/check_projection_leak.py` | 262 | Pre-commit gate: blocks projection-specific naming from substrate code. |
| `scripts/check_projection_registry_reads.py` | 204 | Pre-commit gate: exactly one reader of data/umh/projection_registry.json. |
| `scripts/check_pytest_collection.py` | 142 | Pre-commit gate: blocks commits that break pytest collection. |
| `scripts/check_secret_patterns.py` | 92 | Pre-commit hook: reject commits containing secret patterns. |
| `scripts/check_skill_staleness.py` | 170 | check_skill_staleness.py — Tool Mastery Engine staleness audit. |
| `scripts/check_stop_condition.py` | 95 | Stop hook handler. |
| `scripts/check_type_divergence.py` | 386 | Pre-commit gate: blocks commits that create types diverging from canonical registry. |
| `scripts/check_ungoverned_mutations.py` | 228 | Pre-commit gate: blocks commits introducing ungoverned mutation endpoints. |
| `scripts/check_voice_runtime_divergence.py` | 455 | Gate 14 — Voice Runtime Divergence (P4S31 Voice Convergence). |
| `scripts/claude-cpu-limited` | 6 | cpulimit wrapper for running Claude CLI under a CPU ceiling |
| `scripts/codebase_graph.py` | 1,236 | codebase_graph.py — Persistent codebase knowledge graph for EOS. |
| `scripts/control_plane_run.py` | 105 | control_plane_run.py — run a shell command or script through the Control Plane. |
| `scripts/cpu-watchdog.sh` | 103 | UMH CPU Watchdog — last-resort defense against Hostinger throttling. |
| `scripts/create_meetings_db.py` | 67 | — |
| `scripts/cron-run` | 59 | Cron wrapper — load-gated (2.0/core), nice+flock protected runner for scheduled scripts (CPU Gate layer 4) |
| `scripts/day_reminder.py` | 116 | Day Reminder — fires reminders throughout the day. |
| `scripts/dead_code_check.py` | 58 | Check for dead code in the substrate package. |
| `scripts/deadline_monitor.py` | 182 | Deadline Monitor — checks tasks with due dates |
| `scripts/decisions.py` | 203 | decisions.py — operator CLI for the Control Plane decision log. |
| `scripts/deferred.py` | 349 | deferred.py — operator CLI for the Control Plane deferred queue. |
| `scripts/detemplatize_skills.py` | 205 | Removes hardcoded venture data from all skills. |
| `scripts/device_sync.py` | 113 | Post-commit hook: push to GitHub, pull on Beast. |
| `scripts/discord_daily_clear.py` | 34 | — |
| `scripts/discord_setup_channels.py` | 196 | Discord Builder/Product Channels Setup v1. |
| `scripts/emit_signal.py` | 68 | Emit an orchestrator signal from cron or the shell. |
| `scripts/env_upsert.py` | 104 | Idempotent .env key upsert. |
| `scripts/eod_sync.py` | 242 | EOD Sync — 6pm PDT daily closing loop. |
| `scripts/eos_status.py` | 161 | EOS Operator Status — single inspectable surface. |
| `scripts/export_pipeline.py` | 315 | export_pipeline.py — Autonomous export-to-ingestion pipeline. |
| `scripts/fire_export.py` | 365 | Fire a single browser export via Camoufox anti-detect browser. |
| `scripts/fire_exports_windows.ps1` | 69 | fire_exports_windows.ps1 — Run browser exports from Windows workstation |
| `scripts/gen_voice_error_codes_ts.py` | 91 | Codegen: generate the TS mirror of the canonical VoiceErrorCode enum. |
| `scripts/generate_codebase_report.py` | 1,119 | generate_codebase_report.py — Exhaustive visual codebase report. |
| `scripts/generate_codewiki.py` | 855 | CodeWiki inventory generator — deterministic backbone of docs/codewiki/. |
| `scripts/generate_vapid_keys.py` | 35 | Generate VAPID key pair for Web Push notifications. |
| `scripts/github_trinity_ingest.py` | 229 | github_trinity_ingest.py — Clone and ingest the three core repos via canonical pipeline. |
| `scripts/goals.py` | 109 | CLI entry points for goal management. Wraps runtime/goal_selector.py. |
| `scripts/gws_scanner_cron.py` | 104 | gws_scanner_cron.py — Thin cron wrapper for GWSDocumentScanner. |
| `scripts/healthcheck.sh` | 29 | UMH Health Check |
| `scripts/inbox_gps_afternoon.py` | 29 | Email GPS — 3pm afternoon inbox pass. |
| `scripts/inbox_zero_init.py` | 403 | Inbox Zero Initialization — run ONCE on first DEX setup. |
| `scripts/incremental_graph.py` | 772 | incremental_graph.py — Dirty-set incremental updates for the codebase graph. |
| `scripts/ingest_conversations.py` | 212 | Batch ingest conversation exports into UMH canonical memory store. |
| `scripts/ingest_github_repos.py` | 218 | Batch ingest GitHub repos into UMH canonical memory store. |
| `scripts/install-cpu-watchdog.sh` | 40 | Install the UMH CPU watchdog as a systemd timer. |
| `scripts/install_divergence_gate.sh` | 26 | Install the type divergence pre-commit hook. |
| `scripts/install_graph_hooks.sh` | 24 | install_graph_hooks.sh — wire pre-commit + post-merge hooks into .git/hooks. |
| `scripts/install_hooks.sh` | 55 | Install UMH pre-commit hooks into the repository. |
| `scripts/install_sync_automation.sh` | 113 | install_sync_automation.sh — install sync ritual automation (hook + cron) |
| `scripts/install_windows_relay_autostart.ps1` | 169 | — |
| `scripts/invariant_check.sh` | 78 | Invariant checks for UMH substrate unification. |
| `scripts/loop_runner.py` | 202 | Loop runner CLI — start, stop, and query persistent loops. |
| `scripts/measure_phase8_batch.py` | 339 | Phase 8 batch measurement — full re-extraction. |
| `scripts/memory_continuous_sync.py` | 132 | Continuous memory synchronization. |
| `scripts/memory_instant_sync.py` | 114 | Instant memory sync hook — fires on PostToolUse for Write/Edit. |
| `scripts/memory_watcher_daemon.py` | 65 | Memory Watcher Daemon — runs the substrate memory watcher. |
| `scripts/merge_graphs.py` | 341 | merge_graphs.py — Merge graphify_overlay.json into codebase_graph.json. |
| `scripts/meta_ide_browser_gate.py` | 330 | Meta IDE Browser Verification Gate — 4-layer × 3-pass. |
| `scripts/midday_checkin.py` | 110 | Mid-day check-in — runs at 12:30pm PDT. |
| `scripts/migrate_instance_leaks.py` | 310 | Bulk migration tool: mechanically replaces instance-specific values in substrate/ code. |
| `scripts/migrate_module.sh` | 78 | Phase C module migration helper |
| `scripts/morning_intel.py` | 199 | Morning Intelligence Brief — runs at 5:45am PDT daily, |
| `scripts/noshow_detector.py` | 164 | No-show detector — checks meetings that started 30+ min ago with no |
| `scripts/notion_cleanup.py` | 568 | Notion Cleanup — archives old scaffold databases |
| `scripts/notion_outcome_sync.py` | 197 | Notion → Neon Outcome Sync |
| `scripts/notion_seed.py` | 508 | Notion Seed — populates initial rows in EOS Notion databases. |
| `scripts/notion_seed_all.py` | 933 | Notion Seed All — seeds Empyrean Creative, Personal Brand ventures |
| `scripts/notion_setup.py` | 1,082 | Notion Setup — creates the full per-venture primitive database |
| `scripts/notion_sync_poller.py` | 43 | Notion Sync Poller — runs every 15 minutes via cron. |
| `scripts/notion_tasks_sync.py` | 282 | Notion Tasks → Neon Sync |
| `scripts/notion_tasks_sync_state.json` | 4 | sync-state checkpoint for Notion tasks sync |
| `scripts/oauth_grant_gmail.py` | 151 | One-shot OAuth grant for Gmail scope — run on Windows (needs browser). |
| `scripts/obsidian_rsync.sh` | 67 | obsidian_rsync.sh — sync Obsidian vault from Windows machine via Tailscale |
| `scripts/op_run.sh` | 99 | op_run.sh — canonical UMH 1Password Secret Runtime wrapper. |
| `scripts/orchestrator.py` | 1,124 | orchestrator.py — Continuous, autonomous execution layer for EOS. |
| `scripts/orchestrator_loop.py` | 74 | Orchestrator loop runner. |
| `scripts/orchestrator_status.py` | 388 | orchestrator_status.py — operator-friendly snapshot of the Control Plane. |
| `scripts/organism_mutation_cli.py` | 267 | organism_mutation_cli.py — CLI for governed mutations. |
| `scripts/p4s31c_isolation_demo.py` | 76 | P4S-31C isolation demonstration app — spare-port, no daemon, no DB writes. |
| `scripts/p4s31c_load_probe.py` | 139 | P4S-31C bounded load probe — CPU-law compliant. |
| `scripts/permission_notify.py` | 104 | PermissionRequest hook. |
| `scripts/phase75a_classifier.py` | 280 | Phase 75A — Auto-classify UMH modules by PRD domain and MVP status. |
| `scripts/phase75a_dep_scanner.py` | 232 | Phase 75A — AST-based dependency scanner for UMH. |
| `scripts/portfolio_brief.py` | 127 | Sunday Portfolio Brief — runs at 6am every Sunday. |
| `scripts/post_meeting_capture.py` | 134 | Post-meeting capture — polls for recently ended calendar events |
| `scripts/pre-commit` | 40 | Pre-commit gate runner — executes the repo's enforcement gate scripts |
| `scripts/pre_tool_use_log.py` | 56 | PreToolUse hook. |
| `scripts/probe_beast_projection_source.sh` | 41 | Beast projection source-truth probe — READ-ONLY. |
| `scripts/probe_beast_source_readiness.sh` | 130 | Beast projection source-READINESS probe — READ-ONLY, repeatable, governed. |
| `scripts/proof_p4s31b_input_surface.py` | 203 | P4S-31B proof harness — Cockpit Chat intent rail, through the REAL handlers. |
| `scripts/query_graph.py` | 328 | query_graph.py — Retrieval layer over the EOS codebase knowledge graph. |
| `scripts/query_skills.py` | 214 | query_skills.py — Tool Mastery Engine CLI registry. |
| `scripts/refresh_fly_token.py` | 57 | Refresh Fly.io deploy token using the org token from 1Password. |
| `scripts/relationship_nurture.py` | 127 | Relationship nurturing — checks for contacts not heard from in 30+ days |
| `scripts/requirements.txt` | 7 | Python pip dependencies |
| `scripts/rotate_jsonl.py` | 60 | Rotate JSONL stores that exceed a size threshold. |
| `scripts/rotate_secrets.sh` | 107 | rotate_secrets.sh — automated 30-day secret rotation |
| `scripts/router_claude_runtime_debug.py` | 70 | Router runtime debug helper — prints the actual, live state the router |
| `scripts/run_browser_gate.bat` | 18 | Windows batch script — run browser gate |
| `scripts/run_continuity_validation.py` | 386 | Continuity engine end-to-end validation. |
| `scripts/run_graphify.py` | 526 | run_graphify.py — Pluggable enrichment layer (Graphify adapter). |
| `scripts/run_m1_operator_mvp_check.py` | 200 | M1 Operator MVP Closure — verification script. |
| `scripts/run_prod.sh` | 55 | UMH Production Runner |
| `scripts/run_qualification.py` | 1,148 | Adaptive Qualification Runner — convergence-driven, not count-driven. |
| `scripts/run_reconciliation_ingestion.py` | 211 | Multi-document ingestion with reconciliation. |
| `scripts/run_reconciliation_query_validation.py` | 170 | Reconciliation query validation. |
| `scripts/run_reconciliation_replay_validation.py` | 128 | Reconciliation replay validation. |
| `scripts/run_ui.sh` | 12 | Start UMH with UI |
| `scripts/seed_eos_watermarks_to_now.py` | 65 | Seed EOS watermarks to NOW — skip historical replay on next poller start. |
| `scripts/send_to_builder.py` | 34 | Send a file to the EOS Discord builder channel. |
| `scripts/session_bootstrap.py` | 187 | session_bootstrap.py — Mandatory context load at session start. |
| `scripts/session_start_context.py` | 231 | SessionStart hook. |
| `scripts/shim_retirement_monitor.py` | 272 | Shim retirement readiness monitor. |
| `scripts/sovereignty-grep.sh` | 49 | Canonical sovereignty grep for UMH codebase. |
| `scripts/start_windows_relay_node.ps1` | 334 | — |
| `scripts/subagent_start_context.py` | 72 | SubagentStart hook. |
| `scripts/substrate_audio_loop_cli.py` | 136 | Bounded operator CLI for the local audio loop. |
| `scripts/substrate_claude_session_cli.py` | 171 | Claude Code Session Bridge CLI. |
| `scripts/substrate_discord_voice_transport_cli.py` | 238 | Discord voice transport CLI — bounded operator interface to the |
| `scripts/substrate_execution_trace_cli.py` | 178 | Operator CLI for EOS execution trace history. |
| `scripts/substrate_local_listener.py` | 104 | Local listener CLI — emit a bounded activation trigger. |
| `scripts/substrate_operator_cli.py` | 229 | Operator CLI for EOS substrate — Operator Interface Layer v1. |
| `scripts/substrate_operator_tick.sh` | 143 | Substrate operator tick — smallest safe drain+reconcile cycle for the |
| `scripts/substrate_voice_session_cli.py` | 156 | Bounded operator CLI for the voice session substrate. |
| `scripts/substrate_wake_producer_cli.py` | 110 | Wake producer CLI — simulate wake-word / clap events and view history. |
| `scripts/summarize_nodes.py` | 150 | summarize_nodes.py — Append-only one-line summaries for every graph node. |
| `scripts/sync_all.sh` | 262 | sync_all.sh — cross-device git sync check and fast-forward |
| `scripts/sync_skills_to_neon.py` | 132 | sync_skills_to_neon.py — Canonical Tool Mastery Engine → Neon sync. |
| `scripts/test_bridge_lifecycle.sh` | 132 | test_bridge_lifecycle.sh — Chaos test for bridge auto-recovery. |
| `scripts/test_code_view_e2e.sh` | 108 | E2E test for operator-ui Code View backend |
| `scripts/tme_quality_audit.py` | 245 | TME Quality Audit — checks content depth, not just structure. |
| `scripts/tme_staleness_sweep.py` | 86 | TME staleness sweep — summary-first report for hooks and cron. |
| `scripts/tool_mastery_author.py` | 125 | Tool Mastery author dispatcher. |
| `scripts/tool_mastery_manager.py` | 216 | Tool Mastery Manager — CLI. |
| `scripts/tool_mastery_research_dispatcher.py` | 312 | Tool Mastery research dispatcher. |
| `scripts/uninstall_windows_relay_autostart.ps1` | 73 | — |
| `scripts/update-graph` | 93 | End-to-end knowledge refresh: codebase_graph.py → build_palace.py → summarize_nodes.py |
| `scripts/user_prompt_capture.py` | 113 | UserPromptSubmit hook: capture user messages into conversation files. |
| `scripts/userscript_meet_captions.example.js` | 82 | userscript_meet_captions.example.js |
| `scripts/validate_w0_coherence_dry.py` | 239 | W0 Dry Validation with Coherence Envelope. |
| `scripts/vault_gws_credentials.py` | 144 | Vault Google Workspace OAuth material into 1Password (WP-P4-PROVIDER-TOKEN-VAULTING-001). |
| `scripts/verify_codewiki.py` | 206 | CodeWiki verifier — the single acceptance check for docs/codewiki/. |
| `scripts/verify_completion_claim.py` | 88 | Completion Claim Verifier — runs at Stop hook. |
| `scripts/verify_deploy.py` | 91 | Standalone post-deploy verification script. |
| `scripts/verify_knowledge_system.py` | 353 | verify_knowledge_system.py — Acceptance check for the EOS cognition stack. |
| `scripts/verify_pr47_cadence_learning.py` | 107 | Phase 10.3F — Cadence post-production learning check. |
| `scripts/verify_pr47_production.py` | 181 | Phase 10.3D — Production merge verification for PR #47. |
| `scripts/verify_pr47_reliability.py` | 137 | Phase 10.3E — Template + Agent Reliability Update verification. |
| `scripts/verify_relay_end_to_end.sh` | 114 | — |
| `scripts/verify_template_store.py` | 49 | Verify the runtime template store is populated and valid. |
| `scripts/verify_tool_skill.py` | 192 | verify_tool_skill.py — Tool Mastery Engine verifier / linter. |
| `scripts/waiting_on_checker.py` | 93 | WAITING_ON checker — scans emails in WAITING_ON folder |
| `scripts/watch-cognition` | 26 | Watcher wrapper for cognition/graph freshness monitoring |
| `scripts/watch_graph.py` | 526 | watch_graph.py — Near real-time file watcher for the codebase graph. |
| `scripts/week_architect.py` | 133 | Week Architect — Sunday 8pm PDT. |
| `scripts/weekly_review.py` | 243 | Weekly business review — Sunday 7pm PDT. |
| `scripts/wiki_stop_hook.py` | 169 | Stop hook: capture real conversation content to session file. |
| `scripts/windows_interactive_desktop_relay.ps1` | 1,358 | — |

## scripts/auth_monitor/ (7 files)

| Path | Lines | Purpose |
|---|---|---|
| `scripts/auth_monitor/cc_keepalive.sh` | 26 | cc_keepalive.sh — prevents OAuth token expiry during idle sessions |
| `scripts/auth_monitor/credential_coordinator.sh` | 250 | credential_coordinator.sh — single source of truth for CC credential management |
| `scripts/auth_monitor/credential_watcher.sh` | 105 | credential_watcher.sh — watches ~/.claude/.credentials.json for any change |
| `scripts/auth_monitor/health_check.sh` | 190 | health_check.sh — runs every 5 minutes, validates CC auth state |
| `scripts/auth_monitor/session_resurrector.sh` | 65 | session_resurrector.sh — checks CC session health in tmux, alerts if dead |
| `scripts/auth_monitor/setup_isolation.sh` | 73 | setup_isolation.sh — creates per-session CLAUDE_CONFIG_DIR directories |
| `scripts/auth_monitor/start_session.sh` | 65 | start_session.sh — starts a CC session with isolated credentials |

## scripts/c40b_phases/ (9 files)

| Path | Lines | Purpose |
|---|---|---|
| `scripts/c40b_phases/__init__.py` | 0 | package marker (empty) |
| `scripts/c40b_phases/campaign_context.py` | 409 | C40B Campaign Context — shared state across all phases. |
| `scripts/c40b_phases/embodiment_harness.py` | 348 | C40B Embodiment Harness — 4-dimensional runtime qualification. |
| `scripts/c40b_phases/phase1_runtime_audit.py` | 432 | C40B Phase 1 — Runtime Boundary Audit. |
| `scripts/c40b_phases/phase2_runtime_fix.py` | 218 | C40B Phase 2 — Runtime Defect Resolution. |
| `scripts/c40b_phases/phase3_operator_qualification.py` | 332 | C40B Phase 3 — Operator Runtime Qualification. |
| `scripts/c40b_phases/phase4_embodied_stress.py` | 380 | C40B Phase 4 — Embodied Stress. |
| `scripts/c40b_phases/phase5_runtime_certification.py` | 395 | C40B Phase 5 — Runtime Certification. |
| `scripts/c40b_phases/report_generator.py` | 242 | C40B Report Generator — campaign report + Discord dispatch. |

## scripts/cron/ (1 files)

| Path | Lines | Purpose |
|---|---|---|
| `scripts/cron/sync_all.cron` | 12 | crontab fragment |

## scripts/graph_hooks/ (2 files)

| Path | Lines | Purpose |
|---|---|---|
| `scripts/graph_hooks/post-merge` | 26 | post-merge — rebuild the codebase graph and palace after pulling code. |
| `scripts/graph_hooks/pre-commit` | 25 | pre-commit — warn when code changes are committed without a graph refresh. |

## scripts/hooks/ (2 files)

| Path | Lines | Purpose |
|---|---|---|
| `scripts/hooks/post-merge` | 13 | post-merge — sync all surfaces after any merge/pull on VPS |
| `scripts/hooks/pre-commit` | 61 | pre-commit — blocks commits that violate substrate integrity gates. |

## scripts/scheduled/ (7 files)

| Path | Lines | Purpose |
|---|---|---|
| `scripts/scheduled/morning_prep.sh` | 75 | EOS Morning Prep — runs 5:30am via cron |
| `scripts/scheduled/morning_prep_cp.py` | 84 | morning_prep_cp.py — Control Plane wrapper for morning_prep.sh. |
| `scripts/scheduled/nightly_consolidation.sh` | 74 | ─── Nightly Memory Consolidation ───────────────────────────────────────────── |
| `scripts/scheduled/nightly_consolidation_cp.py` | 112 | nightly_consolidation_cp.py — Control Plane wrapper for nightly_consolidation.sh. |
| `scripts/scheduled/nightly_maintenance.sh` | 206 | EOS Nightly Maintenance — runs 2:00am via cron |
| `scripts/scheduled/weekly_review.sh` | 78 | EOS Weekly Review — runs Sunday 6:00am via cron |
| `scripts/scheduled/weekly_review_cp.py` | 108 | weekly_review_cp.py — Control Plane wrapper for weekly_review.sh. |

## scripts/workers/ (1 files)

| Path | Lines | Purpose |
|---|---|---|
| `scripts/workers/discord_approval_worker.py` | 235 | discord_approval_worker.py — tail notifications.jsonl, post to Discord. |
