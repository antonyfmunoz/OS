#!/usr/bin/env bash
# workstation_daemon.sh — Launch the supervised station daemon on Linux/VPS.
#
# Usage:
#   ./scripts/workstation_daemon.sh [--profile founder_workstation]
#
# For systemd auto-start, create a unit file:
#   /etc/systemd/system/eos-workstation.service
#   [Unit]
#   Description=EOS Workstation Daemon
#   After=network.target
#
#   [Service]
#   Type=simple
#   User=root
#   WorkingDirectory=/opt/OS
#   ExecStart=/opt/OS/scripts/workstation_daemon.sh
#   Restart=always
#   RestartSec=5
#
#   [Install]
#   WantedBy=multi-user.target
#
# Then: systemctl enable eos-workstation && systemctl start eos-workstation

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Defaults
PROFILE="${1:-}"
NODE_ID="${EOS_NODE_ID:-antony-workstation}"

ARGS=(
    "--node-id" "$NODE_ID"
    "--poll-interval" "1.0"
    "--heartbeat-interval" "15.0"
)

if [ -n "$PROFILE" ]; then
    # Strip --profile flag if passed as --profile=X
    PROFILE="${PROFILE#--profile }"
    PROFILE="${PROFILE#--profile=}"
    if [ -n "$PROFILE" ]; then
        ARGS+=("--profile" "$PROFILE")
    fi
fi

echo "[workstation_daemon.sh] starting supervised daemon node=$NODE_ID"
exec python3 -m eos_ai.substrate.daemon_supervisor "${ARGS[@]}"
