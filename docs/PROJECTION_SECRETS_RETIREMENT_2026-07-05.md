# Plaintext `.env` Retirement — Beast Projection Repos

**Packet:** WP-P4-SECRETS-RETIRE-001
**Date:** 2026-07-05
**Precedes:** any projection feature work
**Follows:** WP-P4-SECRETS-001 (#176 migration) → WP-P4-SECRETS-RUNTIME-001 (#177 protocol)

---

## Goal

Retire the plaintext `.env` files on the Beast projection repos — **only after** proving each
repo can boot through the standard UMH 1Password Secret Runtime Protocol. Migration and the
runtime commit were already proven; this packet closes the liability by removing the plaintext
files from the loaded path, without deleting anything blind.

## The rule enforced

> Do not delete plaintext `.env` until op-run boot/smoke passes.
> Archive, don't blind-delete. Prove the app still boots afterward.

## Preconditions verified per repo (before any `.env` was touched)

For EntrepreneurOS, CreatorOS, LyfeOS on their operating branch:

| Check | Result |
|---|---|
| `git check-ignore .env` | IGNORED (all 3) |
| `.env.op.tpl` contains only `op://` refs | 0 plaintext lines (11 / 3 / 6 refs) |
| op refs resolve without printing values | verified last packet (`ALL_11/3/6_KEYS_INJECTED`) |
| **app boot/smoke through op run** | **BOOT_OK** (see below) |

### Boot smoke (the decisive gate)

Each app's real env-consuming server module was dynamically imported **under `op run`**
(forces `DATABASE_URL` / provider-key resolution + client construction — the actual boot path,
no port bind, no writes). Captured **only** the pass/fail marker and exit code — never env, never values.

| Repo | Module imported | Result |
|---|---|---|
| EntrepreneurOS | `server/ai/gateway.ts` | `BOOT_OK` (exit 0) |
| CreatorOS | `server/db.ts` | `BOOT_OK` (exit 0) |
| LyfeOS | `server/db.ts` | `BOOT_OK` (exit 0) |

## Retirement action (archive-outside-git)

Only after the boot smoke passed, each plaintext `.env` was **moved out of the repo working
tree entirely**:

```
C:\dev\dev\<repo>\.env   ->   C:\dev\_env_archive\<repo>\.env.retired-20260705
```

- **Outside Git** — the archive lives outside any repo, so it is not even a staging candidate.
- **Never committed, never uploaded.**
- **Recoverable** during a burn-in period (moved, not deleted).

Post-move state per repo: `moved=True`, `still_in_repo=False`, `git status` shows no `.env`.

## Post-retirement verification (proves nothing broke)

Each app's boot smoke was **re-run after the archive**, with **no local `.env` present**:

| Repo | Post-archive smoke |
|---|---|
| EntrepreneurOS | `BOOT_OK` (exit 0) |
| CreatorOS | `BOOT_OK` (exit 0) |
| LyfeOS | `BOOT_OK` (exit 0) |

Secrets are now sourced **purely from 1Password** via `op run` — no repo depends on a local
plaintext `.env`. LyfeOS's WIP (28 dirty / 21 source files) was **untouched** by retirement
(no reset/clean/stash/discard).

## Status

All three projections: **plaintext `.env` retired**. See
`data/umh/projection_reconciliation/secrets_runtime_status.json`
(`plaintext_env_retirement` block + per-system `op_run_boot_smoke` and
`plaintext_env_retired_or_pending: "retired ..."`).

The archived files remain on the Beast (outside Git) as a recoverable burn-in safety net; a
later operator may hard-delete them once confident. UMH substrate carries no plaintext `.env`
in-tree and is unaffected.

## Constraints honored

No feature work · no env normalization beyond the approved protocol · no secret values
printed/copied/logged/staged/committed/sent to `/opt/OS` · no `git add -A` · no
reset/clean/stash/discard of LyfeOS WIP · plaintext `.env` not deleted until op-run boot passed ·
archival was an operator-approved Beast action · `/opt/OS` records key names/counts/status/`op://`
references only.
