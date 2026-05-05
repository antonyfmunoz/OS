# W0-001 Test Tool Preflight Readiness

**Version:** 1.0
**Date:** 2026-05-05
**Phase:** 96.7B/96.7C

## Purpose

Evaluate whether the W0-001 ingestion test can run as a full Adapter
Package maturity test, based on the current state of all required
tool packages.

## Google Workspace Paths

| Path | Status | Usable for W0-001 | Reason |
|------|--------|-------------------|--------|
| API tab-aware extractor | COMPLETE (implementation) | NOT READY | Missing formal adapter package, governance, tests, contract mapping |
| SDK tab-aware extractor | NOT_IMPLEMENTED | NOT READY | Not implemented |
| CLI interface wrapper | COMPLETE (implementation) | EXCLUDED | Wraps API — not independent |
| CLI direct protocol | NOT_IMPLEMENTED | NOT READY | Not implemented |
| CLI vendor/native | UNKNOWN | NOT READY | Unknown capability |
| MCP API connector | NOT_IMPLEMENTED | NOT READY | Not implemented, not discovered |
| MCP computer-use controller | NOT_IMPLEMENTED | NOT READY | Not implemented |
| Native Computer Use | PARTIAL | NOT READY | Foreground ownership blocks extraction |
| Browser automation | BLOCKED | NOT READY | Requires separate approval |
| Browser extension | NOT_IMPLEMENTED | NOT READY | Future candidate |
| Local export/archive | NOT_IMPLEMENTED | NOT READY | Requires export approval |
| Local sync parser | NOT_IMPLEMENTED | NOT READY | Requires sync policy |
| File parser | NOT_IMPLEMENTED | NOT READY | Future candidate |

## W0-001 Operational Tools

| Tool | Implementation Status | Adapter Package Status | Ready |
|------|----------------------|----------------------|-------|
| Claude Code CLI | Working | NO FORMAL PACKAGE | NOT READY |
| Shell/Bash | Working | NO FORMAL PACKAGE | NOT READY |
| Python runtime | Working | NO FORMAL PACKAGE | NOT READY |
| pytest framework | Working | NO FORMAL PACKAGE | NOT READY |
| Git | Working | NO FORMAL PACKAGE | NOT READY (only needed if commit requested) |
| tmux | Working | NO FORMAL PACKAGE | NOT READY (only needed if active runtime) |
| VPS/WSL runtime | Working | NO FORMAL PACKAGE | NOT READY |

## Assessment

**Can W0-001 run as a full Adapter Package maturity test?** NO.

No tool involved in W0-001 has a formally complete Adapter Package.
The API tab-aware extractor has a working implementation and a Tool
Mastery Pack (google_docs_mastery_pack), but it lacks:
- Formal adapter package wrapper
- Governance policy
- No-secret policy
- Contract mapping
- Validation tests formalized as adapter tests
- Auth profile formalization

The operational tools (Claude Code, shell, Python, pytest, git, tmux)
all function correctly but have no formal Adapter Packages.

## What Must Happen Before W0-001 Can Run as Full Adapter Package Test

1. Create formal Adapter Package for Google Workspace API tab-aware path
2. Create formal Adapter Packages for operational tools (at least Claude Code, shell, Python, pytest)
3. Complete governance/no-secret/contract/test layers for API path
4. Formalize auth profiles
5. Run maturity enforcement gate — must return EXECUTION_READY

## What W0-001 CAN Do Now

W0-001 can run as a **selected-path functional test** using the API
tab-aware extractor with a founder waiver. This proves the extraction
works but does NOT constitute a full Adapter Package maturity test.
