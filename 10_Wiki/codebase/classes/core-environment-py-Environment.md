---
type: codebase-class
file: core/environment.py
line: 97
generated: 2026-04-12
---

# Environment

**File:** [[core-environment-py]] | **Line:** 97

Encapsulates all path + policy decisions for an execution context.

The production environment is a singleton-ish object (call
`Environment.production()` to get one). Sandbox and playground
environments are instantiated per run via `make_sandbox()` /
...

## Methods

- [[core-environment-py-Environment-is_production]]`() → bool` — 
- [[core-environment-py-Environment-is_sandbox]]`() → bool` — 
- [[core-environment-py-Environment-label]]`() → str` — 
- [[core-environment-py-Environment-action_log_path]]`() → Path` — 
- [[core-environment-py-Environment-workflow_log_path]]`() → Path` — 
- [[core-environment-py-Environment-orchestrator_log_path]]`() → Path` — 
- [[core-environment-py-Environment-harness_log_path]]`() → Path` — 
- [[core-environment-py-Environment-optimizer_proposals_path]]`() → Path` — 
- [[core-environment-py-Environment-sandbox_manifest_path]]`() → Path` — 
- [[core-environment-py-Environment-workflow_state_dir]]`() → Path` — 
- [[core-environment-py-Environment-agent_state_dir]]`() → Path` — 
- [[core-environment-py-Environment-resolve]]`(target) → Path` — Translate a repo-relative or absolute path into this env's tree.
- [[core-environment-py-Environment-_to_rel]]`(p) → Path` — Convert any caller-supplied path into a repo-relative Path.
- [[core-environment-py-Environment-ensure_copied]]`(target) → Path` — Copy-on-write: if a file exists in production but not yet in
- [[core-environment-py-Environment-read_file]]`(target) → bytes` — Read with read-through: if the file isn't in the workspace,
- [[core-environment-py-Environment-guard_write]]`(target) → None` — Raise PermissionError if this environment is not allowed to
- [[core-environment-py-Environment-provision]]`() → None` — Create the directory tree. Idempotent.
- [[core-environment-py-Environment-cleanup]]`() → None` — Remove the entire env tree. No-op for production.
- [[core-environment-py-Environment-__enter__]]`() → 'Environment'` — 
- [[core-environment-py-Environment-__exit__]]`(exc_type, exc, tb) → None` — 
- [[core-environment-py-Environment-to_dict]]`() → dict` — 
- [[core-environment-py-Environment-production]]`() → 'Environment'` — The real-thing environment. Writes land in /opt/OS.

## Decorators

- `@dataclass`
