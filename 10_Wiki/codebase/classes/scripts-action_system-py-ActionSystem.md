---
type: codebase-class
file: scripts/action_system.py
line: 231
generated: 2026-04-12
---

# ActionSystem

**File:** [[scripts-action_system-py]] | **Line:** 231

Single orchestration surface for propose → assess → execute → log.

Environment-aware: pass `env=make_sandbox(...)` to redirect every
file write, log append, and snapshot into an isolated tree. When
`env` is None (the default), the system runs against production.

## Methods

- [[scripts-action_system-py-ActionSystem-__init__]]`() → None` — Args:
- [[scripts-action_system-py-ActionSystem-_resolve_target]]`(target) → Path` — Translate an action target into the current env's workspace.
- [[scripts-action_system-py-ActionSystem-_graph]]`() → GraphQuery` — 
- [[scripts-action_system-py-ActionSystem-_critical_hub_set]]`() → set[str]` — 
- [[scripts-action_system-py-ActionSystem-propose]]`() → Action` — Create an Action, populate impact + risk, but do NOT execute.
- [[scripts-action_system-py-ActionSystem-assess_impact]]`(action) → Impact` — Use the graph to describe the blast radius of this action.
- [[scripts-action_system-py-ActionSystem-evaluate_risk]]`(action) → RiskLevel` — Deterministic risk assignment. No LLM, no heuristics that
- [[scripts-action_system-py-ActionSystem-execute]]`(action) → ActionResult` — Run the approval gate, then dispatch to the type-specific
- [[scripts-action_system-py-ActionSystem-_security_check]]`(action) → 'object | None'` — Translate an Action into a SecurityContext.authorize_action call.
- [[scripts-action_system-py-ActionSystem-_advisor_check]]`(action) → dict[str, Any] | None` — Ask the advisor to validate a HIGH/CRITICAL action.
- [[scripts-action_system-py-ActionSystem-_exec_query_graph]]`(action) → ActionResult` — Read-only graph lookup. payload.query must be one of:
- [[scripts-action_system-py-ActionSystem-_exec_edit_file]]`(action) → ActionResult` — Whole-file rewrite with snapshot. Payload must contain
- [[scripts-action_system-py-ActionSystem-_exec_write_file]]`(action) → ActionResult` — Create a new file (or overwrite). If the file exists, snapshots
- [[scripts-action_system-py-ActionSystem-_exec_delete_file]]`(action) → ActionResult` — Soft delete: move to snapshot dir instead of actually unlinking.
- [[scripts-action_system-py-ActionSystem-_exec_run_script]]`(action) → ActionResult` — Run a Python script by path. payload.args is optional list[str].
- [[scripts-action_system-py-ActionSystem-_exec_run_command]]`(action) → ActionResult` — Run a shell command. payload.command is required.
- [[scripts-action_system-py-ActionSystem-rollback]]`(action_id) → ActionResult` — Undo an earlier file-mutating action by restoring its snapshot.
- [[scripts-action_system-py-ActionSystem-_snapshot_file]]`(action_id, path) → Path` — 
- [[scripts-action_system-py-ActionSystem-_resolve_content]]`(payload) → str` — 
- [[scripts-action_system-py-ActionSystem-_preview]]`(action) → str` — Text preview used by dry-run.
- [[scripts-action_system-py-ActionSystem-_refresh_graph]]`(paths) → dict[str, Any]` — Best-effort incremental refresh. Never raises — the action
- [[scripts-action_system-py-ActionSystem-_emit_log]]`(action) → None` — 
- [[scripts-action_system-py-ActionSystem-_append_jsonl]]`(record) → None` — 
- [[scripts-action_system-py-ActionSystem-_emit_neon]]`(record) → None` — Best-effort Neon audit. Never blocks or raises.
- [[scripts-action_system-py-ActionSystem-history]]`() → list[dict[str, Any]]` — 
