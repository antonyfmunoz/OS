# UMH 1Password Secret Runtime Protocol

**Packet:** WP-P4-SECRETS-RUNTIME-001
**Status:** active — governs UMH substrate + all projection repos
**Recorded:** 2026-07-05

---

## The law

> Secrets are not repo state.
> Secrets are not branch state.
> Secrets are **runtime authority** injected through the UMH-standard 1Password protocol.
> Every harness, human, agent, substrate command, and projection command uses the same secret runtime contract.

One protocol governs UMH and every projection. UMH is **not** special — it follows the
same contract as EntrepreneurOS, CreatorOS, and LyfeOS.

## The invariant (standardize this, not the filename)

```
1Password vault
  -> committed op:// Secret Reference Manifest
    -> op run runtime injection
      -> plaintext .env stays ignored / local-only / non-canonical
```

The **filename** of the manifest is a repo-local adapter value. The **contract** may not vary.

## SecretReferenceManifest — the canonical abstraction

A `SecretReferenceManifest` is:

- a **committed** file,
- containing **only** `op://` references or safe non-secret literals,
- containing **zero** plaintext secret values,
- whose path each repo **declares**,
- read by the shared `op run` wrapper,
- the sole committed env-reference file for the repo.

Runtime injection happens **only** through `op run`. Plaintext `.env` is ignored,
local-only, and non-canonical — never required for normal development runtime.

## Per-repo manifest declaration

| System | Role | Vault | Manifest path | op:// refs |
|---|---|---|---|---|
| **UMH** (`/opt/OS`) | substrate | `<substrate-vault>` | `services/.env.tpl` | 27 |
| **EntrepreneurOS** | projection | `EntrepreneurOS` | `.env.op.tpl` | 11 |
| **CreatorOS** | projection | `CreatorOS` | `.env.op.tpl` | 3 |
| **LyfeOS** | projection | `LyfeOS` | `.env.op.tpl` | 6 |

**Filename may vary by repo. The contract may not.**

- UMH's `services/.env.tpl` is **grandfathered** as the substrate's canonical
  `SecretReferenceManifest`. It is loaded by `scripts/rotate_secrets.sh` and other
  `op run` callers. It is **not** renamed in this packet — forcing a rename would create
  avoidable loader blast radius. A later loader-decoupling packet may migrate UMH to
  `.env.op.tpl` only after proving `rotate_secrets.sh` and all UMH boot paths are unaffected.
- Projection repos use `.env.op.tpl` by convention.
- **Future repos** should prefer `.env.op.tpl` unless they already carry an existing loader convention.

## Vault / item / field convention

- **Vault per system:** `<substrate-vault>` (substrate), `EntrepreneurOS` / `CreatorOS` / `LyfeOS` (projections).
- **Item per runtime environment:** `Development` (later: `Staging`, `Production`).
- **Field names equal environment-variable keys exactly.**
- **Reference form:** `op://<Vault>/<EnvironmentItem>/<ENV_KEY>`.

## Runtime loading

Standard command shape:

```bash
op run --env-file=<manifest_path> -- <repo command>
```

Use the canonical wrapper for humans, agents, and harnesses:

```bash
scripts/op_run.sh -- npm run dev                       # auto-discovers the manifest
scripts/op_run.sh --manifest services/.env.tpl -- bash scripts/rotate_secrets.sh
scripts/op_run.sh --repo /path/to/projection -- npm run build
```

### `scripts/op_run.sh` contract

The wrapper is **fail-closed**. Before it runs the command it verifies:

1. the declared/discovered manifest **exists**,
2. the manifest contains **at least one `op://` reference**,
3. the manifest contains **no value-shaped plaintext secrets**,
4. **no real plaintext `.env` is staged** in git.

It then runs `op run --env-file=<manifest> -- <command>` and **never prints resolved values**.
Any repo may expose its own wrapper, but that wrapper must only call the same primitive.

## Plaintext `.env` rule

- `.env` is local-only, non-canonical, ignored, and temporary.
- `.env` must **never** be tracked.
- `.env` must **never** be required once `op run` boot is verified.
- Plaintext `.env` archival/removal occurs **only after**:
  1. all `op://` refs resolve,
  2. the app boots/checks through `op run`,
  3. `.gitignore` protects `.env` and `.env.*`,
  4. the secret scan is green.

## `.gitignore` standard

Every repo must **ignore**:

```
.env
.env.*
```

Every repo must **allow** safe templates:

```
!.env.op.tpl
!.env.example
!.env.tpl
```

`.env.example` / `.env.tpl` are allowed **only if sanitized and value-free**.

## Branch handling

Safe protocol files are committed on **each repo's actual current operating branch** —
never a side branch that leaves the working branch exposed.

- EntrepreneurOS: `feature/company-system`
- CreatorOS: `main`
- LyfeOS: `main`

Temporary branches may carry patches. **Operating branches carry protection.**
The secrets protocol is not real until it protects the branch the repo actually runs from.

## Current status (2026-07-05)

All four systems satisfy the contract. See
`data/umh/projection_reconciliation/secrets_runtime_status.json` for the machine-readable
record (`vault_exists`, `env_op_template_present`, `refs_resolve`,
`gitignore_protects_plaintext_env`, `op_run_verified`, `plaintext_env_retired_or_pending`
per system).

- **UMH** — `services/.env.tpl` (27 refs), `.env` ignored, op run in use; no plaintext `.env` in tree.
- **EntrepreneurOS** — `.env.op.tpl` (11 refs) committed on `feature/company-system` @ `9c8725f`; `ALL_11_KEYS_INJECTED`; `.env` untracked + ignored.
- **CreatorOS** — `.env.op.tpl` (3 refs) committed on `main` @ `139e2c9`; `ALL_3_KEYS_INJECTED`; `.env` untracked + ignored.
- **LyfeOS** — `.env.op.tpl` (6 refs) committed on `main` @ `6ce1ae3e`; `ALL_6_KEYS_INJECTED`; `.env` untracked + ignored (gap closed).

The temporary `chore/secrets-1password-runtime` side branches were deleted (local + remote)
on all three projection repos after protection landed on each operating branch.

**Pending (separate, operator-approved):** archive/remove the plaintext `.env` files on the
Beast after an app-boot burn-in via `op run`. Migration is proven; retirement is deferred by policy.

## Related governance

- `docs/PROJECTION_SECRETS_MIGRATION_2026-07-05.md` — the migration that vaulted the secrets (#176).
- `docs/PROJECTION_SOURCE_TRUTH.md` — Beast is projection source of truth (#173).
- `scripts/op_run.sh` — the canonical runtime wrapper.
- `tests/test_secrets_runtime_protocol.py` — the contract guards.
