#!/usr/bin/env bash
# setup_isolation.sh — creates per-session CLAUDE_CONFIG_DIR directories
# Each directory symlinks everything from ~/.claude EXCEPT .credentials.json
# which gets its own independent copy managed by the coordinator
#
# Run once, or re-run after adding new items to ~/.claude

set -euo pipefail

MASTER_DIR="/root/.claude"
SESSIONS_BASE="/root/.claude_sessions"
SESSION_NAMES=("builder" "product" "adhoc")

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

for session in "${SESSION_NAMES[@]}"; do
    SESSION_DIR="$SESSIONS_BASE/$session"
    log "Setting up: $SESSION_DIR"

    mkdir -p "$SESSION_DIR"

    # Symlink everything from master EXCEPT credentials and backups
    for item in "$MASTER_DIR"/*; do
        basename_item=$(basename "$item")

        # Skip credentials — each session gets its own copy
        [[ "$basename_item" == ".credentials.json" ]] && continue
        [[ "$basename_item" == ".credentials_backups" ]] && continue

        target="$SESSION_DIR/$basename_item"

        # Remove existing (stale symlink or old file)
        if [[ -L "$target" ]] || [[ -e "$target" ]]; then
            rm -f "$target"
        fi

        ln -s "$item" "$target"
    done

    # Also symlink hidden files (like .credentials_backups is handled, but others)
    for item in "$MASTER_DIR"/.*; do
        basename_item=$(basename "$item")
        [[ "$basename_item" == "." ]] || [[ "$basename_item" == ".." ]] && continue
        [[ "$basename_item" == ".credentials.json" ]] && continue
        [[ "$basename_item" == ".credentials_backups" ]] && continue

        target="$SESSION_DIR/$basename_item"
        if [[ -L "$target" ]] || [[ -e "$target" ]]; then
            rm -f "$target"
        fi
        ln -s "$item" "$target"
    done

    # Copy credentials (not symlink — this is the isolation point)
    if [[ -f "$MASTER_DIR/.credentials.json" ]]; then
        cp "$MASTER_DIR/.credentials.json" "$SESSION_DIR/.credentials.json"
        chmod 600 "$SESSION_DIR/.credentials.json"
        log "  Copied credentials to $SESSION_DIR/.credentials.json"
    fi

    log "  Done: $(ls -la "$SESSION_DIR/" | wc -l) items"
done

log "=== Isolation setup complete ==="
log "Session directories:"
for session in "${SESSION_NAMES[@]}"; do
    echo "  $SESSIONS_BASE/$session"
done
echo ""
echo "To use: export CLAUDE_CONFIG_DIR=$SESSIONS_BASE/<session_name>"
echo "Then start claude in that tmux session."
