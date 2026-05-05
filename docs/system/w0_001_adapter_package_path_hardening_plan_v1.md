# W0-001 Adapter Package Path Hardening Plan

**Version:** 1.0
**Date:** 2026-05-05
**Phase:** 96.7B/96.7C

## Prioritized Work Orders

### Priority 1 — Can Be Done Now

| # | Work Order | Package | Path | Current | Target | Required Work |
|---|------------|---------|------|---------|--------|---------------|
| 1 | WO-GWS-API-001 | google_workspace | API tab-aware | complete (impl) | 100% mature | Formalize adapter package, governance policy, no-secret policy, contract mapping, validation tests, auth profile |
| 2 | WO-CC-CLI-001 | claude_code | CLI | working | 100% mature | Create adapter package, formalize mastery pack, governance, tests |
| 3 | WO-SHELL-001 | shell_bash | CLI | working | 100% mature | Create adapter package, mastery, governance, tests |
| 4 | WO-PYTHON-001 | python | Runtime | working | 100% mature | Create adapter package, mastery, governance, tests |
| 5 | WO-PYTEST-001 | pytest | Runtime | working | 100% mature | Create adapter package, mastery, governance, tests |

### Priority 2 — Requires External Setup/Approval

| # | Work Order | Package | Path | Blocker | Required |
|---|------------|---------|------|---------|----------|
| 6 | WO-GWS-CU-001 | google_workspace | Native CU | CU infrastructure | Tab detection, tab navigation, body extraction, scrolling/end detection, per-tab provenance, API parity validation |
| 7 | WO-GWS-BROWSER-001 | google_workspace | Browser automation | Founder/security approval | Approval, connector, governance |

### Priority 3 — Future Candidates (tracked, not blocking)

| # | Work Order | Package | Path | Status | Required When Activated |
|---|------------|---------|------|--------|------------------------|
| 8 | WO-GWS-SDK-001 | google_workspace | SDK extractor | not_implemented | Official SDK, includeTabsContent, parity tests |
| 9 | WO-GWS-CLI-001 | google_workspace | CLI direct | not_implemented | Direct REST/curl, includeTabsContent, parity tests |
| 10 | WO-GWS-MCP-001 | google_workspace | MCP API connector | not_implemented | MCP tool discovery, tab support, governance, parity tests |
| 11 | WO-GWS-EXPORT-001 | google_workspace | Local export/archive | not_implemented | Export approval, tab preservation, parser, parity tests |

### Conditional Work Orders

| # | Work Order | Condition |
|---|------------|-----------|
| 12 | WO-GIT-001 | Only if commit operations requested |
| 13 | WO-TMUX-001 | Only if active tmux runtime |
| 14 | WO-VPS-001 | VPS/WSL runtime formalization |

## Dependencies

```
WO-GWS-API-001 (no deps — can start immediately)
  └─ WO-GWS-CU-001 (depends on CU infrastructure)
       └─ WO-GWS-CU-001 parity tests (depends on API baseline)
WO-CC-CLI-001 (no deps)
WO-SHELL-001 (no deps)
WO-PYTHON-001 (no deps)
WO-PYTEST-001 (no deps)
WO-GWS-BROWSER-001 (depends on founder approval)
WO-GWS-SDK-001 (no hard deps, candidate)
WO-GWS-MCP-001 (depends on MCP server discovery)
WO-GWS-EXPORT-001 (depends on export approval)
```

## Founder Approvals Required

1. **Browser automation path** — requires explicit approval before any work
2. **Local export/archive path** — requires approval before export/download
3. **MCP server discovery** — low risk, but new infrastructure

## Recommended Sequence

1. **Formalize API tab-aware path** (WO-GWS-API-001) — closest to 100%, highest impact
2. **Formalize Claude Code CLI** (WO-CC-CLI-001) — primary orchestration tool
3. **Formalize shell/Python/pytest** (WO-SHELL/PYTHON/PYTEST-001) — fast wins, simple packages
4. **Evaluate CU infrastructure** (WO-GWS-CU-001) — long lead time, start assessment
5. **Future candidates** — SDK, CLI direct, MCP per demand

## Current State → Next Gate

After Priority 1 work orders complete, the API tab-aware path would be
the first 100% mature declared path. W0-001 could then run as a
selected-path maturity test (not full package test, since CU is still
declared but immature).

To run W0-001 as a full Adapter Package maturity test, either:
- Mature CU to 100%, or
- Reclassify CU from DECLARED to FUTURE_CANDIDATE (honest but reduces scope)
