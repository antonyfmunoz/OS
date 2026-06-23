# C24 Session 7: User Migration Script

Generated via UMH governed development loop
Latency: 83000ms | Elapsed: 87s

Now I have full context. Here's the migration script design.

---

## Firebase â†’ Clerk User Migration Script Design

### What we're working with

**Users table** (`shared/schema.ts:7-41`):
- `id` (serial PK) â€” internal DB id
- `email` â€” may be null for OAuth-only users
- `firebaseUid` â€” current auth identifier
- `authProvider` â€” `"email"`, `"google"`, `"apple"`, `"facebook"`
- `password` â€” bcrypt hash (only for email/password users, server-side)
- `firstName`, `lastName`, `displayName`, `username`
- `emailVerified`, `phoneNumber`, `phoneVerified`
- No `clerkUserId` column yet â€” needs migration

**Database** (`server/db.ts`): Drizzle ORM + `pg.Pool` via `DATABASE_URL`

**Existing methods** (`server/storage.ts:320-339`):
- `getUserByFirebaseUid(firebaseUid)` â€” lookup by Firebase UID
- `updateUserFirebaseUid(id, firebaseUid)` â€” update Firebase UID on user row

---

### Migration Script Design

```
scripts/migrate-firebase-to-clerk.ts
```

#### Step 0: Schema migration (run first)

```sql
ALTER TABLE users ADD COLUMN clerk_user_id TEXT;
CREATE UNIQUE INDEX idx_users_clerk_user_id ON users(clerk_user_id);
```

#### Step 1: Fetch all Postgres users

```pseudo
allUsers = db.select().from(users)
                      .where(users.firebaseUid IS NOT NULL)

// Split into two buckets
emailPasswordUsers = allUsers.filter(u => u.authProvider === "email" && u.email)
oauthUsers         = allUsers.filter(u => u.authProvider IN ("google", "apple", "facebook"))
```

#### Step 2: Migrate email/password users

```pseudo
for each user in emailPasswordUsers:
    // Check if already migrated
    if user.clerkUserId is not null:
        skip, log "already migrated"
        continue

    try:
        // Option A: Import with Firebase scrypt hash (preferred)
        // Clerk supports Firebase scrypt hash import via their API
        // This preserves existing passwords â€” no reset needed
        clerkUser = clerkClient.users.createUser({
            emailAddress: [user.email],
            firstName: user.firstName,
            lastName: user.lastName,
            username: user.username,    // if unique constraint allows
            passwordHasher: "firebase_scrypt",  // Clerk's built-in support
            passwordDigest: <firebase_password_hash>,
            // Firebase scrypt config from Firebase console:
            // hashConfig.signerKey, hashConfig.saltSeparator, 
            // hashConfig.rounds, hashConfig.memoryCost
            externalId: user.firebaseUid,  // preserve for traceability
            skipPasswordChecks: true,
        })

        // Option B: If no Firebase hash available (our case â€” passwords
        // are bcrypt in Postgres, not Firebase scrypt), create without
        // password. User must "Forgot Password" on first login.
        clerkUser = clerkClient.users.createUser({
            emailAddress: [user.email],
            firstName: user.firstName,
            lastName: user.lastName,
            username: user.username,
            externalId: String(user.id),
            skipPasswordChecks: true,
        })

        // Map clerk ID back to Postgres
        db.update(users)
          .set({ clerkUserId: clerkUser.id })
          .where(eq(users.id, user.id))

        log SUCCESS: user.id â†’ clerkUser.id

    catch error:
        if error.code === "email_already_exists":
            // User already exists in Clerk (e.g. they signed up during migration)
            existingClerkUsers = clerkClient.users.getUserList({
                emailAddress: [user.email]
            })
            clerkUser = existingClerkUsers[0]
            db.update(users)
              .set({ clerkUserId: clerkUser.id })
              .where(eq(users.id, user.id))
            log LINKED: user.id â†’ clerkUser.id
        else:
            log FAILED: user.id, error
            append to failedUsers[]
```

#### Step 3: Migrate OAuth users

```pseudo
for each user in oauthUsers:
    if user.clerkUserId is not null:
        skip
        continue

    try:
        // OAuth users can't be "imported" with their OAuth token.
        // Create a placeholder Clerk user with their email.
        // When they next sign in via Google/Apple on Clerk,
        // Clerk will match by email and link automatically
        // (if "link accounts with matching email" is ON in Clerk dashboard).

        clerkUser = clerkClient.users.createUser({
            emailAddress: user.email ? [user.email] : [],
            firstName: user.firstName,
            lastName: user.lastName,
            externalId: String(user.id),
            skipPasswordChecks: true,
        })

        db.update(users)
          .set({ clerkUserId: clerkUser.id })
          .where(eq(users.id, user.id))

        log SUCCESS: user.id â†’ clerkUser.id (OAuth: user.authProvider)

    catch error:
        // Same email-exists handling as above
        handleDuplicate(user, error)
```

#### Step 4: Handle users without email

```pseudo
noEmailUsers = allUsers.filter(u => !u.email)

for each user in noEmailUsers:
    // These users authenticated via phone or have incomplete profiles.
    // If they have a phoneNumber, create with phone.
    // Otherwise, log as manual review needed.

    if user.phoneNumber:
        clerkUser = clerkClient.users.createUser({
            phoneNumber: [user.phoneNumber],
            firstName: user.firstName,
            lastName: user.lastName,
            externalId: String(user.id),
        })
        // map clerkUserId
    else:
        log MANUAL_REVIEW: user.id â€” no email, no phone
        append to manualReviewUsers[]
```

#### Step 5: Verification pass

```pseudo
// After migration, verify every user got mapped
unmapped = db.select().from(users)
             .where(users.firebaseUid IS NOT NULL)
             .where(users.clerkUserId IS NULL)

if unmapped.length > 0:
    log WARNING: {unmapped.length} users still unmapped
    write unmapped to migration-failures-YYYY-MM-DD.json
else:
    log ALL USERS MIGRATED SUCCESSFULLY

// Summary report
log {
    total: allUsers.length,
    emailPassword: { attempted, succeeded, failed },
    oauth: { attempted, succeeded, failed },
    noEmail: { attempted, succeeded, manualReview },
}
```

---

### Script structure

```
scripts/
  migrate-firebase-to-clerk.ts    // Main migration runner
  migration-report-YYYY-MM-DD.json // Generated output

// Run with:
// npx tsx scripts/migrate-firebase-to-clerk.ts --dry-run   (preview only)
// npx tsx scripts/migrate-firebase-to-clerk.ts              (execute)
```

### Key design decisions

| Decision | Rationale |
|---|---|
| **`externalId` = Postgres `users.id`** | Gives Clerk a stable reference back to your DB. More useful than storing firebaseUid since that's being deprecated. |
| **Batch with rate limiting** | Clerk API has rate limits. Process in batches of 20 with 1s delays between batches. |
| **`--dry-run` flag** | First run logs what *would* happen without touching Clerk or Postgres. Non-negotiable for safety. |
| **Idempotent** | Checks `clerkUserId IS NULL` before each user. Safe to re-run after failures. |
| **Email/password users get no password** | Your `password` column is bcrypt (server-side), not Firebase scrypt. Clerk can't import bcrypt. These users reset their password on first Clerk login. Alternatively, if you have the Firebase project's scrypt hash config, export hashes from Firebase directly and use Clerk's `firebase_scrypt` hasher. |
| **OAuth users = email-only placeholders** | Clerk auto-links when they sign in via Google/Apple again, as long as "link accounts with matching verified email" is enabled in Clerk Dashboard â†’ Settings. |
| **Keep `firebaseUid` column for 30 days** | Rollback safety per your existing migration plan. Drop after confirming stable. |

### New storage methods needed (post-migration)

```typescript
// Add to server/storage.ts
async getUserByClerkId(clerkUserId: string): Promise<User | undefined> {
    const [user] = await db.select().from(users)
        .where(eq(users.clerkUserId, clerkUserId));
    return user;
}
```

This replaces `getUserByFirebaseUid` as the primary auth lookup once Clerk is live.