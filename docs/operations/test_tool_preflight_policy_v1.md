# Test Tool Preflight Policy

**Version:** 1.0
**Date:** 2026-05-05
**Scope:** UMH substrate — all platform consumers

## Core Rule

Before a test or ingestion run, UMH must inventory all tools, access
paths, and runtimes required for the task and verify execution readiness
for each.

## Preflight Process

1. Detect all tools required for the task
2. Look up adapter packages for each tool
3. Evaluate execution readiness for each package
4. Classify tools as: usable, blocked, waived, or missing
5. Produce a preflight report with final status

## Final Status Values

| Status | Meaning |
|--------|---------|
| READY | All required tools have execution-ready packages |
| BLOCKED | One or more required tools cannot execute |
| PARTIAL | Some tools ready, some blocked |
| WAIVED | Execution allowed via founder waiver |
| NEEDS_MATURITY_BUILDOUT | Packages need to be created first |

## W0-001 Required Tools

- claude_code: orchestration
- shell_bash: command execution
- python: validation/test execution
- pytest: test framework
- git: only if commit requested
- tmux: only if active runtime
- google_workspace: source system
- google_docs: tab-aware extraction
- google_drive: inventory/metadata

## Rule

If a tool is not used in the actual task, it does not need execution
readiness for that task. If it is used, it must be 100% mature.

## Module

`core/adapter_package_manager/test_tool_preflight.py`
