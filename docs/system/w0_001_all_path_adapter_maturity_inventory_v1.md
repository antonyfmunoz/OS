# W0-001 All-Path Adapter Maturity Inventory

**Version:** 1.0
**Date:** 2026-05-05
**Phase:** 96.7B/96.7C

## Google Workspace Path Inventory

### Declared Paths (must mature to 100%)

| # | Path | Type | Status | Maturity % | Blocks Full Maturity | Key Gaps |
|---|------|------|--------|------------|---------------------|----------|
| 1 | API tab-aware extractor | API | complete (impl) | 14.3% | YES | Missing adapter package formalization, governance, no-secret, contract mapping, tests, auth formalization |
| 2 | Native Computer Use | CU | partial | 0% | YES | Foreground ownership, missing tab detection/navigation/body extraction/scrolling/provenance/parity/governance/tests |

### Future Candidate Paths (tracked, do not count toward maturity)

| # | Path | Type | Status | Notes |
|---|------|------|--------|-------|
| 3 | SDK tab-aware extractor | SDK | not_implemented | Official client library possible |
| 4 | CLI direct protocol | CLI | not_implemented | Must use includeTabsContent=true |
| 5 | CLI vendor/native | CLI | unknown | Must prove tab support |
| 6 | MCP API connector | MCP | not_implemented | Must prove tab support |
| 7 | MCP vendor/tool wrapper | MCP | unknown | Must prove all-tabs support |
| 8 | MCP local file connector | MCP | not_implemented | Requires export policy |
| 9 | MCP computer-use controller | MCP | not_implemented | Maps to CU requirements |
| 10 | Browser extension | Browser | not_implemented | Future candidate |
| 11 | Local export/archive parser | Export | not_implemented | Requires export approval |
| 12 | Local sync parser | Sync | not_implemented | Requires sync policy |
| 13 | File parser | Parser | not_implemented | For exported DOCX/PDF/MD/HTML |

### Excluded Paths (not part of package)

| # | Path | Reason |
|---|------|--------|
| 14 | CLI interface wrapper | Wraps API — not independent |
| 15 | MCP interface wrapper | Not independent |

### Requires Approval Paths

| # | Path | Status | Approval Needed |
|---|------|--------|----------------|
| 16 | Browser automation | blocked | Separate security/founder approval |

## W0-001 Operational Tool Inventory

| Tool | Path | Declaration | Impl Status | Adapter Package | Maturity % | Gaps |
|------|------|-------------|-------------|-----------------|------------|------|
| Claude Code | CLI | DECLARED | complete (working) | MISSING | 0% | No formal package, mastery, governance, tests |
| Shell/Bash | CLI | DECLARED | complete (working) | MISSING | 0% | No formal package, mastery, governance, tests |
| Python | Runtime | DECLARED | complete (working) | MISSING | 0% | No formal package, mastery, governance, tests |
| pytest | Runtime | DECLARED | complete (working) | MISSING | 0% | No formal package, mastery, governance, tests |
| Git | CLI | DECLARED | complete (working) | MISSING | 0% | No formal package (only needed if commit requested) |
| tmux | CLI | DECLARED | complete (working) | MISSING | 0% | No formal package (only needed if active runtime) |
| VPS/WSL | Runtime | DECLARED | complete (working) | MISSING | 0% | No formal package, mastery, governance, tests |

## Package Maturity Summary

### Google Workspace Package
- **Declared paths:** 2 (API tab-aware, Native CU)
- **Fully mature paths:** 0
- **Package maturity:** 0%
- **Target:** 100%
- **Can run full adapter test:** NO

### Operational Tools
- **Tools inventoried:** 7
- **Formal adapter packages:** 0
- **Maturity:** 0%
- **Target:** 100%

## Honest Assessment

No tool currently has a 100% mature Adapter Package. The API tab-aware
extractor is the closest to maturity (working implementation + Tool
Mastery Pack), but it lacks formalization of the remaining 8 adapter
layers. All operational tools function correctly but have zero formal
adapter infrastructure.
