#!/usr/bin/env bash
# start_session.sh — starts a CC session with isolated credentials
#
# Usage:
#   bash start_session.sh <session_name> [claude_args...]
#
# Examples:
#   bash start_session.sh builder                     # interactive
#   bash start_session.sh product --continue          # resume last
#   bash start_session.sh adhoc -p "quick question"   # one-shot
#
# This script:
# 1. Ensures the isolation directory exists and is current
# 2. Sets CLAUDE_CONFIG_DIR to the isolated directory
# 3. Launches claude with any extra arguments

set -euo pipefail

SESSIONS_BASE="/root/.claude_sessions"
MASTER_DIR="/root/.claude"
SETUP_SCRIPT="/opt/OS/scripts/auth_monitor/setup_isolation.sh"

SESSION_NAME="${1:?Usage: start_session.sh <session_name> [claude_args...]}"
shift

SESSION_DIR="$SESSIONS_BASE/$SESSION_NAME"

# Ensure isolation directory exists
if [[ ! -d "$SESSION_DIR" ]]; then
    echo "Session directory missing — running setup..."
    bash "$SETUP_SCRIPT"
fi

# Verify credentials exist in session dir
if [[ ! -f "$SESSION_DIR/.credentials.json" ]]; then
    if [[ -f "$MASTER_DIR/.credentials.json" ]]; then
        cp "$MASTER_DIR/.credentials.json" "$SESSION_DIR/.credentials.json"
        chmod 600 "$SESSION_DIR/.credentials.json"
        echo "Copied credentials from master to session dir"
    else
        echo "ERROR: No credentials found in master or session dir"
        exit 1
    fi
fi

# Verify settings.json symlink is valid
if [[ ! -e "$SESSION_DIR/settings.json" ]]; then
    echo "WARNING: settings.json missing — re-running setup"
    bash "$SETUP_SCRIPT"
fi

export CLAUDE_CONFIG_DIR="$SESSION_DIR"
echo "CC session '$SESSION_NAME' using CLAUDE_CONFIG_DIR=$SESSION_DIR"
exec claude "$@"
