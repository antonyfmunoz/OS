#!/usr/bin/env bash
# op_run.sh — canonical UMH 1Password Secret Runtime wrapper.
#
# One secret-loading contract for UMH substrate AND every projection repo.
# Secrets live in 1Password; a committed Secret Reference Manifest holds only
# op:// references; this wrapper injects values into the child process at
# runtime via `op run`. Plaintext .env is never required, never printed.
#
# THE CONTRACT (WP-P4-SECRETS-RUNTIME-001):
#   1Password vault  ->  committed op:// reference manifest  ->  op run injection
#   ->  plaintext .env stays ignored / local-only / non-canonical.
# The manifest FILENAME may vary per repo; the contract may not.
#   - UMH (/opt/OS): services/.env.tpl          vault $UMH_OP_VAULT  (grandfathered)
#   - projections:   .env.op.tpl                vault <AppName>
#
# Usage:
#   scripts/op_run.sh [--manifest <path>] [--repo <dir>] -- <command> [args...]
#   scripts/op_run.sh -- npm run dev            # auto-discovers the manifest
#   scripts/op_run.sh --manifest services/.env.tpl -- bash scripts/rotate_secrets.sh
#
# Guarantees before it runs the command (fail-closed):
#   - the manifest exists,
#   - the manifest contains at least one op:// reference,
#   - the manifest contains no value-shaped plaintext secrets,
#   - no real plaintext .env file is staged in git.
# It NEVER echoes resolved secret values.
set -euo pipefail

REPO_DIR="."
MANIFEST=""
CMD=()

# --- arg parsing: everything after `--` is the command, verbatim ---
while [[ $# -gt 0 ]]; do
  case "$1" in
    --manifest) MANIFEST="$2"; shift 2 ;;
    --repo)     REPO_DIR="$2"; shift 2 ;;
    --)         shift; CMD=("$@"); break ;;
    *) echo "op_run: unknown argument '$1' (did you forget '--' before the command?)" >&2; exit 2 ;;
  esac
done

cd "$REPO_DIR"

if [[ ${#CMD[@]} -eq 0 ]]; then
  echo "op_run: no command given. Usage: scripts/op_run.sh [--manifest <path>] -- <command>" >&2
  exit 2
fi

# --- discover the manifest if not passed: UMH convention first, then projection ---
if [[ -z "$MANIFEST" ]]; then
  for candidate in services/.env.tpl .env.op.tpl; do
    if [[ -f "$candidate" ]]; then MANIFEST="$candidate"; break; fi
  done
fi

# --- contract gate 1: manifest must exist ---
if [[ -z "$MANIFEST" || ! -f "$MANIFEST" ]]; then
  echo "op_run: no Secret Reference Manifest found (looked for services/.env.tpl, .env.op.tpl)." >&2
  echo "        Declare one with --manifest <path>. The manifest holds only op:// references." >&2
  exit 3
fi

# --- contract gate 2: manifest must contain at least one op:// reference ---
if ! grep -qE 'op://' "$MANIFEST"; then
  echo "op_run: manifest '$MANIFEST' contains no op:// references — not a valid Secret Reference Manifest." >&2
  exit 3
fi

# --- contract gate 3: manifest must not contain value-shaped plaintext secrets ---
# A manifest line is safe if its value is an op:// ref, empty, or a non-secret literal.
# Flag lines whose RHS looks like a real credential (provider key / DB URL with password).
LEAKS="$(grep -nEv '^[[:space:]]*#' "$MANIFEST" \
  | grep -E '=' \
  | grep -vE '=[[:space:]]*("?op://|$|""|'"''"')' \
  | grep -Ei 'sk_live_[0-9a-zA-Z]{16,}|sk_test_[0-9a-zA-Z]{16,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{35}|(postgres|postgresql|mongodb(\+srv)?|mysql|redis)://[^:@/]+:[^@]{6,}@|-----BEGIN [A-Z ]*PRIVATE KEY-----' \
  || true)"
if [[ -n "$LEAKS" ]]; then
  echo "op_run: manifest '$MANIFEST' appears to contain plaintext secret VALUES, not op:// references." >&2
  echo "        A Secret Reference Manifest is committable only if it holds references, never values." >&2
  echo "        Offending line numbers: $(echo "$LEAKS" | cut -d: -f1 | paste -sd, -)" >&2
  exit 4
fi

# --- contract gate 4: refuse if a real plaintext .env is staged in git ---
if git rev-parse --git-dir >/dev/null 2>&1; then
  STAGED_ENV="$(git diff --cached --name-only 2>/dev/null \
    | grep -E '(^|/)\.env($|\.)' \
    | grep -vE '\.(op\.tpl|tpl|example|sample)$' || true)"
  if [[ -n "$STAGED_ENV" ]]; then
    echo "op_run: refusing to run — plaintext env file(s) staged for commit:" >&2
    echo "$STAGED_ENV" | sed 's/^/          /' >&2
    echo "        Secrets belong in 1Password, not in git. Unstage them first." >&2
    exit 5
  fi
fi

# --- all gates passed: inject via 1Password and exec the command (values never printed) ---
exec op run --env-file="$MANIFEST" -- "${CMD[@]}"
