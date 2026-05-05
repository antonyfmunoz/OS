---
type: codebase-class
file: scripts/orchestrator.py
line: 170
generated: 2026-04-12
---

# Verifier

**File:** [[scripts-orchestrator-py]] | **Line:** 170

Pre-submit validation + post-run stability guards.

Does not run workflows itself — the WorkflowEngine has its own internal
verifier. This class is about the *orchestration* layer: is this job
well-formed, and is the system in a state where we should run it at all?

## Methods

- [[scripts-orchestrator-py-Verifier-validate_job]]`(job) → list[str]` — 
- [[scripts-orchestrator-py-Verifier-system_is_healthy]]`() → tuple[bool, str]` — Cheap liveness check before submitting work.
