# LyfeOS Infrastructure and Deployment Map

Revised in Phase 14.6F to align with 18 ratified P0 decisions (2026-06-04).

**Phase:** 14.6B-LyfeOS (revised 14.6F)
**Artifact:** 44
**Revised:** 2026-06-04
**Operator Approved:** false
**Allows Implementation:** false
**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

**Ratified Infrastructure Direction (DEC-146B-LOS-003, OPERATOR-APPROVED 2026-06-04):** Fly.io is the Trinity standard infrastructure. LyfeOS will migrate from Replit to Fly.io. Current Replit deployment documented below is accurate current-state truth. Migration to Fly.io is the ratified direction but has not been implemented. Implementation does not begin until a separate implementation gate is approved.

---

## Current Deployment Architecture

LyfeOS is deployed on Replit (autoscale) with Neon Postgres as the external database. There is no containerization, no CI/CD pipeline, and no infrastructure-as-code. Deployment is managed entirely through the Replit platform.

---

## Hosting

| Component | Provider | Details |
|-----------|----------|---------|
| Application hosting | Replit (autoscale) | Node.js runtime, auto-deploy on push |
| Custom domain | lyfeos.net | DNS configured through Replit |
| SSL/TLS | Replit-managed | Automatic HTTPS via Let's Encrypt |
| CDN | Replit-provided | Static asset serving through Replit edge |

---

## Database

| Component | Provider | Details |
|-----------|----------|---------|
| Database | Neon Postgres (serverless) | External to Replit |
| ORM | Drizzle ORM | Schema in shared/schema.ts |
| Migrations | Drizzle Kit | drizzle-kit push for schema sync |
| Connection | DATABASE_URL env var | Neon serverless driver |
| Connection pooling | Neon built-in | Serverless compute, scales to zero |
| Backup | Neon PITR (unverified) | See backup_recovery_risk_packet |

---

## Build Pipeline

| Stage | Tool | Output |
|-------|------|--------|
| Frontend build | Vite | dist/public/ (React SPA) |
| Backend build | esbuild | dist/index.js (Express server bundle) |
| TypeScript compilation | tsc (type-check only) | No emit, Vite/esbuild handle transpilation |
| CSS | Tailwind CSS | Compiled via Vite PostCSS |
| Package manager | npm | package.json + package-lock.json |

---

## Runtime Configuration

| Item | Value | Source |
|------|-------|--------|
| Node.js version | Replit-managed (likely 18 or 20) | Replit nixpacks config |
| Port | 5000 | Configured in server entry |
| Process manager | Replit-managed | No PM2, no systemd |
| Auto-restart | Replit autoscale | Restarts on crash, scales to zero on idle |

---

## Environment Variables

| Variable | Purpose | Sensitivity |
|----------|---------|-------------|
| DATABASE_URL | Neon Postgres connection string | CRITICAL |
| SESSION_SECRET | Express session signing key | CRITICAL |
| FIREBASE_API_KEY | Firebase client API key | MEDIUM |
| FIREBASE_AUTH_DOMAIN | Firebase auth domain | LOW |
| FIREBASE_PROJECT_ID | Firebase project ID | LOW |
| FIREBASE_MESSAGING_SENDER_ID | FCM sender ID | LOW |
| FIREBASE_APP_ID | Firebase app ID | LOW |
| GOOGLE_CLIENT_ID | Google OAuth client ID | MEDIUM |
| GOOGLE_CLIENT_SECRET | Google OAuth client secret | CRITICAL |
| GOOGLE_REDIRECT_URI | OAuth callback URL | LOW |
| OPENAI_API_KEY | OpenAI API key (NOVA) | CRITICAL |
| ANTHROPIC_API_KEY | Anthropic API key (NOVA fallback) | CRITICAL |
| VAPID_PUBLIC_KEY | Web Push VAPID public key | LOW |
| VAPID_PRIVATE_KEY | Web Push VAPID private key | CRITICAL |

**Storage:** Replit Secrets (environment variables). Not in version control.

---

## PWA Configuration

| Component | Status | Details |
|-----------|--------|---------|
| Web App Manifest | Present | manifest.json with app name, icons, theme |
| Service Worker | Present | Caching strategy, offline support |
| Push Notifications | FCM (Firebase Cloud Messaging) | VAPID keys + Firebase config |
| Install prompt | Present | A2HS (Add to Home Screen) support |
| Offline support | Partial | Service worker caches static assets |

---

## What Does NOT Exist

| Item | Status | Impact |
|------|--------|--------|
| Docker / Dockerfile | NOT present | Cannot containerize or self-host |
| Fly.io configuration | NOT present — **RATIFIED TARGET** (DEC-146B-LOS-003) | Migration to Fly.io is ratified direction |
| Vercel configuration | NOT present | No serverless deployment option |
| CI/CD pipeline | NOT present | No automated testing before deploy |
| GitHub Actions | NOT present | No automated workflows |
| Infrastructure as Code | NOT present | No Terraform, Pulumi, or CDK |
| Staging environment | NOT present | All changes deploy directly to production |
| Blue/green deployment | NOT available | Replit does not support this pattern |
| Rollback mechanism | Manual only | Revert git commit and redeploy via Replit |
| Load balancer configuration | Replit-managed | No custom configuration possible |
| Rate limiting | NOT confirmed | No explicit rate limiting middleware found |
| WAF / DDoS protection | Replit-provided (basic) | No custom WAF rules |

---

## Deployment Flow

```
Developer pushes to GitHub
    |
    v
Replit detects change (auto-sync or manual pull)
    |
    v
Replit runs build (vite build + esbuild)
    |
    v
Replit starts server on port 5000
    |
    v
Live at lyfeos.net
```

No tests run before deploy. No staging validation. No approval gate.

---

## Platform Risks

### Replit Dependency

- **Vendor lock-in:** Application is deployed exclusively on Replit. No alternative deployment path exists.
- **Scaling limits:** Replit autoscale has performance characteristics that are not well-documented for production workloads.
- **Cold start:** Autoscale may scale to zero, causing latency on first request after idle period.
- **Cost unpredictability:** Autoscale billing depends on compute usage which varies with traffic patterns.
- **Platform stability:** Replit is a development platform first, production hosting second. Outages affect production.

### No CI/CD

- Code deploys without automated tests
- No lint/type-check gate before production
- No security scanning
- No dependency vulnerability checking
- Human error in deployment is unguarded

---

## Operator Decision — RESOLVED

**DEC-146B-LOS-003** (formerly DEC-146B-INFRA-001): Infrastructure migration path

**STATUS: RESOLVED** — Ratified 2026-06-04 (Phase 14.6E). OPERATOR-APPROVED.

**Ratified Answer:** Option 2 — Migrate to Fly.io. Fly.io is the Trinity standard.

Original options presented:
1. **Stay on Replit** — accept platform limitations, focus on application features
2. **Migrate to Fly.io** — containerize, gain deployment control, CI/CD, staging env ← **SELECTED**
3. **Migrate to Vercel** — serverless, better DX for React+Express, built-in CI
4. **Hybrid** — keep Replit for development, deploy production elsewhere

**Original recommendation:** Defer migration until after production hardening (backup, RLS, error tracking). The current Replit deployment works. Migration is a standardization and reliability improvement, not an emergency. When ready, Fly.io aligns with the Trinity platform standard established in Phase 14.5.

**Current state:** Replit remains the active deployment platform. Fly.io migration has not begun. All Replit documentation above is current-state truth.
