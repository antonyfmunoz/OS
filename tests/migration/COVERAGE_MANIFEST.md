# Migration Test Suite — Coverage Manifest

> Date: 2026-05-13
> Source: canonical synthesis §34 (Proven) + §35 (Partially Proven) + recent commits
> Purpose: Pin PROVEN paths as migration safety net

---

## §34 PROVEN Items — Classification

| # | Item | Classification | Test File | Reason |
|---|------|---------------|-----------|--------|
| 1 | Relay transport (Discord bridge) | SKIP | — | Requires running Discord bot + os-discord container |
| 2 | Authority gates (governance pre-execution check) | TESTABLE | test_authority_gates.py | Pure logic: classify_action + check_can_execute are deterministic |
| 3 | WorkPacket validation | TESTABLE | test_work_packet.py | Pure dataclass + validation functions, no external deps |
| 4 | VPS orchestration | SKIP | — | Infrastructure: VPS availability, tmux, systemd — not testable in pytest |
| 5 | Foreground CU ingestion pipeline (API slice) | PARTIAL | — | Requires GWS API auth + running Google Workspace session |
| 6 | Phase 75B governed spine end-to-end | PARTIAL | test_governed_spine.py | Spine requires DB for authority check; tested with mock |
| 7 | Salience pipeline (episodic → score → consolidate) | SKIP | — | No salience scoring code found in runtime/; §35 says "not yet consolidated nightly" |
| 8 | Tailscale mesh | SKIP | — | Network infrastructure, not testable in pytest |
| 9 | ttyd/Termius/code-server access paths | SKIP | — | Terminal infrastructure |
| 10 | Persistent claude tmux session | SKIP | — | Infrastructure |
| 11 | OAuth token + keepalive cron | SKIP | — | Credentials management, tested indirectly via cc_sdk |
| 12 | Remotion | SKIP | — | Subprocess/Node.js, separate repo |
| 13 | Clerk auth flow | SKIP | — | SaaS UI flow, not testable from VPS |
| 14 | Core user flow (login → portfolio → company → CC) | SKIP | — | SaaS UI flow |
| 15 | saas-dev-skill | SKIP | — | Separate repo |

## Recent Commits — Classification

| # | Commit | Classification | Test File | Reason |
|---|--------|---------------|-----------|--------|
| R1 | ingestion-orchestrator-1 (LocalFileSource) | TESTABLE | test_ingestion_local.py | Full pipeline with temp dir fixture |
| R2 | ingestion-orchestrator-2 (GWSSource) | PARTIAL | — | Requires GWS API credentials |
| R3 | decomposer-depth-upgrade (LLM extraction) | TESTABLE+LLM | test_ingestion_decomposer.py | Requires LLM call; mocked for offline |
| R4 | persist-all-observations | TESTABLE | test_ingestion_local.py | Covered by full-cycle test |
| R5 | ontology-domain-bridge (BusinessBridge) | TESTABLE | test_domain_bridge.py | Pure logic with constructed observations |
| R6 | authority-tier-on-source | TESTABLE | test_ingestion_local.py | Covered by tier propagation assertion |
| R7 | cc_sdk error-leak fix | TESTABLE | test_cc_sdk.py | Pure string matching |
| R8 | cc_sdk subprocess auth | TESTABLE | test_cc_sdk.py | Mockable /proc walk |
| R9 | cc_sdk timeout fix | TESTABLE | test_cc_sdk.py | Pure config resolution |
| R10 | reingest-text-blobs | PARTIAL | — | Requires live memory store + LLM |

## Summary

| Classification | Count |
|---------------|-------|
| TESTABLE | 8 |
| PARTIAL (needs fixtures/auth) | 3 |
| SKIP (infrastructure) | 9 |
| SKIP (separate repo) | 2 |
| SKIP (SaaS UI) | 2 |
| **Total items** | **24** |

## PROVEN-IN-NAME-ONLY Findings

| # | Item | Finding |
|---|------|---------|
| 7 | Salience pipeline | §34 claims "proven" but no salience scoring code exists in runtime/. The episodic logging may work, but scoring/consolidation are not implemented. This is a §35 item at best. |
