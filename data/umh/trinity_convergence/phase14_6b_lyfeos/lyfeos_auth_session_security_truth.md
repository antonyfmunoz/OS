# LyfeOS Auth, Session, and Security Current Truth

**Phase:** 14.6B-LyfeOS
**Artifact:** 37
**Operator Approved:** false
**Allows Implementation:** false

---

## Authentication Architecture

LyfeOS uses a **dual auth system**: Passport.js for local login + Firebase for OAuth/verification/2FA.

### Local Auth (Passport.js)
- **Strategy:** passport-local
- **Password hashing:** bcrypt v6.0.0 (in package.json dependencies)
  - Note: replit.md mentions both "scrypt" and "bcrypt" — package.json confirms bcrypt is the installed dependency
- **Registration flow:**
  1. User submits email + password
  2. Server creates Firebase Auth user via Admin SDK
  3. Server creates local database user with bcrypt-hashed password
  4. Session created
- **Login flow:**
  1. User submits email + password
  2. bcrypt validates password against PostgreSQL stored hash
  3. Session created
- **Provenance:** CODE_RESOLVED_CURRENT_TRUTH

### Firebase OAuth
- **Providers:** Google, Apple, Facebook
- **Flow:** Client-side Firebase SDK initiates OAuth -> Firebase returns ID token -> Server verifies via Admin SDK -> Session created
- **Reverse proxy:** `/__/auth/*` routes proxy to Firebase for same-origin OAuth (avoids 3rd-party cookie blocking in Safari/Chrome)
- **Auth domain:** Set to app's own domain (not firebaseapp.com) for same-origin flows
- **Provenance:** CODE_RESOLVED_CURRENT_TRUTH

---

## Session Management

| Property | Value | Provenance |
|----------|-------|------------|
| Library | express-session v1.18.1 | CODE_RESOLVED_CURRENT_TRUTH |
| Primary store | connect-pg-simple (PostgreSQL) | CODE_RESOLVED_CURRENT_TRUTH |
| Fallback store | memorystore v1.6.7 | CODE_RESOLVED_CURRENT_TRUTH |
| Max age | 7 days | CODE_RESOLVED_CURRENT_TRUTH |
| Secure cookies | In production only | CODE_RESOLVED_CURRENT_TRUTH |
| Trust proxy | Enabled | CODE_RESOLVED_CURRENT_TRUTH |
| Session secret | From `SESSION_SECRET` env var | CODE_RESOLVED_CURRENT_TRUTH |

### Security Risk: Session Secret Auto-Generation
If `SESSION_SECRET` is not set, the application auto-generates one. This means:
- Sessions are invalidated on every server restart
- The generated secret may not be cryptographically strong enough
- **Risk level:** MEDIUM
- **Classification:** INFERRED_PROFESSIONAL_GAP

### Memory Store Fallback
If PostgreSQL session store fails, falls back to in-memory store (memorystore). This means:
- Sessions lost on restart
- Memory grows with session count (no disk persistence)
- Acceptable for development, problematic for production
- **Risk level:** LOW (fallback only, not primary)
- **Classification:** IMPLEMENTATION_DEBT

---

## Email Verification and Password Reset

| Function | Provider | Mechanism |
|----------|----------|-----------|
| Email verification | Firebase Auth | Firebase native email verification flow |
| Password reset | Firebase Auth | Firebase native password reset flow |
| Email sending | Firebase (native) | Resend previously used, now removed |

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

---

## Two-Factor Authentication (2FA)

### Email 2FA
- Firebase email verification codes
- `two_factor_email_code` + `two_factor_email_expiry` in users table
- **Provenance:** CODE_RESOLVED_CURRENT_TRUTH

### Phone 2FA
- Firebase Phone Authentication
- Uses `RecaptchaVerifier` + `signInWithPhoneNumber` on frontend
- `two_factor_phone_code` + `two_factor_phone_expiry` in users table
- `phone_verified` boolean tracks verification state
- No separate SMS provider needed (Firebase handles it)
- Twilio was previously used, now removed
- Requires `FIREBASE_SERVICE_ACCOUNT_KEY` for full functionality
- **Provenance:** CODE_RESOLVED_CURRENT_TRUTH

---

## Security Headers and Middleware

| Feature | Status | Provenance |
|---------|--------|------------|
| Helmet.js | Installed (in dependencies) | CODE_RESOLVED_CURRENT_TRUTH |
| Compression | gzip via compression middleware | CODE_RESOLVED_CURRENT_TRUTH |
| Input validation | Zod schemas (drizzle-zod) | CODE_RESOLVED_CURRENT_TRUTH |
| CSRF protection | NOT confirmed | INFERRED_PROFESSIONAL_GAP |
| Rate limiting | NOT confirmed in production | INFERRED_PROFESSIONAL_GAP |
| CORS configuration | NOT documented | INFERRED_PROFESSIONAL_GAP |
| Content Security Policy | NOT confirmed | INFERRED_PROFESSIONAL_GAP |

---

## Security Assessment Summary

### Confirmed Working
- bcrypt password hashing
- Express-session with PostgreSQL store
- Firebase OAuth (Google/Apple/Facebook)
- Firebase email verification and password reset
- Firebase Phone 2FA
- Helmet.js security headers (installed)
- Zod input validation
- Parameterized queries via Drizzle ORM (SQL injection prevention)

### Confirmed Gaps (INFERRED_PROFESSIONAL_GAP)
1. **No RLS** — all data isolation is application-level only
2. **No rate limiting confirmed** — auth and AI endpoints are unbounded
3. **No CORS configuration documented** — cross-origin request handling unclear
4. **No CSP confirmed** — content security policy status unknown
5. **No CSRF protection confirmed** — cross-site request forgery mitigation unknown
6. **Session secret auto-generation** — production risk if env var not set
7. **OAuth token encryption unknown** — integrations table stores access/refresh tokens
8. **No security audit performed** — no penetration testing or security review

### Legacy/Stub Fields in Users Table
- `stripe_customer_id` — Stripe removed but field remains
- `stripe_subscription_id` — Stripe removed but field remains
- `email_verification_token` — possibly legacy (Firebase handles verification now)
- `password_reset_token` — possibly legacy (Firebase handles reset now)

---

## Recommendations for Hardening

1. **P0:** Verify `SESSION_SECRET` is set in production environment
2. **P0:** Audit OAuth token storage encryption
3. **P1:** Implement rate limiting on auth endpoints and AI chat endpoint
4. **P1:** Configure CORS properly for production domain
5. **P1:** Add CSRF protection middleware
6. **P2:** Add CSP headers via Helmet configuration
7. **P2:** Remove legacy auth fields if Firebase handles verification/reset
8. **P2:** Remove Stripe stubs or add migration plan
9. **P3:** RLS policies on all user-scoped tables
