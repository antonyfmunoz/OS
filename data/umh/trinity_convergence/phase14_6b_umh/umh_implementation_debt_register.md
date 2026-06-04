# UMH Implementation Debt Register

Phase: 14.6B-UMH | Status: DRAFT | Provenance: CODE_RESOLVED_CURRENT_TRUTH + INFERRED_PROFESSIONAL_GAP

---

## Naming Debt

| # | Item | Location | Effort | Priority |
|---|------|----------|--------|----------|
| N1 | README.md says "Universal Mastery Hierarchy" | README.md line 1 | LOW | P0 |
| N2 | PHILOSOPHY.md uses EntrepreneurOS as system name | PHILOSOPHY.md (entire file) | MEDIUM | P0 |
| N3 | cloud.md says "Universal Mastery Hierarchy" | cloud.md | LOW | P0 |
| N4 | EntrepreneurOSGateway backward compat alias | gateway.py:1927 | LOW | P1 |
| N5 | EntrepreneurOSContext backward compat alias | context.py:59 | LOW | P1 |
| N6 | EntrepreneurOSOrchestrator backward compat alias | orchestrator.py:1910 | LOW | P1 |
| N7 | EOS_ROUTER_* env vars in model_router.py | model_router.py:908,912,1083,1086 | MEDIUM | P1 |
| N8 | eos_network in docker-compose.yml | docker-compose.yml | LOW | P1 |
| N9 | EOS naming in discord_bot.py | discord_bot.py | MEDIUM | P1 |
| N10 | EOS Memory Palace title | knowledge/palace/index.md | LOW | P2 |
| N11 | 503 EntrepreneurOS occurrences across codebase | Various | HIGH | P2 |
| N12 | 22 AgentOS occurrences across codebase | Various | LOW | P2 |
| N13 | EOS agent names in cognitive_loop.py | cognitive_loop.py:470-474 | LOW | P1 |

## Architecture Debt

| # | Item | Location | Effort | Priority |
|---|------|----------|--------|----------|
| A1 | Three parallel execution paths not unified | gateway.py, spine.py, work_packet.py | HIGH | P0 |
| A2 | ProductConnectionManager imports from projections/ | product_connections.py | MEDIUM | P1 |
| A3 | workstation/ constitutional engines (26,671 lines dead code) | substrate/execution/workers/workstation/ | LOW (delete) | P1 |
| A4 | Empty placeholder directories | substrate/deployment/, distribution/, execution/environments/, logs/ | LOW | P2 |
| A5 | Broken import in gateway.py | gateway.py:1542 (observability.status.status) | LOW | P1 |
| A6 | 13 legacy type duplicates in canonical_types.py | canonical_types.py LEGACY_DUPLICATES | MEDIUM | P2 |

## Security Debt

| # | Item | Location | Effort | Priority |
|---|------|----------|--------|----------|
| S1 | Substrate uses neondb_owner (BYPASSRLS) | state/storage/db.py | MEDIUM | P0 |
| S2 | /api/umh/profile hardcodes instance context | cockpit.py:1029-1038 | LOW | P0 |
| S3 | Plaintext secrets in env files | services/.env, infra/docker/umh.env | MEDIUM | P1 |
| S4 | No HTTPS enforcement | docker-compose.yml | MEDIUM | P1 |
| S5 | Discord wildcard permissions | docker-compose.yml | LOW | P2 |
| S6 | chromium --no-sandbox | docker/computer-use/ | LOW | P2 |

## Cockpit Debt

| # | Item | Location | Effort | Priority |
|---|------|----------|--------|----------|
| C1 | 7 execution control endpoints are stubs | cockpit.py | MEDIUM | P0 |
| C2 | No tmux session visibility panel | cockpit frontend | MEDIUM | P1 |
| C3 | No degraded mode detection | cockpit frontend + backend | MEDIUM | P1 |
| C4 | No overnight summary flow | services/operator_api.py | MEDIUM | P1 |
| C5 | Rate limiting is in-memory | cockpit.py | LOW | P1 |

## Projection Debt

| # | Item | Location | Effort | Priority |
|---|------|----------|--------|----------|
| P1 | LyfeOS integration incomplete | projections/lyfeos/integration/ | MEDIUM | P1 |
| P2 | CreatorOS has no poller | projections/creatoros/integration/ | LOW | P1 |
| P3 | Projection manifests outdated vs 14.6B canons | projections/*/integration/manifest.py | MEDIUM | P1 |
| P4 | No integration contract versioning | projections/*/integration/ | LOW | P1 |
| P5 | No projection health check mechanism | substrate/integrations/ | LOW | P1 |

## Observability Debt

| # | Item | Location | Effort | Priority |
|---|------|----------|--------|----------|
| O1 | No request/access logging | transports/api/ | MEDIUM | P0 |
| O2 | No alerting system | (new) | MEDIUM | P1 |
| O3 | OTEL exporters disabled | docker-compose.yml | LOW | P2 |
| O4 | No log retention policy | substrate/observability/ | LOW | P1 |

## Testing Debt

| # | Item | Location | Effort | Priority |
|---|------|----------|--------|----------|
| T1 | No CI pipeline | (new, .github/workflows/) | MEDIUM | P1 |
| T2 | No E2E tests for cockpit->API->substrate | tests/ | MEDIUM | P1 |
| T3 | ARCHITECTURE.md section numbering broken | ARCHITECTURE.md | LOW | P2 |
| T4 | Wiki index stale with 37 broken wikilinks | knowledge/index.md | LOW | P2 |

## Summary

| Category | P0 | P1 | P2 | Total |
|----------|----|----|----|----|
| Naming | 3 | 5 | 3 | 11 |
| Architecture | 1 | 3 | 2 | 6 |
| Security | 2 | 2 | 2 | 6 |
| Cockpit | 1 | 4 | 0 | 5 |
| Projection | 0 | 5 | 0 | 5 |
| Observability | 1 | 2 | 1 | 4 |
| Testing | 0 | 2 | 2 | 4 |
| **Total** | **8** | **23** | **10** | **41** |
