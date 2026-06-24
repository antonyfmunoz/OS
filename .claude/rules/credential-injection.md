# Credential Injection Law (NON-NEGOTIABLE — ENFORCED BY PRE-COMMIT)

Computer use credentials (passwords, auth tokens, API keys) are NEVER passed
as plaintext CLI arguments, hardcoded strings, or unprotected env vars.

All credentials for browser automation and computer use flow through 1Password:
- `op run --env-file=<tpl>` wraps the collector command on the executor side
- `op` resolves `op://` URIs to real values and injects as env vars
- Template files (*.tpl) use `op://vault/item/field` URIs — never raw secrets
- Fallback to cached auth when `op` CLI unavailable (logged as warning)

Pattern (executor-side injection — env vars don't transit SSH):
  ssh <executor> "op run --env-file=<tpl> -- python collector.py ..."

Never:
- Pass credentials as CLI arguments (visible in ps, logs, shell history)
- Hardcode credentials in substrate/ or scripts/
- Rely on pre-cached auth state as the only credential path
- Skip 1Password when op CLI is available

Substrate enforcement: `validate_credential_source()` in
`substrate/execution/credential_gate.py` — call before any computer use
that requires authentication.

Pre-commit hook: `scripts/check_credential_injection.py` blocks commits
introducing plaintext password patterns in subprocess/SSH calls.
