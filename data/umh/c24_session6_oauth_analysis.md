# C24 Session 6: Oauth Analysis

Generated via UMH governed development loop
Latency: 86056ms | Elapsed: 88s

Now I have the complete picture. Here's the full trace.

---

## Current Firebase OAuth Flow â€” End-to-End

### Flow 1: Google OAuth (Client-Side via Firebase SDK)

**Step 1 â€” User clicks "Sign in with Google"**
- `authContext.tsx:696` â†’ `loginWithGoogle(mode)` is called
- Saves `lyfeos-oauth-mode` + timestamp to localStorage (for redirect recovery)
- Calls `signInWithGoogle()` from `firebaseAuth.ts:121`

**Step 2 â€” Firebase popup/redirect decision** (`firebaseAuth.ts:53-119`)
- `signInWithProvider()` checks `isMobileBrowser()`
- **Mobile**: goes straight to `signInWithRedirect(auth, googleProvider)`, sets `lyfeos-oauth-redirect-pending` in localStorage
- **Desktop**: tries `signInWithPopup(auth, googleProvider)` first
  - If popup blocked/fails â†’ falls back to `signInWithRedirect()`
  - If user cancels â†’ returns `null` silently

**Step 3 â€” Firebase returns a `UserCredential`**
- **Popup path**: returns immediately to `loginWithGoogle()`, which calls `processOAuthResult(result, mode)`
- **Redirect path**: page reloads â†’ `authContext.tsx:150-309` `checkAuth()` useEffect detects `lyfeos-oauth-redirect-pending` in localStorage â†’ calls `checkRedirectResult()` â†’ elaborate fallback chain (800ms hydration wait â†’ `getRedirectResult()` â†’ `onAuthStateChanged` listener with 3s timeout â†’ 1s final wait â†’ retry `getRedirectResult`) â†’ eventually calls `processOAuthResult()`

**Step 4 â€” `processOAuthResult()` sends user data to server** (`authContext.tsx:68-136`)
- Extracts `{ displayName, email, uid, photoURL, providerData }` from the Firebase `UserCredential`
- Detects provider: checks if `providerData[0].providerId === 'apple.com'`
- POSTs to **`POST /api/auth/firebase`** with `{ uid, email, displayName, photoURL, mode, provider }`
- **Note: No Firebase ID token is sent or verified.** The server trusts the raw `uid` from the client.

**Step 5 â€” Server handles `POST /api/auth/firebase`** (`server/routes/auth.ts:531-658`)
- **Login mode** (`mode === 'login'`):
  - Looks up user by email via `storage.getUserByEmail(email)`
  - If not found â†’ returns `403` with `ACCOUNT_NOT_REGISTERED`
  - If found â†’ links `firebaseUid` if not already set
- **Register mode** (`mode === 'register'`):
  - If no existing user â†’ creates full user record (user, stats, profile, integrations, daily log) with `authProvider: 'google'|'apple'`
  - Sets `isNewUser = true`
- Both modes: creates express session (`req.session.userId`), processes login streak, logs activity, returns `{ user, isNewUser, onboardingCompleted, primaryColor }`

**Step 6 â€” Client handles server response** (`authContext.tsx:82-136`)
- If `ACCOUNT_NOT_REGISTERED` â†’ signs out of Firebase, toasts error, redirects to `/register`
- If `isNewUser` or `onboardingCompleted === false` â†’ redirects to `/onboarding`
- If returning user â†’ prefetches queries, redirects to `/login-success`

### Flow 2: Apple OAuth (Client-Side via Firebase SDK)

Identical to Google except:
- Uses `OAuthProvider("apple.com")` with scopes `email` and `name` (`firebaseAuth.ts:22-24`)
- Provider detection in `processOAuthResult` checks `providerData[0].providerId === 'apple.com'`
- Server stores `authProvider: 'apple'`

### Flow 3: Server-Side Google OAuth (Backup)

There's a **second, parallel** Google OAuth flow entirely server-side (`auth.ts:809-1025`):

- `GET /api/auth/google/start` â†’ generates CSRF state, redirects to Google consent screen
- `GET /api/auth/google/callback` â†’ exchanges auth code for tokens via `https://oauth2.googleapis.com/token`, fetches userinfo, creates/finds user (same logic as Flow 1), creates session, generates a Firebase custom token, redirects to `/login?google_auth_token=...&google_auth_mode=...`

This is a fallback for environments where the Firebase client SDK popup/redirect doesn't work.

---

## Custom Logic That Must Be Preserved

| Logic | Location | Must Preserve? |
|-------|----------|---------------|
| **Login vs Register mode enforcement** â€” login rejects unregistered emails with `ACCOUNT_NOT_REGISTERED` | `auth.ts:610-614`, `authContext.tsx:84-94` | **Yes** â€” Clerk doesn't enforce this by default. Need Clerk webhook or `signUp` vs `signIn` component separation |
| **New user provisioning** â€” creates stats, profile, integrations, daily log on first OAuth sign-in | `auth.ts:548-607` | **Yes** â€” move to Clerk `user.created` webhook |
| **`authProvider` field** â€” stores `'google'`, `'apple'`, or `'email'` on user record | `auth.ts:557` | **Yes** â€” derive from Clerk user's `externalAccounts` |
| **Login streak processing** â€” `processLoginStreak()` + `processDailyHealthUpdate()` on every sign-in | `auth.ts:625-629` | **Yes** â€” move to Clerk session webhook or call on `/api/auth/me` |
| **Activity logging** â€” `logActivityEvent(userId, 'login')` | `auth.ts:631` | **Yes** â€” same as above |
| **Default reminders init** â€” `initDefaultReminders(userId)` | `auth.ts:632` | **Yes** â€” move to user.created webhook |
| **Onboarding redirect** â€” new/incomplete users go to `/onboarding` | `authContext.tsx:107-113` | **Yes** â€” check `onboardingCompleted` from profile after Clerk auth |
| **Primary color loading** â€” theme color sent in auth response, applied on login | `auth.ts:639-641`, `authContext.tsx:100-102` | **Yes** â€” fetch from `/api/auth/me` or profile endpoint |
| **Firebase UID linking** â€” stores Firebase UID on user record for email verification/2FA | `auth.ts:617-619` | **Depends** â€” if migrating 2FA/email verification to Clerk, this goes away |
| **Pre-logout callbacks** â€” components save data before session clears | `authContext.tsx:58-66, 613-625` | **Yes** â€” keep in new auth context |
| **Mobile redirect recovery** â€” elaborate fallback chain for redirect OAuth on mobile | `authContext.tsx:175-277` | **No** â€” Clerk handles redirect flows internally |
| **Popup â†’ redirect fallback** â€” tries popup, falls back to redirect on failure | `firebaseAuth.ts:53-119` | **No** â€” Clerk handles this |
| **`firebaseUser` state** â€” exposed in auth context | `authContext.tsx:29, 49` | **No** â€” remove entirely |
| **Password reset via Firebase** â€” `sendPasswordReset`, `confirmPasswordReset` | `firebaseAuth.ts:181-209` | **No** â€” Clerk has built-in password reset |
| **Email verification via Firebase** â€” `sendVerificationEmail`, `applyVerificationCode` | `firebaseAuth.ts:153-229` | **No** â€” Clerk handles email verification |
| **Custom token generation** â€” `createCustomToken` for Firebase client auth | `firebaseAdmin.ts:128-138`, `auth.ts:438-469` | **No** â€” only exists to bridge serverâ†’client Firebase auth |
| **Server-side Google OAuth** (`/api/auth/google/start`, `/callback`) | `auth.ts:809-1025` | **No** â€” redundant with Clerk |

---

## How Clerk Social OAuth Replaces This

### What Clerk handles automatically (delete all of this):
1. **OAuth provider configuration** â€” Google/Apple configured in Clerk Dashboard, not in code
2. **Popup vs redirect logic** â€” `<SignIn>` / `<SignUp>` components handle it
3. **Mobile browser detection & fallback chains** â€” gone entirely
4. **Firebase SDK initialization** (`firebase.ts`, `firebaseAuth.ts`) â€” deleted
5. **Firebase Admin SDK** (`firebaseAdmin.ts`) â€” deleted (unless kept temporarily for push notifications)
6. **`POST /api/auth/firebase`** route â€” deleted
7. **Server-side Google OAuth routes** (`/start`, `/callback`) â€” deleted
8. **Session management** (`express-session`) â€” replaced by Clerk session tokens (JWT)
9. **Password hashing** (`bcrypt`) â€” Clerk manages passwords
10. **Email verification flow** â€” Clerk built-in
11. **Password reset flow** â€” Clerk built-in

### What you must rebuild with Clerk:
1. **`user.created` webhook** â€” receives Clerk webhook when new user signs up â†’ creates stats, profile, integrations, daily log, default reminders
2. **`session.created` webhook** (or middleware on `/api/auth/me`) â€” processes login streak, daily health update, activity logging
3. **Auth context rewrite** â€” replace `AuthProvider` internals:
   - `useAuth()` from `@clerk/clerk-react` replaces Firebase auth state
   - `user` comes from Clerk's `useUser()`, mapped to your DB user
   - `loginWithGoogle` / `loginWithApple` â†’ replaced by `<SignIn>` component with social buttons
   - Onboarding redirect logic stays, driven by your DB's `onboardingCompleted` flag
   - Pre-logout callbacks stay
4. **Server middleware** â€” replace `isAuthenticated` (currently checks `req.session.userId`) with Clerk's `clerkMiddleware()` + `getAuth(req)`
5. **User lookup** â€” currently by email. After Clerk, look up by `clerkUserId` (store Clerk's `user.id` in your DB) or by email from `getAuth(req)`