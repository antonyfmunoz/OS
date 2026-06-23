# C24 Session 10: Verification Checklist

Generated via UMH governed development loop
Latency: 149933ms | Elapsed: 153s

Created `MIGRATION_VERIFICATION_CHECKLIST.md` with **106 checks** across 7 sections:

1. **Auth Flows (27 checks)** â€” email/password, Google OAuth, Apple OAuth, email verification, password reset, phone 2FA â€” each with specific pass/fail criteria
2. **Push Notifications (7-13 checks)** â€” split into Option A (keep FCM) and Option B (migrate to Web Push), so you verify whichever path you choose
3. **Database (12 checks)** â€” `clerk_user_id` column, data integrity, webhook sync, `firebaseUid` deprecation timeline
4. **Environment (16 checks)** â€” every `VITE_FIREBASE_*` var mapped to remove/retain status, plus Clerk vars confirmed across `.env`, Dockerfile, `fly.toml`, and `.replit`
5. **Server (16 checks)** â€” all 6 Firebase endpoints removed, `firebaseAdmin.ts` replaced, Clerk middleware installed, webhook endpoint verified
6. **Client (16 checks)** â€” both Firebase files deleted, all imports gone, `ClerkProvider` wrapping app, grep-based proof of zero Firebase auth remnants
7. **Build & Deploy (12 checks)** â€” clean build, Docker/Fly.io deploy, and a 12-point production smoke test

The scorecard at the bottom gives you a single view of migration completeness. Rollback criteria are defined: keep `firebaseUid` and the Firebase project live for 30 days.