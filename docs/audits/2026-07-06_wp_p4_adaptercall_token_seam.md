# AdapterCall Provider-Token Seam — Injection Contract (Fail-Closed)

**Work packets:** WP-P4-ADAPTERCALL-TOKEN-SEAM-001 (contract, §1–6) ·
WP-P4-PROVIDER-TOKEN-VAULTING-001 (gws vaulting + cutover plan, §7–9)
**Date:** 2026-07-06
**Type:** boundary packet — contract + minimal fail-closed code. No send_email
execution, no OAuth flows implemented, no provider SDK imports in projections/.
**Code:** `substrate/execution/credential_gate.py` (provider-token seam section)
**Tests:** `tests/test_adaptercall_token_seam.py` (17 tests + 4 template-conformance tests)

---

## 1. Where AdapterCall / adapter execution happens today (recon)

"AdapterCall" is a UMH seam primitive (one of the eight in
`projections/eos/integration/action_seam.py::UMH_SEAM_PRIMITIVES`), not a
single class. The concrete surfaces:

| Surface | File | Role |
|---|---|---|
| Adapter protocol | `adapters/protocol.py` | `Adapter.execute(AdapterRequest) -> AdapterResponse` — the canonical adapter contract |
| Adapter types | `substrate/types.py` | `AdapterRequest` (~L789), `AdapterResponse` (~L492), `AdapterType/AdapterStatus/AdapterConfig` (~L1226+) |
| Capability routing | `substrate/execution/runtime/capability_router.py` | intent → ranked provider chain; `CapabilityInvocation` in `substrate/types.py` |
| Credential choke point | `substrate/execution/credential_gate.py` | `validate_credential_source()` / `build_op_wrapped_command()` — 1Password `op run` wrapping |
| GWS adapters | `adapters/google_workspace/` | `gws_connector.py` (gws CLI via keyring), `email_gps.py`, `tasks_adapter.py`, `doc_creator.py` |
| GitHub adapter | `adapters/github/github_operations.py` | gh CLI writes wrapped as `ActionEnvelope` for the governed spine |
| EOS executor seam | `projections/eos/integration/action_execution.py` | executes ONLY the non-provider allowlist (`create_task`, `create_document`); provider-coupled types (e.g. `send_email`) are refused at the accessor AND inside the atomic claim SQL (`tables.py::EXECUTABLE_ACTION_TYPES`) |
| Seam map | `docs/EOS_ACTION_EXECUTOR_SEAM.md` + `data/umh/projection_reconciliation/eos_action_executor_seam_map.json` | seam `external-side-effect-call` → primitive **AdapterCall** → target: adapters/ + credential_gate.py |

Key pre-existing gap: `build_op_wrapped_command()` is **fail-open** — when
`op` or the template is missing it returns the ORIGINAL unwrapped command
(sanctioned for browser evidence collection, which falls back to cached
auth). That behavior is unacceptable for provider-backed governed actions:
a send_email must never "degrade" into running without injected credentials
or into reading a stored plaintext token.

## 2. Provider-token requirement map

What token material each provider-backed governed action will need. Names
only — values live in 1Password per the Credential Injection Law.

| Provider id | Env var names (injected by `op run`) | Template | Governed actions unlocked | Today's (banned) state |
|---|---|---|---|---|
| `google_workspace` | `GWS_OAUTH_CLIENT_ID`, `GWS_OAUTH_CLIENT_SECRET`, `GWS_OAUTH_REFRESH_TOKEN` | `scripts/.env.gws.tpl` | future `send_email`, calendar/drive writes | OAuth grant scripts persist plaintext JSON at `~/.config/gws/gmail_credentials.json` (`scripts/oauth_grant_gmail.py`, `services/oauth_device_flow.py`); gws CLI uses OS keyring; Beast EOS app stores plaintext rows in its `oauth_tokens` table (flagged SECURITY gap in `docs/EOS_ACTION_EXECUTOR_SEAM.md` §4). **Update:** material vaulted + template provisioned on the VPS — see §7; plaintext file remains until the §8 cutover |
| `github` | `GITHUB_TOKEN` | `scripts/.env.github.tpl` | PR create/merge, branch ops (`adapters/github/github_operations.py`) | gh CLI ambient auth |
| `notion` | `NOTION_API_KEY` | `scripts/.env.notion.tpl` | Notion writes (`adapters/notion/`) | env var from service .env |
| `discord` | `DISCORD_BOT_TOKEN` | `scripts/.env.discord.tpl` | bot posts outside the resident `os-discord` service | service .env |

Registry lives in code:
`substrate/execution/credential_gate.py::PROVIDER_TOKEN_REQUIREMENTS`.
Adding a provider = adding one `ProviderTokenRequirement` row + provisioning
its `.tpl` (op:// references only) on the executing node. An UNREGISTERED
provider is refused (`unknown_provider`) — the registry is itself a gate.

The `access token` for Google is deliberately NOT in the requirement set:
access tokens are short-lived derivatives minted at call time from the
refresh token inside the adapter process; persisting them anywhere is the
plaintext pattern this seam bans.

## 3. The injection contract

1. **Token values live only in 1Password.** Per-provider op env templates
   (`scripts/.env.<provider>.tpl`) map env var NAMES to `op://vault/item/field`
   references. Real values exist only inside the `op run`-wrapped adapter
   subprocess environment, resolved on the executing node.
2. **Resolution happens at the adapter boundary, in substrate.** The adapter
   (or the executor about to spawn an adapter subprocess) calls
   `resolve_provider_token_injection(provider)` /
   `require_provider_token_injection(provider)` and, when allowed, prepends
   `decision.op_command_prefix` — `("op", "run", "--env-file=<tpl>", "--")` —
   to the adapter command. Combined with the CPU Gate Law this composes as
   `gated_subprocess_run(list(decision.op_command_prefix) + inner_cmd, ...)`.
3. **EOS projection code never touches token logic.** `projections/eos/`
   imports no provider SDKs, reads no token material, and passes only a
   provider id string across the seam. Enforced today by the executor's
   non-provider allowlist; when `send_email` is unblocked, the executor adds
   the action type to a provider-mapped allowlist and the ADAPTER performs
   injection — the projection still never sees a token.
4. **Never in the EOS DB, never in responses.** Provider tokens are never
   written to any projection database (the Beast `oauth_tokens` plaintext
   table is a banned pattern — migration is owner-approval item #2 in
   `docs/EOS_ACTION_EXECUTOR_SEAM.md` §5) and never appear in any accessor
   envelope, API response, log line, or error message. The decision/refusal
   types carry names and paths only, by construction.
5. **No plaintext env fallback.** Absence of `op`, of the template, or of a
   required var name in the template is a REFUSAL — never a fallthrough to
   `os.environ`, a credentials file, or a DB row.

## 4. Fail-closed behavior (implemented)

`resolve_provider_token_injection(provider)` returns a frozen
`AdapterCallCredentialDecision`; it never raises and never degrades:

| Condition | `allowed` | `refusal_code` |
|---|---|---|
| provider not in `PROVIDER_TOKEN_REQUIREMENTS` | False | `unknown_provider` |
| `op` CLI not on PATH | False | `op_cli_unavailable` |
| `scripts/.env.<provider>.tpl` absent | False | `env_template_missing` |
| template lacks a required env var NAME | False | `env_template_incomplete` (missing names listed) |
| all preconditions met | True | — (`op_command_prefix` populated) |

`require_provider_token_injection(provider)` raises the typed
`ProviderTokenUnavailableError` (carries the decision; message = provider +
code + reason, non-secret) for callers preferring exception flow.

Non-secret by construction: the resolver reads only the LEFT side of
`NAME=` lines in the template — op:// references and values are never
parsed, stored, returned, or logged (regression-tested, including a
poisoned-template test).

The legacy fail-open `build_op_wrapped_command()` is retained ONLY for the
browser evidence collection path (cached-auth fallback is its documented
behavior) and is now explicitly marked as such in its docstring. All
provider-backed governed actions MUST use the fail-closed seam.

## 5. Verification

```
python3 -m pytest tests/test_adaptercall_token_seam.py -q          # 17 passed
python3 -m py_compile substrate/execution/credential_gate.py
python3 scripts/check_type_divergence.py --registry-audit           # types registered
python3 scripts/check_credential_injection.py --all                 # no plaintext patterns
```

New canonical types registered per the Type Coherence Law
(`substrate/canonical_types.py`): `CredentialGateResult` (pre-existing,
previously unregistered), `ProviderTokenRequirement`,
`AdapterCallCredentialDecision`, `ProviderTokenUnavailableError`.

## 6. Deferred debt (explicitly NOT in this packet)

- **No OAuth flows.** Obtaining/refreshing the GWS refresh token into
  1Password (replacing `~/.config/gws/gmail_credentials.json` and the
  Beast `oauth_tokens` table) is the credential-migration packet — owner
  approval required (`docs/EOS_ACTION_EXECUTOR_SEAM.md` §5 item 2).
- **No send_email execution.** `EXECUTABLE_ACTION_TYPES` stays
  `{create_task, create_document}`; unblocking a provider action type is a
  separate packet that consumes this seam.
- **Template provisioning.** The four `scripts/.env.<provider>.tpl` files
  are provisioned per node when each provider is activated (op:// references
  only). Their absence today is correct: the seam refuses.
- **Existing adapters not yet migrated.** `gws_connector.py` (keyring),
  `github_operations.py` (ambient gh auth), Notion/Discord (.env) keep
  their current read-path auth; they migrate to this seam when their WRITE
  actions become governed AdapterCalls.

---

## 7. google_workspace vaulted (WP-P4-PROVIDER-TOKEN-VAULTING-001)

The `google_workspace` provider is now INJECTABLE on the VPS node:
`resolve_provider_token_injection('google_workspace')` returns
`allowed=True` with the `op run --env-file=scripts/.env.gws.tpl --` prefix.

### 7.1 What was vaulted

- **Source (plaintext, still in place — see cutover plan §8):**
  `~/.config/gws/gmail_credentials.json` on the VPS. Keys observed
  (structure only): `access_token, client_id, client_secret, expiry,
  issued_at, refresh_token, scopes, token_uri`. The sibling
  `gmail_credentials_empyreanstudios.co.json` is a byte-identical copy
  (same sha256) — one OAuth grant, two filenames (see
  `services/oauth_device_flow.py::_save_credentials`, which writes both).
- **Vault item:** `Google-Workspace-OAuth` (API_CREDENTIAL) in the
  `UMH-Production` vault — same vault + hyphenated-title convention as
  `Discord-Bot`, `Notion-Integration`, `AI-Anthropic`. Concealed fields:
  `client_id`, `client_secret`, `refresh_token`. Non-secret context field:
  `token_uri`. The short-lived `access_token` was deliberately NOT vaulted
  (contract §2 — access tokens are minted at call time from the refresh
  token; persisting them is the banned pattern).
- **Transfer mechanism:** `scripts/vault_gws_credentials.py` — reads the
  JSON in-process and pipes a full item template to `op item create` via
  STDIN. Values never touched argv, logs, stdout, or shell history; the
  script prints field NAMES and value LENGTHS only. Re-runnable for
  rotation via `--rotate`.
- **Template provisioned:** `scripts/.env.gws.tpl` (committed — op://
  references only), declaring exactly `GWS_OAUTH_CLIENT_ID`,
  `GWS_OAUTH_CLIENT_SECRET`, `GWS_OAUTH_REFRESH_TOKEN`. Conformance is
  regression-tested (`TestProvisionedGwsTemplate`).

### 7.2 Verification performed (lengths/booleans only — no values)

```
python3 scripts/vault_gws_credentials.py
  field client_id: len=73 / client_secret: len=35 / refresh_token: len=103
  created item: title=Google-Workspace-OAuth vault=UMH-Production

op read op://UMH-Production/Google-Workspace-OAuth/<field> | wc -c
  -> 73 / 35 / 103 (matches source file lengths)

op run --env-file=scripts/.env.gws.tpl -- python3 <sha256 compare>
  -> all three injected env values hash-identical to the file values

resolve_provider_token_injection('google_workspace')
  -> allowed=True, op_command_prefix=('op','run','--env-file=.../scripts/.env.gws.tpl','--')

services/magic_link_handler._get_gmail_service() + users().getProfile()
  -> read-only success (existing gws adapter path unchanged and working)
```

### 7.3 Beast `oauth_tokens` table (documented only — NO mutation this packet)

- **Schema:** `data/repos/entrepreneuros/shared/schema.ts` (~L425)
  `oauth_tokens(id, user_id -> users.id, provider, access_token NOT NULL,
  refresh_token, token_type, expires_at, scope, created_at, updated_at)` —
  plaintext `text` columns for both tokens.
- **Where it lives:** the EOS app database (Neon) used by the Beast-hosted
  EntrepreneurOS app (source truth for the app is on the Beast; `data/repos/
  entrepreneuros/` on the VPS is a schema mirror).
- **Where consumed:** the EOS app's own Google OAuth connect flow
  (server-side token store keyed by `user_id`+`provider`). UMH substrate/
  adapters do NOT read this table — the VPS gws paths read
  `~/.config/gws/gmail_credentials.json` (magic-link handler) or the gws
  CLI keyring (`gws_connector.py`).
- **Status:** banned pattern per §3.4; flagged as SECURITY gap in
  `docs/EOS_ACTION_EXECUTOR_SEAM.md` §4 and owner-approval item #2 in §5.
  Migration (vault rows → 1Password, drop plaintext columns) is a separate
  owner-approved packet. Nothing in this packet touched that DB.

## 8. Cutover plan — retiring the plaintext file (operator follow-up)

The plaintext file was NOT deleted in this packet: `services/
magic_link_handler.py` still reads it at call time. Cutover order:

1. **Migrate the reader.** Change `magic_link_handler._get_gmail_service()`
   to build `google.oauth2.credentials.Credentials` from
   `GWS_OAUTH_CLIENT_ID/SECRET/REFRESH_TOKEN` env vars, and run the
   `os-webhook` service under `op run --env-file=scripts/.env.gws.tpl`
   (or resolve via `require_provider_token_injection('google_workspace')`
   at service start). Same for any future gws adapter subprocess:
   `gated_subprocess_run(list(decision.op_command_prefix) + inner_cmd, ...)`.
2. **Verify via injection.** With the file still present, run the reader
   under injection and confirm a read-only `users().getProfile()` succeeds
   with the file path temporarily renamed (proves no fallthrough read).
3. **Delete the plaintext material** (operator action, after step 2 passes):
   `rm ~/.config/gws/gmail_credentials.json ~/.config/gws/gmail_credentials_empyreanstudios.co.json`
   — and review `~/.config/gws/client_secret.json` + `token_cache.json`
   (grant-flow inputs/caches) for the same treatment.
4. **Re-point the grant flow.** Update `scripts/oauth_grant_gmail.py` /
   `services/oauth_device_flow.py::_save_credentials` to write into
   1Password (`python3 scripts/vault_gws_credentials.py --rotate` from a
   temp file, or direct stdin pipe) instead of persisting plaintext JSON.
5. **Guard against reappearance.** Add the two credential filenames to a
   check (e.g. `scripts/check_credential_injection.py` or a cron audit) so
   a re-grant that recreates plaintext is flagged.

## 9. Rotation runbook

When the refresh token is revoked/expired or the OAuth client is rotated:

1. Re-run the grant: `python3 scripts/oauth_grant_gmail.py` (writes the
   credentials file — until cutover step 4 lands, this is still the
   grant flow's output).
2. `python3 scripts/vault_gws_credentials.py --rotate` — deletes and
   recreates the `Google-Workspace-OAuth` item from the fresh file
   (values via stdin only; prints lengths only).
3. Verify: `op read op://UMH-Production/Google-Workspace-OAuth/refresh_token | wc -c`
   (length only) and re-run the §7.2 injection smoke test.
4. Post-cutover: delete the plaintext file again (cutover step 3).

Rollback of this packet: `op item delete 'Google-Workspace-OAuth' --vault
UMH-Production` + revert the commit (removes `scripts/.env.gws.tpl` and
`scripts/vault_gws_credentials.py`). The adapter keeps working throughout —
it still reads the untouched plaintext file until cutover step 1.
