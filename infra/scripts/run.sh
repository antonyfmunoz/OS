#!/usr/bin/env bash
# run.sh — Run any command with UMH secrets from 1Password
#
# Usage: bash infra/scripts/run.sh <command> [args...]
# Examples:
#   bash infra/scripts/run.sh python3 scripts/eod_sync.py
#   bash infra/scripts/run.sh python3 -c "import os; print(os.getenv('DATABASE_URL'))"
set -euo pipefail

UMH_ROOT="${UMH_ROOT:-/opt/OS}"

# nonsecret.env holds this tenant's non-secret config and is gitignored
# (code is separated from instance data). A fresh clone ships only the
# .example — the operator copies it to nonsecret.env and fills it in.
NONSECRET="$UMH_ROOT/config/nonsecret.env"
if [[ ! -f "$NONSECRET" ]]; then
    echo "run.sh: $NONSECRET not found." >&2
    echo "  Copy config/nonsecret.env.example to config/nonsecret.env and fill in this tenant's values." >&2
    exit 1
fi

exec op run \
    --env-file="$UMH_ROOT/services/.env.tpl" \
    --env-file="$NONSECRET" \
    -- "$@"
