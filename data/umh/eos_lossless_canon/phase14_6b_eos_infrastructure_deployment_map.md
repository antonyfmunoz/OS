---
phase: "14.6B-EOS"
status: "DRAFT"
operator_approved: false
allows_implementation: false
date: "2026-06-04"
provenance: "SYNTHESIZED_CANON"
description: "Current and target deployment architecture for EOS — infrastructure, hosting, database, CI/CD, monitoring, environments, scaling, disaster recovery, cost, and open questions."
---

# EOS Infrastructure & Deployment Map

This document captures the complete deployment picture for EntrepreneurOS:
what exists today, what the target architecture looks like, and every gap
between them. No implementation is authorized from this document.

Cross-references (not duplicated):
- `phase14_6b_eos_current_implementation_truth.json` — code-level state across all locations
- `phase14_6b_eos_auth_security_truth.json` — auth, RLS, session, API security posture
- `phase14_6b_eos_api_contract_map.json` — all API endpoints current and planned

---

## 1. Current State — No Production Deployment

**Provenance: CODE_RESOLVED_CURRENT_TRUTH**

EOS has zero production deployment. Nothing is running, reachable, or serving users.

| Dimension | Status |
|---|---|
| EOS SaaS frontend | NOT DEPLOYED. No running React app anywhere. |
| EOS SaaS backend | NOT DEPLOYED. No running Express/Hono server for EOS. |
| EOS projection on UMH | NOT DEPLOYED. `projections/eos/` code exists but no container runs it. |
| Fly.io config | NOT PRESENT. No `fly.toml` for EOS. (UMH cockpit has one at `cockpit/fly.toml`.) |
| Docker container | NOT PRESENT. No EOS-specific container in `docker-compose.yml`. The `eos_network` name is the shared Docker network for UMH services (os-discord, os-operator, os-webhook, os-scraper), not an EOS container. |
| Domain | NOT CONFIGURED. No DNS record points to an EOS deployment. |
| CI/CD | NOT PRESENT. No GitHub Actions, no Fly deploy pipeline, no automated testing. |
| Monitoring | NOT PRESENT. No APM, no error tracking, no uptime monitoring for EOS. |

### Where code lives today

| Location | Files | Status | Last Activity |
|---|---|---|---|
| GitHub `main` (antonyfmunoz/EntrepreneurOS) | 202 | Stale | 2026-02-20 (Replit Agent) |
| Beast `feature/company-system` | 603 | Promotion candidate | 2026-04-16 |
| VPS `projections/eos/` | ~30 files, 5699 lines | Active UMH projection | Current |
| VPS `transports/api/http/` | UMH platform layer | Active | Current |
| VPS `saas/` | Empty (bridge/__pycache__ only) | Placeholder | N/A |

### What runs on VPS today (UMH substrate, not EOS SaaS)

Four Docker containers on the VPS serve UMH substrate services. These are not EOS
application containers but they execute EOS projection logic when signals arrive:

- `os-discord` — Discord bot (primary human interface today)
- `os-operator` — Operator API + background jobs
- `os-webhook` — Calendly webhook receiver (port 8080)
- `os-scraper` — Overnight scrape jobs (restart: no)

All share `eos_network` bridge network and bind-mount `/opt/OS` as `/app`.

---

## 2. Target Architecture

**Provenance: SYNTHESIZED_CANON**

EOS requires three deployment surfaces that operate independently but
communicate via API:

```
                        +-----------------------+
                        |     Cloudflare CDN    |
                        |  (static + DNS + WAF) |
                        +-----------+-----------+
                                    |
                     +--------------+--------------+
                     |                             |
            +--------v--------+          +---------v--------+
            |   Fly.io (SJC)  |          |   Fly.io (SJC)   |
            |  EOS Frontend   |          |   EOS Backend     |
            |  (Nginx + SPA)  |          | (Node.js/Express) |
            +--------+--------+          +---------+---------+
                     |                             |
                     |    Clerk (auth, sessions)   |
                     +----------+--+---------------+
                                |  |
                     +----------v--v-----------+
                     |     Neon Postgres        |
                     | (connection pooling,     |
                     |  branching, RLS)         |
                     +----------+--------------+
                                |
                     +----------v--------------+
                     |   VPS (100.77.233.50)   |
                     |   UMH Substrate + EOS   |
                     |   Projection (Docker)   |
                     +--------------------------+
```

### Component responsibilities

| Component | Role | Runtime |
|---|---|---|
| EOS Frontend | React 18 SPA. Vite build. Static assets served by Nginx. | Fly.io Machine (shared-cpu-1x, 512MB) |
| EOS Backend | Express 4 + Hono API. Business logic, Clerk auth verification, Drizzle ORM queries. | Fly.io Machine (shared-cpu-1x, 1GB) |
| Neon Postgres | Primary datastore. Dual-pool RLS (neondb_owner + eos_app). Connection pooling via Neon proxy. | Neon managed (us-east-1 or us-west-2) |
| UMH Substrate | Agent execution, governance, intelligence routing, signal processing. EOS projection registers at boot. | VPS Docker (existing os-operator container or new eos-projection container) |
| Clerk | Authentication, session management, org/tenant identity, MFA, OAuth. | Clerk cloud (SaaS) |
| Cloudflare | DNS, CDN for static assets, WAF, DDoS protection, SSL termination. | Cloudflare managed |

### Separation from UMH Cockpit and other projections

EOS, the UMH Cockpit, CreatorOS, and LyfeOS are separate deployments:

| App | Fly.io App Name | Domain | Status |
|---|---|---|---|
| UMH Cockpit | `umh-cockpit` | universalmetaharness.tech | Deployed (SJC region) |
| EOS SaaS | TBD (e.g., `eos-app`) | TBD (see Section 9) | Not deployed |
| CreatorOS | TBD | TBD | Not started |
| LyfeOS | TBD | TBD | Not started |

They share the same Neon database cluster (org-scoped via RLS) and the same
UMH substrate on the VPS, but each has its own Fly.io app, domain, and
Clerk application.

---

## 3. Database Architecture

**Provenance: CODE_RESOLVED_CURRENT_TRUTH + SYNTHESIZED_CANON**

### Existing Neon projects

| Neon Project | Region | Purpose | Schema Version | Status |
|---|---|---|---|---|
| `ep-dark-poetry` | us-east-1 | Dev/staging for UMH+EOS integration | v2 (events-driven) | Active — has `umh_status` columns and `umh_outcomes` table |
| `ep-winter-sea` | us-west-2 | Production EntrepreneurOS | v1 (companies, crm_contacts, crm_deals) | Stale — older schema, cutover deferred |

### Target schema ownership

Two schema layers share the same Neon database but are maintained by different
codebases:

| Layer | Tables | Managed By | Migration Tool |
|---|---|---|---|
| UMH Platform | users, organizations, org_members, portfolios, approvals, embeddings, umh_outcomes, user_agent_sessions | `transports/api/http/db/migrate.ts` | Drizzle Kit |
| EOS Application | ventures, clients, transactions, offers, crm_contacts, crm_deals, crm_activities, agents, skills, events, skill_versions, workflows, interactions, outcomes, human_profiles | Beast branch schema (promotion candidate) | Drizzle Kit |

### Connection pooling

Neon provides built-in connection pooling via its proxy endpoint. Configuration:

- **Admin pool** (`DATABASE_URL`): `neondb_owner` credentials, BYPASSRLS. Used only for migrations and seed scripts.
- **App pool** (`DATABASE_APP_URL`): `eos_app` role, RLS enforced. All application queries must use this pool via `withOrg()` wrapper.
- **Critical gap**: `DATABASE_APP_URL` falls back to `DATABASE_URL` if not set, silently disabling RLS. This must be made a required variable.

### Branching strategy

Neon database branching provides zero-copy dev/staging environments:

| Environment | Neon Branch | Purpose |
|---|---|---|
| Production | `main` | Live data, RLS enforced |
| Staging | `staging` (branched from main) | Pre-deploy verification, seed data |
| Dev | `dev-<feature>` (branched from staging) | Feature development, disposable |

### Backups

Neon provides automatic point-in-time recovery (PITR) with configurable retention:

- **Free tier**: 7-day history
- **Pro tier**: 30-day history (target for production)
- **Manual snapshots**: Before migrations, before Beast branch promotion, before any schema-breaking change

---

## 4. CDN & Static Assets

**Provenance: SYNTHESIZED_CANON + INFERRED_PROFESSIONAL_GAP**

### Target setup

| Concern | Solution |
|---|---|
| CDN | Cloudflare (free tier sufficient initially) |
| Static hosting | Vite build output served by Nginx on Fly.io (same pattern as UMH Cockpit) |
| Asset hashing | Vite produces content-hashed filenames by default — long cache TTL safe |
| Image optimization | Cloudflare Polish (Pro plan) or build-time optimization via `vite-imagetools` |
| Font loading | Self-hosted Inter/Geist fonts (avoid Google Fonts GDPR issues). Loaded from `/fonts/` with `font-display: swap`. |
| Favicon / OG images | Static files in `public/`. Must include apple-touch-icon, og:image for social sharing. |

### Cache policy

| Path Pattern | Cache-Control | Reason |
|---|---|---|
| `/assets/*` (hashed) | `public, max-age=31536000, immutable` | Content-hashed — safe to cache forever |
| `/index.html` | `no-cache` | SPA entry point must always be fresh |
| `/fonts/*` | `public, max-age=31536000, immutable` | Fonts do not change |
| `/api/*` | `no-store` | API responses are dynamic, never cached |

---

## 5. CI/CD Pipeline

**Provenance: INFERRED_PROFESSIONAL_GAP**

No CI/CD exists today. The following pipeline must be built:

### GitHub Actions workflow (target)

```
Push to main (or PR merge)
  |
  +-> Lint (ESLint + Prettier)
  +-> Type check (tsc --noEmit)
  +-> Unit tests (Vitest)
  +-> Integration tests (Vitest + Neon dev branch)
  |
  +-> [on main only] Build Docker image
  +-> [on main only] Deploy to Fly.io staging
  +-> [on main only] Run smoke tests against staging
  +-> [manual approval] Promote staging -> production
```

### Required pipeline components

| Stage | Tool | Notes |
|---|---|---|
| Lint | ESLint 9 + Prettier | Both exist in Beast branch `package.json` |
| Type check | TypeScript `tsc --noEmit` | Catches type errors without building |
| Unit tests | Vitest | Beast branch has Vitest configured |
| Integration tests | Vitest + Neon branch | Spin up Neon dev branch per PR, run Drizzle migrations, test DB layer |
| Build | `npm run build` (Vite) | Produces static SPA + bundled server |
| Docker build | Multi-stage Dockerfile | Frontend: Nginx. Backend: Node.js 20. |
| Deploy | `flyctl deploy` | Separate apps for frontend and backend |
| Smoke tests | Playwright or custom curl scripts | Hit /health, verify auth flow, test critical API endpoints |
| Promote | Manual `flyctl deploy --app eos-app` | No auto-promote to production until confidence is established |

### Pre-commit hooks (inherited from UMH)

The UMH repo already has pre-commit hooks that apply to any EOS code in the
OS repo (projections/eos/, transports/api/http/):

- `check_type_divergence.py` — blocks parallel type definitions
- `check_instance_leak.py` — blocks hardcoded instance values in substrate/
- `check_projection_leak.py` — blocks projection names in substrate/
- `check_dependency_direction.py` — blocks upward dependency imports

The standalone EOS SaaS repo (EntrepreneurOS) needs its own hooks post-promotion.

---

## 6. Monitoring & Observability

**Provenance: INFERRED_PROFESSIONAL_GAP**

### Target stack

| Layer | Tool | Rationale |
|---|---|---|
| Error tracking | Sentry (free tier: 5K events/month) | Industry standard. JS + Node.js SDKs. Source map upload in CI. |
| Uptime monitoring | Fly.io built-in health checks + BetterStack (free tier) | Fly checks restart crashed machines. BetterStack alerts on downtime. |
| Application metrics | Fly.io Metrics (built-in Prometheus) | CPU, memory, request count, response time per machine. No extra cost. |
| Logging | Fly.io Log Shipper → Logtail/BetterStack | Structured JSON logs. Retention 30 days on free tier. |
| Database monitoring | Neon dashboard | Query performance, connection count, storage usage. Built into Neon console. |
| Real User Monitoring | Sentry Performance or PostHog (existing account) | Frontend page load, LCP, FID, CLS. |
| Alerting | BetterStack or PagerDuty (free tier) | Escalation: Slack/Discord notification → SMS → phone call |

### Health check endpoints

| Endpoint | Purpose | Response |
|---|---|---|
| `GET /health` | Load balancer liveness | `{ "status": "ok", "version": "<git-sha>" }` |
| `GET /health/ready` | Readiness (DB connected, Clerk reachable) | `{ "status": "ready", "db": true, "clerk": true }` |
| `GET /health/deep` | Full dependency check (Neon, Clerk, VPS substrate) | `{ "status": "ok", "neon": true, "clerk": true, "substrate": true }` |

---

## 7. Environment Management

**Provenance: SYNTHESIZED_CANON + INFERRED_PROFESSIONAL_GAP**

### Three environments

| Environment | Purpose | Neon Branch | Fly.io App | Domain |
|---|---|---|---|---|
| Development | Local dev, feature work | `dev-*` (per-feature branch) | N/A (localhost:5173 + localhost:3000) | localhost |
| Staging | Pre-production verification | `staging` | `eos-app-staging` | staging.entrepreneuros.com (or similar) |
| Production | Live users | `main` | `eos-app` | entrepreneuros.com (or operator-chosen domain) |

### Environment variables (required per environment)

| Variable | Dev | Staging | Production | Source |
|---|---|---|---|---|
| `DATABASE_URL` | Neon dev branch | Neon staging branch | Neon main branch | Neon console |
| `DATABASE_APP_URL` | Neon dev branch (eos_app) | Neon staging (eos_app) | Neon main (eos_app) | Neon console |
| `CLERK_PUBLISHABLE_KEY` | Clerk dev instance | Clerk staging instance | Clerk production instance | Clerk dashboard |
| `CLERK_SECRET_KEY` | Clerk dev secret | Clerk staging secret | Clerk production secret | Clerk dashboard |
| `CLERK_WEBHOOK_SECRET` | Clerk dev webhook | Clerk staging webhook | Clerk production webhook | Clerk dashboard |
| `UMH_SUBSTRATE_URL` | localhost:8765 | VPS Tailscale IP:8765 | VPS Tailscale IP:8765 | Operator config |
| `SENTRY_DSN` | Dev DSN | Staging DSN | Production DSN | Sentry console |
| `NODE_ENV` | development | staging | production | Fly.io secrets |
| `VITE_CLERK_PUBLISHABLE_KEY` | (build-time) | (build-time) | (build-time) | Fly.io build args |

### Secret management

| Method | Used For |
|---|---|
| Fly.io Secrets (`flyctl secrets set`) | Production + staging server-side secrets |
| Fly.io Build Args | VITE_* build-time variables (public, baked into SPA) |
| `.env.local` (gitignored) | Local development |
| GitHub Actions Secrets | CI pipeline secrets (Neon, Clerk, Fly.io deploy token) |

---

## 8. Docker Configuration

**Provenance: SYNTHESIZED_CANON**

### EOS Frontend Dockerfile (target)

Follows the same pattern as the UMH Cockpit (`cockpit/Dockerfile`):

- **Build stage**: Node 20 slim, `npm ci`, Vite build with build args for VITE_* env vars.
- **Runtime stage**: Nginx Alpine, copies built SPA to `/usr/share/nginx/html`, custom `nginx.conf` for SPA routing (all non-file requests rewrite to `/index.html`).
- **Port**: 8080 (matches Fly.io internal_port convention).

### EOS Backend Dockerfile (target)

- **Build stage**: Node 20 slim, `npm ci`, `esbuild` or `tsx` build for server bundle.
- **Runtime stage**: Node 20 slim (not Alpine — native modules may need glibc), copies built server, runs `node dist/server.js`.
- **Port**: 3000 (internal, mapped via Fly.io).
- **Health check**: `HEALTHCHECK CMD curl -f http://localhost:3000/health || exit 1`

### EOS Projection Container (optional, VPS)

If EOS projection logic needs its own container (separate from os-operator):

- Bind-mounts `/opt/OS` as `/app` (same pattern as existing containers).
- Runs on `eos_network` bridge.
- Python 3.11 (matches existing Docker base image).
- Command: `python3 projections/eos/entrypoint.py` (to be created).

### docker-compose addition (VPS, not Fly.io)

```yaml
  eos-projection:
    build: .
    container_name: eos-projection
    restart: always
    working_dir: /app
    command: python3 projections/eos/entrypoint.py
    networks:
      - eos_network
    extra_hosts:
      - "host.docker.internal:host-gateway"
    volumes:
      - ${UMH_ROOT:-/opt/OS}:/app
    env_file:
      - services/.env
      - infra/docker/umh.env
    environment:
      - PYTHONPATH=/app
      - UMH_ROOT=/app
      - TZ=America/Los_Angeles
    deploy:
      resources:
        limits:
          cpus: "0.5"
          memory: 512M
```

---

## 9. Domain & DNS

**Provenance: OPEN_QUESTION_OPERATOR_DECISION_REQUIRED**

### Options

| Option | Domain | Notes |
|---|---|---|
| A | `entrepreneuros.com` | Premium — must acquire. Clear brand identity. |
| B | `eos.ost.dev` (or similar) | Subdomain of OST domain. Free. Less brand equity. |
| C | `app.entrepreneuros.ai` | .ai TLD. Modern tech feel. Must acquire. |
| D | `eos.universalmetaharness.tech` | Subdomain of existing UMH domain. Free. Confuses EOS identity with UMH. |

### DNS records (once domain chosen)

| Record | Type | Value | Purpose |
|---|---|---|---|
| `@` or `app` | CNAME | `eos-app.fly.dev` | Frontend app |
| `api` | CNAME | `eos-api.fly.dev` | Backend API |
| `_acme-challenge` | TXT | (auto by Fly.io) | SSL certificate verification |

### SSL

Fly.io provides automatic SSL via Let's Encrypt for custom domains.
No manual certificate management required.

---

## 10. Cost Estimation

**Provenance: INFERRED_PROFESSIONAL_GAP**

### Monthly cost at launch (solo founder, minimal traffic)

| Service | Tier | Monthly Cost | Notes |
|---|---|---|---|
| Fly.io Frontend | shared-cpu-1x, 512MB, auto-stop | ~$0 (free allowance covers 1 machine) | Stops when idle |
| Fly.io Backend | shared-cpu-1x, 1GB, auto-stop | ~$3-5 | 1GB machine slightly above free tier |
| Neon Postgres | Free tier (0.5 GiB storage, 1 branch) | $0 | 7-day PITR, autoscale to 0 |
| Clerk | Free tier (10K MAU) | $0 | More than sufficient for MVP |
| Cloudflare | Free tier | $0 | DNS, CDN, basic WAF |
| Sentry | Free tier (5K events/month) | $0 | Error tracking |
| BetterStack | Free tier | $0 | Uptime monitoring |
| Domain | .com or .ai | $10-50/year | One-time + annual renewal |
| **Total** | | **~$3-10/month** | |

### Monthly cost at $10K MRR milestone (~100-500 users)

| Service | Tier | Monthly Cost | Notes |
|---|---|---|---|
| Fly.io Frontend | shared-cpu-1x, 512MB, always-on | ~$3 | Low CPU, static serving |
| Fly.io Backend | shared-cpu-2x, 1GB, 2 machines | ~$20-30 | Horizontal scale for API |
| Neon Postgres | Pro ($19/month, 10 GiB, unlimited branches) | $19 | 30-day PITR, autoscale |
| Clerk | Pro ($25/month, 10K+ MAU) | $25 | Advanced features, SSO |
| Cloudflare | Pro ($20/month) | $20 | Image optimization, advanced WAF |
| Sentry | Team ($26/month, 50K events) | $26 | Performance monitoring |
| BetterStack | Starter ($24/month) | $24 | Incident management |
| **Total** | | **~$140-170/month** | |

---

## 11. Scaling Strategy

**Provenance: SYNTHESIZED_CANON + INFERRED_PROFESSIONAL_GAP**

### Phase 1 — Solo founder MVP (0-10 users)

- Single Fly.io machine per service, auto-stop enabled.
- Neon free tier with autoscale-to-zero.
- No caching layer. Direct DB queries for everything.
- VPS handles all UMH substrate work (existing capacity).

### Phase 2 — Early customers (10-100 users)

- Keep single machine but disable auto-stop (consistent response times).
- Add Redis (Fly.io Upstash integration, free tier) for session cache and rate limiting.
- Neon Pro for branching and longer PITR.
- Monitor query performance via Neon dashboard; add indexes as needed.

### Phase 3 — Growth ($10K+ MRR, 100-1000 users)

- Horizontal scale: 2-3 backend machines with Fly.io load balancing.
- Neon read replicas for analytics/reporting queries.
- CDN caching for public API responses (templates, public skill catalog).
- Consider moving VPS substrate to Fly.io or dedicated server if CPU becomes bottleneck.

### Phase 4 — Enterprise (1000+ users, multi-region)

- Multi-region Fly.io deployment (SJC + IAD or EU).
- Neon multi-region (when available) or read replicas per region.
- Dedicated Clerk Enterprise instance.
- Full APM (Datadog or equivalent).
- SOC 2 compliance requirements enter scope.

### Scaling decisions that do NOT need to be made now

- Microservice decomposition (monolith is correct at this scale)
- Kubernetes (Fly.io Machines are simpler and cheaper)
- Multi-database sharding (Neon RLS handles tenant isolation)
- Custom auth system (Clerk handles the entire auth surface)

---

## 12. Disaster Recovery

**Provenance: INFERRED_PROFESSIONAL_GAP**

### Recovery targets

| Metric | Target (MVP) | Target (Growth) |
|---|---|---|
| RPO (Recovery Point Objective) | 24 hours | 1 hour |
| RTO (Recovery Time Objective) | 4 hours | 30 minutes |

### Backup and recovery plan

| Component | Backup Method | Recovery Method |
|---|---|---|
| Database | Neon PITR (automatic, 7-30 day retention) | Neon branch from point-in-time, promote to main |
| Application code | Git (GitHub) | `flyctl deploy` from any machine with repo access |
| Environment secrets | Fly.io Secrets (encrypted at rest) | Re-set via `flyctl secrets set` from documented list |
| Clerk config | Clerk dashboard (managed SaaS) | No recovery needed — Clerk manages its own HA |
| DNS | Cloudflare (managed) | No recovery needed — Cloudflare manages its own HA |
| UMH Substrate | VPS snapshots (Hostinger weekly) + Git | Restore VPS from snapshot, `git pull`, `docker compose up` |

### Pre-migration safety protocol

Before any schema migration or data-altering deployment:

1. Create Neon branch from production (zero-copy snapshot)
2. Run migration against branch
3. Verify data integrity on branch
4. If success: run migration against production
5. If failure: branch is disposable, production untouched

### Incident response

| Severity | Response | SLA (MVP) |
|---|---|---|
| P0 — total outage | Drop everything, restore service | 4 hours |
| P1 — data corruption | Stop writes, restore from PITR, notify affected users | 8 hours |
| P2 — degraded performance | Investigate, scale horizontally if needed | 24 hours |
| P3 — non-critical bug | Queue for next deploy | Next business day |

---

## 13. Open Questions Requiring Operator Decision

**Provenance: OPEN_QUESTION_OPERATOR_DECISION_REQUIRED**

| ID | Question | Options | Impact | Default Recommendation |
|---|---|---|---|---|
| DEPLOY-OQ-001 | What domain should EOS use? | See Section 9 options A-D | Brand identity, SEO, user trust | Option A (`entrepreneuros.com`) if acquirable, else Option C |
| DEPLOY-OQ-002 | Should EOS frontend and backend be separate Fly.io apps or a single combined app? | Separate (2 apps) vs Combined (1 app) | Separate is cleaner but adds deployment complexity | Combined for MVP, separate at growth |
| DEPLOY-OQ-003 | Should the EOS SaaS repo remain standalone (EntrepreneurOS) or merge into the OS monorepo? | Standalone vs Monorepo | Standalone: simpler CI for SaaS. Monorepo: shared types, single deploy pipeline. | Standalone with shared types package published to npm |
| DEPLOY-OQ-004 | Which Neon project becomes production? | `ep-dark-poetry` (us-east-1, v2 schema) vs `ep-winter-sea` (us-west-2, v1 schema) vs New project | Schema version, region latency, data migration scope | `ep-dark-poetry` — already has v2 schema with UMH integration |
| DEPLOY-OQ-005 | Should EOS backend communicate with UMH substrate via HTTP API (Tailscale) or direct DB queries? | HTTP API vs Shared DB | HTTP: clean boundary, network latency. Shared DB: faster, tighter coupling. | HTTP API — maintains architectural separation, substrate runs its own governance |
| DEPLOY-OQ-006 | When should Beast branch be promoted to main? | Before deployment vs After deployment infra is ready | Blocks downstream work | After deployment infra is ready — promote into a deployable pipeline, not into a void |
| DEPLOY-OQ-007 | Should the VPS remain the UMH substrate host long-term or should substrate move to Fly.io? | VPS (current) vs Fly.io migration | Cost, latency, operational complexity | VPS for now — Docker containers are working, no reason to migrate until scaling demands it |
| DEPLOY-OQ-008 | Fly.io region: SJC (San Jose) like cockpit, or IAD (Ashburn) near Neon us-east-1? | SJC vs IAD | Neon `ep-dark-poetry` is us-east-1. SJC adds ~60ms latency to DB. | IAD — colocate with database for lowest query latency. Or migrate Neon to us-west-2. |

---

## 14. Implementation Debt — Known Gaps Blocking Deployment

**Provenance: IMPLEMENTATION_DEBT**

These are not open questions — they are known technical work that must be
completed before any deployment is possible.

| ID | Gap | Blocking | Effort |
|---|---|---|---|
| DEPLOY-DEBT-001 | No Fly.io config (fly.toml, Dockerfile) for EOS | Cannot deploy | Medium |
| DEPLOY-DEBT-002 | No CI/CD pipeline (GitHub Actions) | No automated deploy, no test gate | Medium |
| DEPLOY-DEBT-003 | Beast branch not promoted to main | 401-file divergence, stale auth on main | High (merge conflict resolution) |
| DEPLOY-DEBT-004 | `DATABASE_APP_URL` fallback silently disables RLS | Security — RLS bypassed in prod if env var missing | Low (make it required, fail on missing) |
| DEPLOY-DEBT-005 | `eos_app` role uses placeholder password in migration | Security — known weak credential | Low (read from env var) |
| DEPLOY-DEBT-006 | No health check endpoints | Fly.io cannot verify app is running | Low |
| DEPLOY-DEBT-007 | No rate limiting on any endpoint | DDoS/abuse vulnerability | Medium |
| DEPLOY-DEBT-008 | No CORS configuration | Cross-origin requests will fail or be uncontrolled | Low |
| DEPLOY-DEBT-009 | No security headers (CSP, HSTS, X-Frame-Options) | Browser security gaps | Low |
| DEPLOY-DEBT-010 | No Sentry or equivalent error tracking | Blind to production errors | Low |
| DEPLOY-DEBT-011 | No EOS-specific Docker container for VPS projection | EOS projection logic runs ad-hoc, not governed | Low |
| DEPLOY-DEBT-012 | `users` and `portfolios` tables have no RLS policies | Cross-tenant data visibility | Medium |

---

## 15. Deployment Sequence (Recommended Order)

**Provenance: SYNTHESIZED_CANON**

This is the recommended sequence, not an authorized implementation plan.

1. **Resolve DEPLOY-OQ-003** (standalone vs monorepo) — determines repo structure for everything after.
2. **Resolve DEPLOY-OQ-004** (which Neon project) — determines connection strings.
3. **Close DEPLOY-DEBT-004 and DEPLOY-DEBT-005** — database security basics.
4. **Promote Beast branch** (DEPLOY-DEBT-003) — get Clerk auth and company system onto main.
5. **Create Dockerfiles and fly.toml** (DEPLOY-DEBT-001) — following cockpit pattern.
6. **Build CI/CD pipeline** (DEPLOY-DEBT-002) — lint, type check, test, deploy.
7. **Add health checks, rate limiting, CORS, security headers** (DEPLOY-DEBT-006 through DEPLOY-DEBT-009).
8. **Deploy to staging** — verify end-to-end on Fly.io with Neon staging branch.
9. **Add monitoring** (DEPLOY-DEBT-010) — Sentry, BetterStack.
10. **Resolve DEPLOY-OQ-001** (domain) — configure DNS.
11. **Promote staging to production** — first live deployment.
12. **Close remaining RLS gap** (DEPLOY-DEBT-012) — before any multi-tenant use.
