---
type: codebase-class
file: core/observability.py
line: 108
generated: 2026-04-12
---

# Observability

**File:** [[core-observability-py]] | **Line:** 108

Pure reader over logs + state files.

By default reads production logs under /opt/OS/data. To point at a
sandbox or playground, pass ``env_root=`` (the sandbox tree root, e.g.
``/opt/OS/data/sandboxes/my-run``) or build custom ``paths``.
...

## Methods

- [[core-observability-py-Observability-__init__]]`() → None` — 
- [[core-observability-py-Observability-_filter_env]]`(rows) → list[dict[str, Any]]` — 
- [[core-observability-py-Observability-snapshot]]`() → dict[str, Any]` — A single dict summarizing the whole system.
- [[core-observability-py-Observability-recent_workflows]]`(n) → list[dict[str, Any]]` — 
- [[core-observability-py-Observability-recent_actions]]`(n) → list[dict[str, Any]]` — 
- [[core-observability-py-Observability-recent_harness_calls]]`(n) → list[dict[str, Any]]` — 
- [[core-observability-py-Observability-recent_failures]]`(n) → list[dict[str, Any]]` — 
- [[core-observability-py-Observability-agent_status]]`() → list[dict[str, Any]]` — Read each persistent agent's state file.
- [[core-observability-py-Observability-orchestrator_status]]`() → dict[str, Any]` — 
- [[core-observability-py-Observability-optimizer_proposals]]`() → list[dict[str, Any]]` — 
- [[core-observability-py-Observability-advisor_stats]]`() → dict[str, Any]` — Compute advisor usage stats from the advisor log.
- [[core-observability-py-Observability-recent_advisor_calls]]`(n) → list[dict[str, Any]]` — Return the last N advisor log entries.
- [[core-observability-py-Observability-sandbox_runs]]`() → list[dict[str, Any]]` — List every sandbox tree under data/sandboxes/ with a summary.
- [[core-observability-py-Observability-playground_runs]]`() → list[dict[str, Any]]` — List every ephemeral playground tree still on disk.
- [[core-observability-py-Observability-compare_to_production]]`() → dict[str, Any]` — Compare *this* observability view to production.
