# MIGRATION-TEST-SUITE — Audit Report

> Date: 2026-05-13
> Source: canonical synthesis §34 (Proven) + §35 (Partially Proven) + recent commits
> Output: /opt/OS/tests/migration/

---

## Summary

| Metric | Value |
|--------|-------|
| Test files | 6 |
| Total tests | 78 |
| Offline tests | 77 |
| Live LLM tests | 1 |
| Pass rate (offline) | 77/77 (100%) |
| Duration (offline) | 1.56s |

---

## Coverage Classification

| Classification | Count |
|---------------|-------|
| TESTABLE (pinned) | 8 |
| PARTIAL (needs fixtures/auth) | 3 |
| SKIP (infrastructure) | 9 |
| SKIP (separate repo) | 2 |
| SKIP (SaaS UI) | 2 |
| **Total §34 + recent items** | **24** |

---

## Per-File Results

| File | Tests | Passed | Category |
|------|-------|--------|----------|
| test_authority_gates.py | 15 | 15 | §34 authority gates |
| test_work_packet.py | 14 | 14 | §34 WorkPacket validation |
| test_governed_spine.py | 5 | 5 | §34 Phase 75B spine |
| test_ingestion_local.py | 10 | 10 | Recent: LocalFileSource + persist + tier |
| test_ingestion_decomposer.py | 4 | 3+1 | Recent: decomposer (3 offline + 1 LLM) |
| test_domain_bridge.py | 11 | 11 | Recent: BusinessBridge |
| test_cc_sdk.py | 19 | 19 | Recent: error-leak + OAuth + timeout |

---

## SKIPPED Items (with reason)

| # | Item | Reason |
|---|------|--------|
| 1 | Relay transport (Discord) | Requires running Discord bot container |
| 2 | VPS orchestration | Infrastructure (systemd/tmux), not testable in pytest |
| 3 | Foreground CU ingestion | Requires GWS API auth + running session |
| 4 | Tailscale mesh | Network infrastructure |
| 5 | ttyd/Termius/code-server | Terminal infrastructure |
| 6 | Persistent claude tmux | Infrastructure |
| 7 | OAuth token + keepalive cron | Credential management (tested indirectly via cc_sdk) |
| 8 | Remotion | Node.js subprocess, separate repo |
| 9 | Clerk auth flow | SaaS UI flow |
| 10 | Core user flow | SaaS UI flow |
| 11 | saas-dev-skill | Separate repo |

---

## PROVEN-IN-NAME-ONLY Findings

| # | Item | Finding |
|---|------|---------|
| 1 | Salience pipeline | §34 claims "Salience pipeline for EOS memory (episodic logging, salience scoring, consolidation, promotion thresholds, Neon metadata)" is PROVEN. However: no `salience_score` function, no `SalienceScore` class, no `episodic` scoring logic exists in `runtime/`. The memory store writes episodic entries, but scoring and consolidation are not implemented. §35 confirms: "Cross-session salience (logged but not yet consolidated nightly)." This item should be reclassified from §34 to §35. |

---

## Makefile Targets

```
make test-migration          # all tests (including LLM)
make test-migration-offline  # offline subset (fast, no tokens)
```

---

## Recommendation

**Migration can proceed** with these tests as the safety net. The 77 offline
tests cover the import paths, data contracts, governance logic, ingestion
pipeline, domain bridge, and cc_sdk hardening — the critical paths that
would break silently if files moved.

**Before migration starts:**
1. Reclassify salience pipeline from §34 to §35 in the synthesis doc
2. Consider adding tests for GWSSource (requires auth fixture)
3. Run `make test-migration` (with LLM) periodically to catch cc_sdk regressions

---

## Chat Summary

- Tests written: 78 across 6 files
- Pass rate: 77/77 offline, 1 LLM test deselected
- Offline subset: 77 tests in 1.56s
- SKIPPED with reason: 11 items (infrastructure, separate repos, SaaS UI)
- PROVEN-IN-NAME-ONLY: 1 (salience pipeline — scoring/consolidation not implemented)
