# schema.ts Conflict Resolution Proposal

> Date: 2026-05-12
> Status: PROPOSAL — awaiting manual resolution
> File: /opt/OS/saas/db/schema.ts

---

## Conflict Structure

The entire file (978 lines) is a single conflict region:

```
Line   1: <<<<<<< Updated upstream
Lines  2-541: "ours" (upstream) — 540 lines
Line 542: =======
Lines 543-977: "theirs" (stashed) — 435 lines
Line 978: >>>>>>> Stashed changes
```

## Diff Summary

| Aspect | Upstream (ours) | Stashed (theirs) |
|--------|-----------------|------------------|
| Tables | 21 (incl. clients, transactions, fulfillmentEvents, offers) | 17 (without those 4) |
| Enums | 7 (identical both sides) | 7 (identical both sides) |
| Zod validators | Present | Present |
| pgvector custom type | Present | Present |
| Lines | 540 | 435 |

### Tables only in upstream (ours)

```typescript
export const clients      // CRM client tracking
export const transactions // Financial transactions
export const fulfillmentEvents // Fulfillment lifecycle
export const offers       // Offer management
```

### Tables identical in both sides

```
users, portfolios, organizations, orgMembers, ventures,
agents, userAgentSessions, skills, events, skillVersions,
workflows, interactions, outcomes, humanProfiles, approvals,
embeddings
```

Note: while the same tables exist in both, column-level differences
exist (upstream has more refined column definitions and comments).

## Git History

```
817bef69 sync local changes to github — vault, agents, skills, saas-dev-skill
67b619d2 refactor: single execution spine + meta harness + eos mvp
5730d42f refactor: production reorganization — structure, skills, templates, fixes
```

The conflict was introduced by a `git stash pop` against a newer upstream,
and the conflict markers were committed directly without resolution.

## Migration Impact

8 migration files exist in `saas/db/migrations/`:
- 0000 through 0008 (0004 missing from sequence)

`grep` for the 4 upstream-only tables (`clients`, `transactions`,
`fulfillment_events`, `offers`) found **zero matches** in migration files.
This means:
1. These tables have never been migrated to production
2. Keeping them in schema.ts is forward-looking (they define future tables)
3. Removing them would not break any existing migration

## Recommendation

**Keep upstream (ours).** Rationale:

1. Upstream is the superset — it contains everything stashed has plus 4 new tables
2. Upstream has more refined column definitions and documentation
3. No migration depends on either side exclusively
4. The stashed version is strictly older (fewer tables, less documentation)

### Resolution command (when approved)

```bash
cd /opt/OS
# Extract upstream side (lines 2-541) as the resolution
sed -n '2,541p' saas/db/schema.ts > /tmp/schema_resolved.ts
cp /tmp/schema_resolved.ts saas/db/schema.ts
# Verify no conflict markers remain
grep -c "<<<<<<\|>>>>>>" saas/db/schema.ts  # should be 0
```

### Alternative: manual merge

If specific columns from the stashed version are preferred, a manual
side-by-side diff is needed. The column-level differences span ~100 lines
across the shared 17 tables.

## Risk Assessment

- **LOW**: No production database depends on this schema file currently
  (saas/ is pre-deployment TypeScript/React application)
- **LOW**: No migration references the conflicting tables
- **MEDIUM**: If drizzle-kit generate is run against this file with
  conflict markers, it will produce a broken migration
