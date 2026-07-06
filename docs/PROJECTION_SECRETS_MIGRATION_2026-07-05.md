# WP-P4-SECRETS-001 — Beast Projection Secrets → 1Password (2026-07-05)

**Governance record.** Operator-approved secrets quarantine. Migrated the real
secret-bearing `.env` files for the three Beast projection repos into 1Password,
converted loading to 1Password-backed references, and made real env files
git-ignored — before any env normalization or feature work.

**No secret VALUES appear in this document, the reconciliation data, the tests, or
any report.** Only key NAMES, counts, and `op://` reference paths are recorded.

## Law applied

> Source backup saved the work (#175). Secrets quarantine protects the work (this
> packet). Only after both are true can projection build-out safely resume.

Plaintext `.env` files were treated as contaminated until proven migrated and
ignored. They were **NOT deleted** — migrate + prove first; archival/removal is a
separate operator-approved step.

## Inventory (read-only, names + counts only)

| Projection | `.env` keys | `.env` was gitignored (before) | tracked/in-history |
|---|---|---|---|
| EntrepreneurOS | 11 | yes | no (never leaked) |
| CreatorOS | 3 | yes | no (never leaked) |
| LyfeOS | 6 | **NO** (the live gap) | no (never leaked) |

Key names migrated (NO values):
- **EntrepreneurOS:** DATABASE_URL, GEMINI_API_KEY, SESSION_SECRET, ANTHROPIC_API_KEY, OPENAI_API_KEY, STITCH_API_KEY, STITCH_PROJECT_ID, VITE_POSTHOG_API_KEY, VITE_CLERK_PUBLISHABLE_KEY, CLERK_SECRET_KEY, CLERK_PUBLISHABLE_KEY
- **CreatorOS:** DATABASE_URL, SESSION_SECRET, VITE_CLERK_PUBLISHABLE_KEY
- **LyfeOS:** DATABASE_URL, SESSION_SECRET, AI_INTEGRATIONS_ANTHROPIC_BASE_URL, AI_INTEGRATIONS_ANTHROPIC_API_KEY, GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET

## 1Password structure (one vault per app)

| Vault | Item | Fields | op:// reference base |
|---|---|---|---|
| `EntrepreneurOS` | `Development` | 11 concealed | `op://EntrepreneurOS/Development/<KEY>` |
| `CreatorOS` | `Development` | 3 concealed | `op://CreatorOS/Development/<KEY>` |
| `LyfeOS` | `Development` | 6 concealed | `op://LyfeOS/Development/<KEY>` |

All 20 `op://` references were verified to **resolve** (read-back exit-0; values
never printed). Migration ran ON the Beast (values read from local `.env`, piped to
`op item create`) — **secret values never transited the operator session, logs, or
/opt/OS.** The abandoned shared `Projection-Secrets` vault (empty) was deleted.

## Loading (1Password-backed)

Each repo now has a **committed** `.env.op.tpl` — only `op://` references, zero
plaintext values. Local run:

```
op run --env-file=.env.op.tpl -- npm run dev
```

## Gitignore hardening

Each repo's `.gitignore` gained (idempotent, guarded by a `WP-P4-SECRETS-001`
marker):

```
.env
.env.*
!.env.op.tpl
!.env.tpl
!.env.example
```

Verified after: `.env` is **IGNORED + untracked** in all three (previously LyfeOS
was not); `.env.op.tpl` is committable; **0 real env files are git-tracked** in any
repo.

## Verification (acceptance)

- All 20 `op://` refs resolve (LyfeOS 6, CreatorOS 3, EntrepreneurOS 11).
- `.env` ignored + untracked in all three (LyfeOS gap closed).
- `.env.op.tpl` committable + contains **0 value-shaped secrets**.
- 0 tracked env files in any repo; `.env` never in git history.
- Beast-side working scripts/temp files removed; `op` output held 0 value-shaped secrets.
- Plaintext `.env` files left in place (not deleted).

## NOT done (scope discipline)

- No plaintext `.env` deleted (awaits operator approval for archival/removal).
- No secret values exposed anywhere.
- No projection feature work, no env normalization beyond the loading template.
- No Beast app code copied into /opt/OS. No schema change. No P5.

## Required follow-on (operator-approved, separate)

1. **Archive/remove plaintext `.env`** on the Beast — ONLY after confirming apps run
   via `op run` (a boot verification). Migrate + prove is done; the delete is the
   final, separately-approved step.
2. **Commit `.env.op.tpl` + `.gitignore` changes** on each Beast repo (they're safe,
   no secrets) so the loading template + ignore rules are versioned — a small
   operator-approved Beast commit, or folded into the next backup.
