#!/usr/bin/env bash
# install_sync_automation.sh — install sync ritual automation (hook + cron)
#
# Usage:
#   scripts/install_sync_automation.sh           # install both
#   scripts/install_sync_automation.sh --check   # verify without changes
#
# Idempotent: safe to run repeatedly. Checks before inserting.
# Symlinks the hook so updates to scripts/hooks/post-merge take effect
# immediately without re-running the installer.

set -euo pipefail

UMH_ROOT="${UMH_ROOT:-/opt/OS}"
CANONICAL_ROOT="/opt/OS"
HOOK_SRC="${UMH_ROOT}/scripts/hooks/post-merge"
HOOK_LINK_TARGET="${CANONICAL_ROOT}/scripts/hooks/post-merge"
GIT_DIR=$(cd "$UMH_ROOT" && git rev-parse --git-common-dir 2>/dev/null || echo "${UMH_ROOT}/.git")
HOOK_DST="${GIT_DIR}/hooks/post-merge"
CRON_SRC="${UMH_ROOT}/scripts/cron/sync_all.cron"
CHECK_ONLY=false

if [[ "${1:-}" == "--check" ]]; then
    CHECK_ONLY=true
fi

ISSUES=0

# --- Hook --------------------------------------------------------------------

echo "Hook: post-merge"

if [[ ! -f "$HOOK_SRC" ]]; then
    echo "  ERROR: canonical hook not found at $HOOK_SRC"
    ISSUES=$((ISSUES + 1))
elif [[ -L "$HOOK_DST" ]]; then
    TARGET=$(readlink "$HOOK_DST")
    if [[ "$TARGET" == "$HOOK_LINK_TARGET" ]]; then
        echo "  OK — symlink points to canonical version"
    else
        echo "  WARN — symlink points to $TARGET, expected $HOOK_LINK_TARGET"
        if ! $CHECK_ONLY; then
            ln -sf "$HOOK_LINK_TARGET" "$HOOK_DST"
            echo "  FIXED — symlink updated"
        fi
        ISSUES=$((ISSUES + 1))
    fi
elif [[ -f "$HOOK_DST" ]]; then
    echo "  WARN — regular file exists (not a symlink to canonical)"
    if ! $CHECK_ONLY; then
        rm "$HOOK_DST"
        ln -s "$HOOK_LINK_TARGET" "$HOOK_DST"
        chmod +x "$HOOK_SRC"
        echo "  FIXED — replaced with symlink to canonical version"
    else
        ISSUES=$((ISSUES + 1))
    fi
else
    if ! $CHECK_ONLY; then
        ln -s "$HOOK_LINK_TARGET" "$HOOK_DST"
        chmod +x "$HOOK_SRC"
        echo "  INSTALLED — symlinked to canonical version"
    else
        echo "  MISSING — not installed"
        ISSUES=$((ISSUES + 1))
    fi
fi

# --- Cron --------------------------------------------------------------------

echo "Cron: sync_all"

CRON_LINE=$(grep -v '^#' "$CRON_SRC" | grep -v '^$' | head -1)

if crontab -l 2>/dev/null | grep -qF 'sync_all.sh --pull'; then
    EXISTING=$(crontab -l 2>/dev/null | grep -F 'sync_all.sh --pull')
    if [[ "$EXISTING" == "$CRON_LINE" ]]; then
        echo "  OK — cron entry matches canonical"
    else
        echo "  WARN — cron entry differs from canonical"
        echo "    have: $EXISTING"
        echo "    want: $CRON_LINE"
        if ! $CHECK_ONLY; then
            (crontab -l 2>/dev/null | grep -vF 'sync_all.sh --pull'; \
             grep -v '^$' "$CRON_SRC") | crontab -
            echo "  FIXED — replaced with canonical entry"
        else
            ISSUES=$((ISSUES + 1))
        fi
    fi
else
    if ! $CHECK_ONLY; then
        (crontab -l 2>/dev/null; cat "$CRON_SRC") | crontab -
        echo "  INSTALLED — cron entry added"
    else
        echo "  MISSING — not installed"
        ISSUES=$((ISSUES + 1))
    fi
fi

# --- Summary -----------------------------------------------------------------

echo ""
if [[ $ISSUES -gt 0 ]]; then
    if $CHECK_ONLY; then
        echo "CHECK: $ISSUES issue(s) found. Run without --check to fix."
        exit 1
    else
        echo "FIXED: $ISSUES issue(s) resolved."
    fi
else
    echo "OK: sync automation fully installed."
fi
