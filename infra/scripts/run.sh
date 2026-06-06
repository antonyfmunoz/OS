#!/usr/bin/env bash
# run.sh — Run any command with UMH secrets from 1Password
#
# Usage: bash infra/scripts/run.sh <command> [args...]
# Examples:
#   bash infra/scripts/run.sh python3 scripts/eod_sync.py
#   bash infra/scripts/run.sh python3 -c "import os; print(os.getenv('DATABASE_URL'))"
set -euo pipefail

UMH_ROOT="${UMH_ROOT:-/opt/OS}"

exec op run \
    --env-file="$UMH_ROOT/services/.env.tpl" \
    --env-file="$UMH_ROOT/config/nonsecret.env" \
    -- "$@"
