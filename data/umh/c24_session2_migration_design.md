# C24 Session 2: Migration Design

Generated via UMH governed development loop
Latency: 51817ms | Elapsed: 54s

The migration plan already exists and is comprehensive. `FIREBASE_TO_CLERK_MIGRATION.md` (288 lines) covers everything you asked for:

**What's already documented:**

1. **Firebase service â†’ Clerk mapping** â€” Full table covering all 16 Firebase APIs (client auth, admin SDK, FCM, Firestore) with their exact Clerk equivalents

2. **File-by-file audit** â€” All 17 files organized into 6 tiers with effort estimates (S/M/L/XL):
   - **Tier 1** (Core infra): `firebase.ts`, `firebaseAuth.ts`, `firebaseAdmin.ts`, `authContext.tsx` â€” delete/rewrite
   - **Tier 2** (Server routes): `auth.ts`, `index.ts`, `storage.ts` â€” heavy rewrite
   - **Tier 3** (Client pages): `ProfilePage.tsx`, `ForgotPasswordPage.tsx`, `ResetPasswordPage.tsx`, `VerifyEmailPage.tsx` â€” moderate
   - **Tier 4** (FCM): `usePushNotifications.ts`, `firebase-messaging-sw.js`, `notificationScheduler.ts` â€” separate decision
   - **Tier 5** (Schema): `schema.ts`, `goals.ts` â€” column changes
   - **Tier 6** (Dead code): `DailyInitModal.tsx` â€” comment removal

3. **5-phase migration order** with zero-downtime progression:
   - Phase 1: Foundation (additive, no breaks)
   - Phase 2: Client auth rewrite (6 files, 3 deleted)
   - Phase 3: Server auth rewrite (highest risk â€” session model change)
   - Phase 4: Cleanup & DB column drop
   - Phase 5: FCM decision (keep vs migrate to Web Push)

4. **Breaking changes** â€” 7 client-side, 5 server-side, 3 database-level

5. **User migration strategy** â€” Firebase scrypt hash import, OAuth seamless, rollback plan with 30-day `firebaseUid` retention

6. **Env var changes**, **package additions/removals**, and **risk mitigation table**

One file the grep found that the doc missed: `server/routes/google.ts` â€” it imports `getAuth`/`initializeApp`. Worth checking if that needs to be added to the plan. Want me to audit that file and update the migration doc?