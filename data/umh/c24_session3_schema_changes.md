# C24 Session 3: Schema Changes

Generated via UMH governed development loop
Latency: 43249ms | Elapsed: 45s

Here's the full analysis:

---

## Schema Change Needed

**In `shared/schema.ts` line 24**, the users table has:
```ts
firebaseUid: text("firebase_uid"),
```

### Recommended change: **Add a `clerkId` column, keep `firebaseUid` temporarily**

This matches what your existing `FIREBASE_TO_CLERK_MIGRATION.md` already recommends. The change in `shared/schema.ts`:

```ts
// Add new column (line ~24 area)
clerkId: text("clerk_id").unique(),   // Clerk user ID

// Keep firebaseUid during transition, remove after 30 days
firebaseUid: text("firebase_uid"),    // DEPRECATED â€” remove after migration
```

And in the insert schema (line 561), add `clerkId: true` and eventually remove `firebaseUid: true`.

---

## All Files Referencing `firebaseUid` / `firebase_uid`

### Source files (must be updated):

| File | Lines | What it does |
|---|---|---|
| `shared/schema.ts` | 24, 561 | Column definition + insert schema pick |
| `server/storage.ts` | 46, 50, 320-321, 334-337 | `getUserByFirebaseUid()` interface method + implementation, `updateUserFirebaseUid()` interface method + implementation |
| `server/routes/auth.ts` | 124-132, 192-194, 251, 424-425, 444-457, 461, 484-487, 558, 617-618, 714-716, 740-741, 920, 975-976, 991-997, 1005-1006 | **Heavy usage** â€” registration, login, email verification, Google OAuth, custom token creation |

### No client-side references
Zero matches in `client/` â€” the frontend never touches `firebaseUid` directly.

### Non-source files (no code changes needed):
- `migrations/0000_hesitant_star_brand.sql` â€” initial migration (historical)
- `migrations/meta/0000â€“0006_snapshot.json` â€” Drizzle snapshots (auto-generated)
- `dump.sql` â€” database dump
- `FIREBASE_TO_CLERK_MIGRATION.md` â€” your existing migration plan

---

## Summary

**3 source files** need changes: `shared/schema.ts`, `server/storage.ts`, `server/routes/auth.ts`. The client is clean. The heaviest work is in `auth.ts` which has ~25+ references spanning registration, login, email verification, and OAuth flows. Storage needs equivalent `getUserByClerkId()` and `updateUserClerkId()` methods to replace the Firebase ones.