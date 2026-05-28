#!/usr/bin/env bash
# Install the type divergence pre-commit hook.
# Safe to run repeatedly — merges with existing pre-commit if present.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOK_DIR="$REPO_ROOT/.git/hooks"
HOOK_FILE="$HOOK_DIR/pre-commit"
CANONICAL="$REPO_ROOT/scripts/hooks/pre-commit"

if [ ! -f "$HOOK_FILE" ]; then
    cp "$CANONICAL" "$HOOK_FILE"
    chmod +x "$HOOK_FILE"
    echo "✓ Installed pre-commit hook (divergence gate)"
elif grep -q "check_type_divergence" "$HOOK_FILE"; then
    echo "✓ Divergence gate already installed in pre-commit hook"
else
    echo "" >> "$HOOK_FILE"
    echo "# ── Type divergence gate ──" >> "$HOOK_FILE"
    echo "python3 \"\$(git rev-parse --show-toplevel)/scripts/check_type_divergence.py\"" >> "$HOOK_FILE"
    echo "✓ Appended divergence gate to existing pre-commit hook"
fi

# Verify
python3 "$REPO_ROOT/scripts/check_type_divergence.py" --all --verbose
