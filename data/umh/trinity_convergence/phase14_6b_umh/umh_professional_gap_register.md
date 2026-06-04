# UMH Professional Gap Register

Phase: 14.6B-UMH | Status: DRAFT | Provenance: INFERRED_PROFESSIONAL_GAP

---

## Priority Legend
- **P0**: Must resolve before Cockpit/UMH governs implementation
- **P1**: Must resolve before Trinity feature build
- **P2**: Must resolve before broader beta or production scale
- **P3**: Future optimization

---

## 1. Product Doctrine Gaps

| # | Gap | Priority | Evidence |
|---|-----|----------|----------|
| 1.1 | Naming incoherence -- "Universal Mastery Hierarchy" vs "Universal Meta Harness" in 50+ files | P0 | README.md says one, pyproject.toml says another |
| 1.2 | PHILOSOPHY.md uses EntrepreneurOS as system name | P0 | PHILOSOPHY.md is the foundational document |
| 1.3 | No single canonical product definition document | P0 | Scattered across README, ARCHITECTURE, PHILOSOPHY |

## 2. Code Architecture Gaps

| # | Gap | Priority | Evidence |
|---|-----|----------|----------|
| 2.1 | Three parallel execution paths (Gateway/Spine/WorkPacket) not unified | P0 | Each has different governance, memory, tracing |
| 2.2 | substrate/integrations/product_connections.py imports from projections/ | P1 | Upward dependency violation |
| 2.3 | 26,671 lines of workstation/ constitutional engines (dead code per audit) | P1 | Identified in exhaustive audit |
| 2.4 | EOS agent names hardcoded in cognitive_loop.py (eos-ceo, eos-sales, etc.) | P1 | Projection names in substrate |
| 2.5 | Empty directories in substrate (deployment/, distribution/, execution/environments/, execution/logs/) | P2 | Placeholder without content |

## 3. Cockpit Readiness Gaps

| # | Gap | Priority | Evidence |
|---|-----|----------|----------|
| 3.1 | Execution control stubs (start/stop/pause/resume return static ok) | P0 | 7 stub endpoints in cockpit.py |
| 3.2 | /api/umh/profile hardcodes founder name and company names | P0 | Instance Context Law violation |
| 3.3 | No tmux session visibility panel | P1 | Infrastructure exists but no UI |
| 3.4 | No degraded mode detection or indicator | P1 | No code for degraded mode handling |
| 3.5 | No overnight work summary upon operator return | P1 | No return-to-summary flow |

## 4. Projection Protocol Gaps

| # | Gap | Priority | Evidence |
|---|-----|----------|----------|
| 4.1 | LyfeOS integration incomplete (only manifest + signals) | P1 | Missing handlers, outcomes, correlation, tables, poller |
| 4.2 | CreatorOS has no poller | P1 | Integration waits for external trigger |
| 4.3 | No versioning on integration contracts | P1 | No mechanism to handle schema changes |
| 4.4 | No health check for projection connections | P1 | No automated detection of projection failures |
| 4.5 | Projection manifests outdated vs corrected 14.6B product canons | P1 | Manifests are shallow current slices |

## 5. Data Boundary Gaps

| # | Gap | Priority | Evidence |
|---|-----|----------|----------|
| 5.1 | No sensitive data exclusion mechanism in signal emitters | P0 | LyfeOS therapy/health data could enter UMH |
| 5.2 | No privacy policy framework for projections | P1 | No data classification on SignalEnvelope |
| 5.3 | No cross-projection data access control | P1 | No mechanism to govern data sharing |
| 5.4 | Audit logs may contain sensitive payloads | P1 | Full signal content in traces |

## 6. Security Gaps

| # | Gap | Priority | Evidence |
|---|-----|----------|----------|
| 6.1 | Substrate connects as neondb_owner (BYPASSRLS) | P0 | All RLS policies bypassed for Python code |
| 6.2 | Dev bypass allows unauthenticated access from private IPs | P0 | Acceptable for single-operator only |
| 6.3 | No HTTPS enforcement in Docker config | P1 | Relies on external proxy/Tailscale |
| 6.4 | Secrets in plaintext env files (no encryption at rest) | P1 | services/.env, infra/docker/umh.env |
| 6.5 | Discord bot has wildcard permissions | P2 | All guilds, channels, users allowed |

## 7. Auth Gaps

| # | Gap | Priority | Evidence |
|---|-----|----------|----------|
| 7.1 | No session-based auth for cockpit (API key only) | P1 | No token refresh, no session expiry |
| 7.2 | No multi-user auth model | P2 | Single-operator assumption throughout |
| 7.3 | SaaS API uses header-based org lookup (no token auth) | P1 | x-org-id header, no JWT/session |

## 8. Rate Limiting Gaps

| # | Gap | Priority | Evidence |
|---|-----|----------|----------|
| 8.1 | Rate limiting is in-memory (resets on restart) | P1 | No persistence layer |
| 8.2 | Only 3 actions rate-limited (promote, execute, approve) | P2 | Other mutations unprotected |
| 8.3 | No per-projection rate limiting | P2 | No protection against noisy projections |

## 9. Observability Gaps

| # | Gap | Priority | Evidence |
|---|-----|----------|----------|
| 9.1 | No request/access logging on cockpit API | P0 | Cannot audit who accessed what |
| 9.2 | No alerting system | P1 | Errors recorded but not alerted |
| 9.3 | No log retention policy | P1 | JSONL files grow unbounded |
| 9.4 | OTEL exporters disabled | P2 | OTEL_*_EXPORTER=none in docker-compose |
| 9.5 | No distributed tracing across services | P2 | No correlation IDs between containers |

## 10. Testing Gaps

| # | Gap | Priority | Evidence |
|---|-----|----------|----------|
| 10.1 | No integration tests hitting real external services | P1 | Integration marker exists but unused |
| 10.2 | No end-to-end test for cockpit -> API -> substrate flow | P1 | Each layer tested in isolation |
| 10.3 | No performance/load tests | P2 | No benchmark for response times |
| 10.4 | LyfeOS has only 24 tests (~5% coverage) | P1 | Per Phase 14.6B-LyfeOS audit |

## 11. CI/CD Gaps

| # | Gap | Priority | Evidence |
|---|-----|----------|----------|
| 11.1 | No CI pipeline | P1 | No GitHub Actions, no automated testing on push |
| 11.2 | No automated deployment pipeline | P1 | Manual docker restart |
| 11.3 | Pre-commit hooks exist but no CI enforcement | P1 | 4 gates exist locally only |

## 12. Backup/Recovery Gaps

| # | Gap | Priority | Evidence |
|---|-----|----------|----------|
| 12.1 | No confirmed backup/restore for Neon database | P0 | Neon has backups but no tested restore |
| 12.2 | No backup for JSONL runtime data | P1 | Local files only |
| 12.3 | No disaster recovery plan | P2 | Single VPS is a single point of failure |
| 12.4 | No runbook for service recovery | P1 | No documented recovery procedures |

## 13. Infrastructure Gaps

| # | Gap | Priority | Evidence |
|---|-----|----------|----------|
| 13.1 | No container health checks in docker-compose | P1 | Services could fail silently |
| 13.2 | No Docker secrets management | P1 | Plaintext env files |
| 13.3 | No container logging driver | P2 | Default stdout/stderr |
| 13.4 | chromium --no-sandbox in computer-use Dockerfile | P2 | Security concern for browser agents |

## 14. Documentation Gaps

| # | Gap | Priority | Evidence |
|---|-----|----------|----------|
| 14.1 | Wiki index stale (2026-04-05) with 37 broken wikilinks | P2 | knowledge/index.md |
| 14.2 | ARCHITECTURE.md section numbering broken (11->13->12) | P2 | Formatting error |
| 14.3 | No API documentation (beyond code inspection) | P1 | 210 endpoints undocumented |

## Summary by Priority

| Priority | Count | Key Themes |
|----------|-------|-----------|
| P0 | 10 | Naming, execution paths, security (RLS bypass), data boundary, cockpit stubs, backup |
| P1 | 25 | Projection integration, auth, CI/CD, observability, naming debt, documentation |
| P2 | 12 | Rate limiting, infrastructure hardening, testing, wiki maintenance |
| P3 | 0 | (None identified at this time) |
