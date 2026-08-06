#!/bin/bash
# Install the UMH Model Watchdog as a systemd service.
# Hardened: env file for secrets, atomic state dir, duplicate-instance prevention.
set -euo pipefail

SCRIPT="/opt/OS/scripts/model-watchdog.py"
STATE_DIR="/opt/OS/data/runtime/model_watchdog"
ENV_FILE="/opt/OS/data/runtime/model_watchdog/env"
LOG_DIR="/opt/OS/logs"

chmod +x "$SCRIPT"
mkdir -p "$STATE_DIR" "$LOG_DIR"

# Create env file if missing (secrets go here, not in the unit)
if [ ! -f "$ENV_FILE" ]; then
    cat > "$ENV_FILE" << 'ENVEOF'
MODEL_WATCHDOG_TARGET=claude-fable-5
# DISCORD_BOT_TOKEN sourced from services/.env at runtime
# MODEL_WATCHDOG_DISCORD_CHANNEL=<channel-id>
ENVEOF
    chmod 600 "$ENV_FILE"
    echo "[model-watchdog] Created env file at $ENV_FILE — configure Discord settings there."
fi

# Preserve the old unit for rollback
if [ -f /etc/systemd/system/umh-model-watchdog.service ]; then
    cp /etc/systemd/system/umh-model-watchdog.service \
       /etc/systemd/system/umh-model-watchdog.service.bak
    echo "[model-watchdog] Previous unit backed up to .bak"
fi

cat > /etc/systemd/system/umh-model-watchdog.service << EOF
[Unit]
Description=UMH Model Watchdog — governed model-provenance primitive
After=network.target
# Prevent duplicate instances
Conflicts=umh-model-watchdog.service

[Service]
Type=simple
ExecStart=/usr/bin/python3 $SCRIPT
Restart=always
RestartSec=15
Nice=19

# Environment
Environment=HOME=/root
Environment=UMH_ROOT=/opt/OS
EnvironmentFile=-/opt/OS/services/.env
EnvironmentFile=-$ENV_FILE
WorkingDirectory=/opt/OS

# Stdout/stderr to journal
StandardOutput=journal
StandardError=journal

# Graceful shutdown
TimeoutStopSec=10
KillSignal=SIGTERM

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now umh-model-watchdog.service

echo "[model-watchdog] Installed and started."
echo "[model-watchdog] Status:    systemctl status umh-model-watchdog"
echo "[model-watchdog] Logs:      journalctl -u umh-model-watchdog -f"
echo "[model-watchdog] App logs:  tail -f /opt/OS/logs/model_watchdog.log"
echo "[model-watchdog] Health:    python3 $SCRIPT health"
echo "[model-watchdog] Summary:   python3 $SCRIPT summary [session_id] [since_date]"
echo "[model-watchdog] State dir: $STATE_DIR"
