# Campaign 24: LyfeOS Firebase→Clerk Migration + Production Deployment — COMPLETE

## Executive Summary

C24 is the first full production trial of the UMH governed development loop. LyfeOS was migrated from Firebase to Clerk authentication and deployed to Fly.io with custom domain `lyfeos.net`, all executed through UMH's Meta IDE dispatching Claude Code sessions to Beast via the mesh relay.

**Result:** LyfeOS is live at https://lyfeos.net with valid TLS, Clerk auth, and Fly.io hosting in SJC region.

---

## Phase 1: Analysis (10 Governed Sessions via Beast Mesh Relay)

All sessions dispatched from VPS → Beast via `transports/node_mesh/server.py` HTTP relay (port 8095), executing `claude -p` on Beast's LyfeOS repo at `C:\dev\dev\LYFEOS`.

| # | Session | Result | Output |
|---|---------|--------|--------|
| 1 | Firebase Audit | ✅ PASS | 5,300 chars — mapped all Firebase dependencies |
| 2 | Migration Design | ✅ PASS | 1,896 chars — Clerk migration architecture |
| 3 | Schema Changes | ✅ PASS | 2,142 chars — clerkId column design |
| 4 | Server Auth Analysis | ✅ PASS | 10,267 chars — Express middleware mapping |
| 5 | Client Auth Analysis | ✅ PASS | 10,301 chars — React auth context mapping |
| 6 | OAuth Analysis | ✅ PASS | 9,249 chars — Google/Apple OAuth via Clerk |
| 7 | Migration Script | ✅ PASS | 8,368 chars — Firebase UID → Clerk ID mapping |
| 8 | Fly.io Deployment Config | ✅ PASS | 1,868 chars — fly.toml + Dockerfile design |
| 9 | PostHog Analytics | ✅ PASS | 2,880 chars — 11 tracked events |
| 10 | Verification Checklist | ✅ PASS | 1,442 chars — pre-deploy checklist |

**10/10 analysis sessions passed.**

## Phase 2: Code Changes (10 Governed Sessions via Beast Mesh Relay)

| # | Session | Result | What Changed |
|---|---------|--------|--------------|
| 11 | Install Clerk | ✅ PASS | `@clerk/clerk-react` + `@clerk/express` installed, config files created |
| 12 | Schema Migration | ✅ PASS | `clerkId` column added to users table, storage methods updated |
| 13 | ClerkProvider | ✅ PASS | `ClerkProvider` wired into `main.tsx` |
| 14 | Clerk Middleware | ✅ PASS | Webhook (user.created) + `requireAuth` middleware on routes |
| 15 | Client Auth Rewrite | ✅ PASS | `authContext.tsx` rewritten to Clerk, `firebase.ts` + `firebaseAuth.ts` deleted |
| 16 | Auth Pages Rewrite | ✅ PASS | 6 auth pages migrated (Login, Register, Forgot, Reset, Verify, Profile) |
| 17 | Server Auth Cleanup | ✅ PASS | 10 Firebase server routes deleted, `firebaseAdmin.ts` deleted, `firebase-admin` removed |
| 18 | Env & Cleanup | ✅ PASS | `firebase` npm package removed, FCM files deleted, env cleaned |
| 19 | Fly.io Config | ✅ PASS | `fly.toml` + multi-stage `Dockerfile` created |
| 20 | Build Verification | ✅ PASS | Vite build clean (420KB + esbuild 550KB), zero TS errors |

**10/10 code change sessions passed. 20/20 total governed sessions.**

## Phase 3: Clerk Application Setup

- Created separate Clerk application for LyfeOS (not shared with cockpit)
- Publishable key: `pk_live_...` stored in 1Password vault `UMH-Production`
- Secret key: `sk_live_...` stored in 1Password vault `UMH-Production`
- Configured on Beast at `C:\dev\dev\LYFEOS\.env` via 1Password `op` CLI

## Phase 4: Fly.io Deployment

- App: `lyfeos-app` in SJC region (changed from SEA for lower latency)
- Deployed via Beast mesh relay: `flyctl deploy --remote-only`
- Docker build args: `VITE_CLERK_PUBLISHABLE_KEY` passed as build-time ARG
- Fixed production server Vite import issue (commit `a8d116f0`)
- Fixed Clerk key Docker build arg passthrough (commit `afc38235`)
- Machine: `shared-cpu-1x`, 512MB RAM, health check passing

## Phase 5: Custom Domain DNS Configuration (Squarespace)

Added 4 DNS records on Squarespace for `lyfeos.net`:

| Type | Name | Data | Purpose |
|------|------|------|---------|
| A | @ | 66.241.125.58 | Apex → Fly.io IPv4 |
| AAAA | @ | 2a09:8280:1::131:88fb:0 | Apex → Fly.io IPv6 |
| A | www | 66.241.125.58 | WWW → Fly.io IPv4 |
| AAAA | www | 2a09:8280:1::131:88fb:0 | WWW → Fly.io IPv6 |

All 4 records propagated and verified via `dig`.

## Phase 6: TLS Certificate Provisioning

- `www.lyfeos.net` — cert auto-verified via A/AAAA records (Let's Encrypt RSA+ECDSA)
- `lyfeos.net` (apex) — required ACME DNS challenge, initially stuck on "Not verified"

## Phase 7: Apex Domain ACME Challenge Resolution

The apex domain cert wouldn't verify because Fly.io requires an ACME CNAME challenge record for apex domains. Added 2 additional DNS records on Squarespace:

| Type | Name | Data | Purpose |
|------|------|------|---------|
| CNAME | _acme-challenge | lyfeos.net.zk8exkx.flydns.net. | Let's Encrypt ACME challenge |
| TXT | _fly-ownership | app-zk8exkx | Fly.io ownership proof |

After adding records, removed and re-created the Fly.io cert to trigger fresh verification. Cert issued within 15 seconds.

## Phase 8: Production Verification

- **https://lyfeos.net** — loads correctly, redirects to `/waitlist`, shows LyfeOS landing page ✅
- **https://www.lyfeos.net** — loads correctly ✅
- **https://lyfeos-app.fly.dev** — loads correctly (Fly.io default domain) ✅
- Both certs: Let's Encrypt, Issued, Active, expires in 2 months ✅
- Health check: 1 total, 1 passing ✅
- Machine state: started, SJC region, version 8 ✅

## Phase 9: DNS Cleanup

- Deleted stale `replit-verify=8dec021f-845e-4b14-af75-37a0359b6d00` TXT record from Squarespace
- Verified via `dig` — only Google site verification TXT remains

## Final DNS State (9 custom records on Squarespace)

1. A @ → 66.241.125.58 (Fly.io)
2. AAAA @ → 2a09:8280:1::131:88fb:0 (Fly.io)
3. A www → 66.241.125.58 (Fly.io)
4. AAAA www → 2a09:8280:1::131:88fb:0 (Fly.io)
5. CNAME _acme-challenge → lyfeos.net.zk8exkx.flydns.net. (cert verification)
6. TXT _fly-ownership → app-zk8exkx (Fly.io ownership)
7. TXT google._domainkey → DKIM key (Google Workspace email)
8. TXT @ → google-site-verification=... (Google Workspace)
9. Plus preset records (Domain Connect CNAME, Google Workspace MX x5)

## Infrastructure Fixes During C24

- `_MAX_DISPATCH_TIMEOUT` in mesh server increased 180s → 600s (code changes need more time)
- Mesh server must be restarted standalone (not in Docker) to pick up timeout change
- Fly.io region changed from SEA → SJC for Clerk key configuration
- Docker build args required for Vite env vars (VITE_* inlined at build time)

## Key Metrics

- **Total governed sessions:** 20 (10 analysis + 10 code changes)
- **Success rate:** 100% (20/20)
- **Execution method:** UMH Meta IDE → Beast mesh relay → Claude Code CLI
- **Time span:** Analysis + code changes on 2026-06-21, deployment + DNS on 2026-06-22
- **Dependencies removed:** firebase, firebase-admin, all VITE_FIREBASE_* env vars
- **Dependencies added:** @clerk/clerk-react, @clerk/express
- **Files deleted:** firebase.ts, firebaseAuth.ts, firebaseAdmin.ts, firebase-messaging-sw.js
- **Auth pages migrated:** 6 (Login, Register, Forgot, Reset, Verify, Profile)
- **Firebase routes deleted:** 10
- **Build output:** Vite 420KB + esbuild 550KB, zero TS errors

## Significance

C24 is the first complete production trial of UMH's governed development loop — from analysis through code changes through deployment through DNS configuration, all orchestrated through the organism. The system dispatched 20 Claude Code sessions to Beast via mesh relay, each making real code changes on a real codebase, culminating in a live production deployment at lyfeos.net.
