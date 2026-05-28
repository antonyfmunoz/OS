#!/usr/bin/env bash
# Install UMH pre-commit hooks into the repository.
# Run once after clone: bash scripts/install_hooks.sh

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOK_DIR="$(git rev-parse --git-common-dir)/hooks"

cat > "$HOOK_DIR/pre-commit" << 'HOOK'
#!/usr/bin/env bash
# UMH Pre-Commit Gate — runs all coherence checks before allowing a commit.
# Gates:
#   1. Type Coherence  — blocks shadow types that diverge from canonical_types.py
#   2. Instance Context — blocks hardcoded instance values in substrate/ code
#
# All gates run so the developer sees ALL violations at once.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
FAILED=0

# ── Gate 1: Type Coherence ──────────────────────────────────────────────────
if [ -f "$REPO_ROOT/scripts/check_type_divergence.py" ]; then
    if ! python3 "$REPO_ROOT/scripts/check_type_divergence.py"; then
        FAILED=1
    fi
fi

# ── Gate 2: Instance Context ────────────────────────────────────────────────
if [ -f "$REPO_ROOT/scripts/check_instance_leak.py" ]; then
    if ! python3 "$REPO_ROOT/scripts/check_instance_leak.py"; then
        FAILED=1
    fi
fi

exit $FAILED
HOOK

chmod +x "$HOOK_DIR/pre-commit"
echo "Pre-commit hook installed at $HOOK_DIR/pre-commit"
echo "Gates: type_coherence, instance_context"
