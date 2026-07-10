---
type: codewiki-dir
dir: scripts
---

# `scripts/` — operational tooling, enforcement gates, and the knowledge stack

**213 files · 9,917,683 bytes · [Full file inventory](../inventory/scripts.md)**

## Purpose
`scripts/` is UMH's operational toolbox: everything that runs *around* the
running services rather than inside them. It holds the five-layer cognition
stack's builders and queriers, the pre-commit enforcement gates that mechanically
protect the architecture laws, the cron/scheduled daily-rhythm jobs, the git
hooks, the deploy/auth utilities, and a large set of one-shot operator CLIs and
campaign runners. It is not application logic — it is the machinery that keeps the
codebase, its knowledge graph, and its deployment coherent.

## How it fits
`scripts/` sits outside the four-layer stack
(projections → transports → adapters → substrate). Scripts freely `sys.path.insert(0, "/opt/OS")`
and import from any layer — they are consumers of the runtime, not part of the
dependency graph the [architecture layer law](../../../.claude/rules/architecture-layers.md)
governs. The relationship runs the other way: the **pre-commit gates in this
directory are what enforce that law** on every commit. `scripts/` is exempt from
the [CPU Gate Law](../../../CLAUDE.md) raw-subprocess ban (the gate scripts scan
`substrate/`, `adapters/`, `transports/`, `services/`, never themselves), but its
scheduled jobs are wrapped by `cron-run` (CPU Gate defense layer 4).

## Structure

| Subdir | Files | Role |
|---|---|---|
| `scripts/` (root) | ~184 | The bulk: gates, knowledge stack, CLIs, cron scripts, git hooks, campaign runners |
| `scripts/auth_monitor/` | 7 | Claude Code OAuth credential lifecycle — keepalive, watcher, health check, per-session isolation, session resurrection |
| `scripts/c40b_phases/` | 9 | C40B Runtime Embodiment Campaign phase runners (audit → fix → qualification → stress → certification + report) |
| `scripts/cron/` | 1 | `sync_all.cron` crontab fragment |
| `scripts/graph_hooks/` | 2 | `post-merge` (rebuild graph+palace after pull) and `pre-commit` (warn on code commit without graph refresh) |
| `scripts/hooks/` | 2 | Canonical `pre-commit` (substrate integrity gates) and `post-merge` (sync surfaces) git hooks |
| `scripts/scheduled/` | 7 | Daily-rhythm cron scripts (morning prep, nightly consolidation, nightly maintenance, weekly review) with Control-Plane `*_cp.py` wrappers |
| `scripts/workers/` | 1 | `discord_approval_worker.py` — tails `notifications.jsonl`, posts approvals to Discord |

## Key components

### The knowledge / cognition stack
This is the machinery behind the mandatory retrieval hierarchy
(Palace → Graph → Summaries → Raw → Logs) declared in
[CLAUDE.md](../../../CLAUDE.md). Load order and rebuild:

- `codebase_graph.py` (1,234 lines) — the persistent codebase knowledge graph
  builder: parses the tree into nodes (files/classes/functions) with imports,
  deps, and a call graph.
- `query_graph.py` (328 lines) — the retrieval layer. `deps`, `dependents`,
  `entry-points`, `critical`, `centrality`, `search`, `stats`. This is the tool
  CLAUDE.md mandates you run *before* reading any Python/JS/TS/SQL file.
- `summarize_nodes.py` (150 lines) — append-only one-line summaries for every
  graph node (`data/node_summaries.json`), the third tier of the hierarchy.
- `build_palace.py` (484 lines) — generates the memory palace
  (`knowledge/palace/`) from the graph — the first tier.
- `update-graph` (93 lines) — the single end-to-end refresh:
  `codebase_graph.py → build_palace.py → summarize_nodes.py`. Flags:
  `--json-only`, `--graph-only`, `--stats`, `--module <m>`, `--with-overlay`.
- `session_bootstrap.py` (187 lines) — mandatory context load at session start;
  prints every layer's status and exits non-zero if the graph is stale.
- `verify_knowledge_system.py` (353 lines) — the single acceptance check that
  every cognition layer is present, fresh, and queryable (exit 0 = all pass).
- `incremental_graph.py` (772) + `watch_graph.py` (526) + `watch-cognition` —
  dirty-set incremental updates and a near-real-time file watcher.
- `run_graphify.py` (526) + `merge_graphs.py` (341) — the Graphify enrichment
  overlay adapter and its merge into the derived graph.
- `generate_codebase_report.py` (1,119) — exhaustive visual codebase report.
- `generate_codewiki.py` (855) + `verify_codewiki.py` (206) — **NEW**: the
  generators for *this* CodeWiki. They build the deterministic inventory/manifest
  layer that the narrative pages (like this one) sit on top of. They exist in the
  wiki worktree; they are not yet in the live `/opt/OS` checkout.

### Pre-commit enforcement gates
`scripts/pre-commit` (40 lines) is the **canonical gate runner** — the single
source of truth. It runs 14 numbered gates in order; `scripts/install_hooks.sh`
installs the identical set into `.git/hooks/pre-commit`. Each blocks a class of
architectural drift:

| Gate | Script | Blocks |
|---|---|---|
| 1 Type Coherence | `check_type_divergence.py` (386) | new types diverging from `substrate/canonical_types.py` |
| 2 Instance Context | `check_instance_leak.py` (265) | hardcoded instance-specific values in `substrate/` |
| 3 Projection Boundary | `check_projection_leak.py` (262) | projection names (EOS/CreatorOS/LyfeOS) in substrate code |
| 4 Dependency Direction | `check_dependency_direction.py` (401) | upward/sideways imports across the four layers |
| 5 CPU Gate | `check_cpu_gate.py` (150) | raw `subprocess` in `substrate/`,`adapters/`,`transports/`,`services/` |
| 6 Ungoverned Mutations | `check_ungoverned_mutations.py` (228) | mutation endpoints bypassing `governed_mutation()` |
| 7 Credential Injection | `check_credential_injection.py` (172) | plaintext credential patterns in subprocess/SSH calls |
| 8 Secret Patterns | `check_secret_patterns.py` (92) | commits containing secret-shaped strings |
| 9 Mesh Relay Firewall | `check_mesh_relay_firewall.py` (144) | unsafe mesh relay firewall state |
| 10 Pytest Collection | `check_pytest_collection.py` (142) | commits that break pytest collection |
| 11 Ontology Layers | `check_ontology_layers.py` (306) | L3 domain contamination in L2 substrate ontology |
| 12 Projection Registry Reads | `check_projection_registry_reads.py` (204) | >1 reader of `data/umh/projection_registry.json` |
| 13 Ontology Home Map | `check_ontology_homes.py` (276) | a new ontology/reality/domain home appearing silently |
| 14 Voice Runtime Divergence | `check_voice_runtime_divergence.py` (455) | voice-diag beacon removal + awaited audio-unlock on the voice-start path |

Two `check_*.py` scripts are **not** pre-commit gates:
`check_stop_condition.py` (Stop-hook handler) and `check_skill_staleness.py`
(TME staleness audit). The older `scripts/hooks/pre-commit` (61 lines) still
lists only Gates 1-5 in its header comment — the canonical `scripts/pre-commit`
runner is the current, complete list; treat the `hooks/` copy's comment as stale.

### Cron / scheduled — the daily rhythm
`cron-run` (59 lines) is **CPU Gate defense layer 4**: it wraps every scheduled
Python job with flock (no overlapping runs), nice/ionice (lowest priority),
`timeout` (kills after 4 min; cron fires every 5), and a load gate (skips
entirely if the system is already overloaded, load ≥ 2.0/core). Lock files live
in root-only `/run/umh-cron/`. `scripts/scheduled/` holds the actual jobs
(`morning_prep.sh` 5:30am, `nightly_consolidation.sh`, `nightly_maintenance.sh`
2:00am, `weekly_review.sh` Sunday) each with a Control-Plane `*_cp.py` wrapper.
Many root scripts are also cron-fired operator loops: `morning_intel.py` (5:45am),
`call_prep.py`, `midday_checkin.py` (12:30pm), `eod_sync.py` (6pm),
`week_architect.py` (Sunday 8pm), `weekly_review.py` (Sunday 7pm),
`notion_sync_poller.py` (every 15 min).

### Deploy / auth utilities
- `refresh_fly_token.py` (57) — refreshes the Fly.io deploy token from the
  1Password org token; the canonical fix for expired-token deploy failures.
- `op_run.sh` (99) — canonical UMH 1Password Secret Runtime wrapper.
- `rotate_secrets.sh` (107) + `rotate_jsonl.py` (60) — 30-day secret rotation and
  JSONL store rotation.
- `run_prod.sh`, `run_ui.sh`, `verify_deploy.py` (91), `device_sync.py`
  (post-commit: push to GitHub, pull on Beast), `sync_all.sh` (262, cross-device
  git fast-forward).
- `scripts/auth_monitor/` — Claude Code OAuth keepalive/watcher/health/isolation,
  the machinery that keeps the `cc_sdk` subprocess auth token alive.

### Campaign runners
`scripts/c40b_phases/` holds the C40B Runtime Embodiment Campaign
(`campaign_context.py`, `embodiment_harness.py`, five phase runners, and
`report_generator.py`). Root-level campaign harnesses include the C29 Harness
Superiority runners (`c29_class_b_runner.py`, `c29_thesis_runner.py` and their
Beast launchers) and `run_qualification.py` (1,148 — the adaptive,
convergence-driven qualification runner). Per the roadmap, campaign engineering
(C34–C40B) is **retired** — these runners are historical/proof, not live runtime.

### Git hooks
`scripts/hooks/` (canonical `pre-commit` gate runner header + `post-merge` sync),
`scripts/graph_hooks/` (`pre-commit` warns on graph staleness, `post-merge`
rebuilds graph+palace after pull). Installers: `install_hooks.sh`,
`install_graph_hooks.sh`, `install_divergence_gate.sh`, `install_sync_automation.sh`.

### Hooks (Claude Code lifecycle)
Distinct from git hooks: `session_start_context.py` (SessionStart),
`subagent_start_context.py` (SubagentStart), `pre_tool_use_log.py` (PreToolUse),
`memory_instant_sync.py` (PostToolUse), `user_prompt_capture.py`
(UserPromptSubmit), `auto_report_dispatch.py` / `check_stop_condition.py` /
`verify_completion_claim.py` / `wiki_stop_hook.py` (Stop),
`permission_notify.py` (PermissionRequest).

### workers/
`scripts/workers/discord_approval_worker.py` (235) tails `notifications.jsonl`
and posts approval requests to Discord — the human-in-the-loop surface for
governed actions requiring approval.

## Data & state
- Reads/writes the knowledge stack: `data/codebase_graph.json`,
  `data/node_summaries.json`, `knowledge/palace/`, the Obsidian graph vault.
- `notion_tasks_sync_state.json` — sync-state checkpoint for the Notion poller.
- `notifications.jsonl` — read by the Discord approval worker.
- `/run/umh-cron/` — cron-run flock lock files (root-only tmpfs).
- Env/secrets: `*.tpl` op-run templates (`.env.beast.tpl`, `.env.gws.tpl`),
  Fly token and 1Password vaults for deploy/auth.
- `agent_executor.log` and `agent_task_executor.py`'s runtime log currently live
  in `scripts/` rather than `logs/` — a placement nit noted in the inventory.

## Gotchas
- **`scripts/pre-commit` is the canonical gate list, not `scripts/hooks/pre-commit`.**
  The latter's comment header only mentions Gates 1-5 and is stale; the real
  runner enforces all 14. When adding a gate, edit `scripts/pre-commit` and
  `install_hooks.sh` together (the runner says so explicitly).
- **`cron-run` skips silently under load.** A scheduled job that "didn't run" may
  have been gated out because system load was ≥ 2.0/core. That is by design (CPU
  Gate Law — Hostinger throttled the VPS for a week after a runaway process). Check
  the load gate before assuming a cron job is broken.
- **`generate_codewiki.py` / `verify_codewiki.py` exist only in the wiki
  worktree**, not in `/opt/OS`. They are this wiki's own generators and are new.
- **Campaign runners (C29, C40B, `run_qualification.py`) are retired**, not live
  runtime. Do not treat them as production paths.
- Scripts are the one place raw `subprocess` is allowed (they are exempt from the
  CPU Gate ban), but scheduled scripts should still run through `cron-run` to keep
  the load gate in the path.

## See also
- [`tests/` — the test suite](tests.md) (gate regression tests live there)
- [`substrate/` — the platform the gates protect](substrate.md)
- [Architecture](../architecture.md) · [Conventions](../conventions.md)
- [Services & runtime](../services-runtime.md) · [`services/`](services.md)
- [Full file inventory](../inventory/scripts.md)
