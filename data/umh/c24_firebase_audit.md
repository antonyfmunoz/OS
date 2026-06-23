# C24 Firebase Audit — LyfeOS

Generated via UMH governed development loop: cockpit → plan → approve → dispatch to Beast → Claude CLI

Here's the complete Firebase dependency map for the LYFEOS project:

---

## NPM Packages

| Package | Version | Location |
|---------|---------|----------|
| `firebase` | ^11.6.1 | `package.json:72` â€” Client SDK |
| `firebase-admin` | ^13.6.1 | `package.json:73` â€” Server Admin SDK |

---

## Environment Variables (`.env`)

| Variable | Type |
|----------|------|
| `VITE_FIREBASE_API_KEY` | Config |
| `VITE_FIREBASE_VAPID_KEY` | Config (FCM push) |
| `VITE_FIREBASE_APP_ID` | Config |
| `VITE_FIREBASE_PROJECT_ID` | Config |
| `VITE_FIREBASE_ACTUAL_PROJECT_ID` | Config |
| `VITE_FIREBASE_AUTH_DOMAIN` | Config |
| `VITE_FIREBASE_MESSAGING_SENDER_ID` | Config |
| `FIREBASE_SERVICE_ACCOUNT_KEY` | Config (server-side, referenced in code) |

---

## Source Files

### Client-side

| File | Firebase Service | Classification |
|------|-----------------|----------------|
| `client/src/lib/firebase.ts` | **Auth, Firestore** | **Config** â€” Initializes Firebase app, Auth (with persistence), and Firestore. Exports `app`, `auth`, `db`. |
| `client/src/lib/firebaseAuth.ts` | **Auth** | **API calls** â€” Google/Apple OAuth (popup + redirect), email/password sign-in, email verification, password reset, custom token sign-in, action code verification. |
| `client/src/lib/authContext.tsx` | **Auth** | **API calls + Import** â€” `onAuthStateChanged` listener, Firebase OAuth flow orchestration, `signInWithGoogle`, `signInWithApple`, `firebaseSignInWithEmail`, sign-out from Firebase. |
| `client/src/hooks/usePushNotifications.ts` | **Cloud Messaging (FCM)** | **API calls** â€” `getMessaging`, `getToken`, `deleteToken`, `onMessage` for foreground notifications. Registers service worker and sends config. |
| `client/src/pages/ProfilePage.tsx` | **Auth (Phone)** | **API calls** â€” `RecaptchaVerifier`, `signInWithPhoneNumber` for phone 2FA verification. Calls `verify-email-firebase` and `verify-phone-firebase` server endpoints. |
| `client/src/pages/VerifyEmailPage.tsx` | **Auth** | **API calls** â€” `applyVerificationCode` (action code), checks `auth.currentUser.emailVerified`. |
| `client/src/pages/ResetPasswordPage.tsx` | **Auth** | **API calls** â€” `verifyPasswordResetCode`, `confirmPasswordReset`, `firebaseSignInWithEmail`, calls `reset-password-firebase` server endpoint. |
| `client/src/pages/ForgotPasswordPage.tsx` | **Auth** | **API calls** â€” `sendPasswordReset`, calls `ensure-firebase-user` server endpoint. |
| `client/src/components/dailyInit/DailyInitModal.tsx` | *(reference only)* | **Import** â€” Comment referencing Firebase-specific fields, no direct Firebase calls. |
| `client/public/firebase-messaging-sw.js` | **Cloud Messaging (FCM)** | **Config + API calls** â€” Service worker. Imports Firebase compat SDKs via CDN, handles `onBackgroundMessage`, push events, notification clicks. |

### Server-side

| File | Firebase Service | Classification |
|------|-----------------|----------------|
| `server/firebaseAdmin.ts` | **Auth (Admin)** | **Config + API calls** â€” Initializes Firebase Admin with service account. Exports: `verifyFirebaseIdToken`, `createFirebaseUser`, `getFirebaseUserByEmail`, `checkFirebaseEmailVerified`, `createCustomToken`, `updateFirebaseUserPassword`. |
| `server/routes/auth.ts` | **Auth (Admin)** | **API calls** â€” Registration creates Firebase users, login/OAuth syncs `firebaseUid`, email verification sync, custom token generation, phone 2FA token verification, password reset via Firebase ID token. |
| `server/notificationScheduler.ts` | **Cloud Messaging (Admin)** | **API calls** â€” `admin.messaging().send()` for push notifications: mission reminders, streak reminders, smart reminders. Manages invalid token cleanup. |
| `server/index.ts` | *(proxy)* | **Config** â€” Sets up HTTP proxy to `{projectId}.firebaseapp.com` for Firebase Auth domain. Rate-limits Firebase auth endpoints. |
| `server/storage.ts` | *(database layer)* | **Import** â€” `getUserByFirebaseUid`, `updateUserFirebaseUid` â€” stores/retrieves Firebase UIDs in PostgreSQL. |

### Schema / Database

| File | Firebase Service | Classification |
|------|-----------------|----------------|
| `shared/schema.ts` | *(data model)* | **Schema** â€” `firebaseUid` column on `users` table (`text("firebase_uid")`). |
| `migrations/0000_hesitant_star_brand.sql` + `migrations/meta/*.json` | *(data model)* | **Schema** â€” Migration files containing `firebase_uid` column definition. |

---

## Summary by Firebase Service

| Service | Where Used |
|---------|-----------|
| **Auth (Client)** | `firebase.ts`, `firebaseAuth.ts`, `authContext.tsx`, `ProfilePage.tsx`, `VerifyEmailPage.tsx`, `ResetPasswordPage.tsx`, `ForgotPasswordPage.tsx` |
| **Auth (Admin)** | `firebaseAdmin.ts`, `auth.ts` (routes) |
| **Cloud Messaging / FCM (Client)** | `usePushNotifications.ts`, `firebase-messaging-sw.js` |
| **Cloud Messaging / FCM (Admin)** | `notificationScheduler.ts` |
| **Firestore (Client)** | `firebase.ts` (initialized but no active queries found) |
| **Storage** | Not used |
| **Functions** | Not used |