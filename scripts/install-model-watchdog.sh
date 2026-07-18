#!/bin/bash
# Install the UMH Model Watchdog as a systemd service.
# Monitors CC sessions for model downgrades from fable-5 and corrects settings.json.
set -euo pipefail

SCRIPT="/opt/OS/scripts/model-watchdog.py"
chmod +x "$SCRIPT"

# Create log directory
mkdir -p /opt/OS/logs

# Create systemd service (long-running daemon, not oneshot)
cat > /etc/systemd/system/umh-model-watchdog.service << 'EOF'
[Unit]
Description=UMH Model Watchdog — auto-correct CC model downgrades
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /opt/OS/scripts/model-watchdog.py
Restart=always
RestartSec=10
Nice=19
Environment=MODEL_WATCHDOG_TARGET=claude-fable-5
Environment=HOME=/root
WorkingDirectory=/opt/OS

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now umh-model-watchdog.service

echo "[model-watchdog] Installed and started."
echo "[model-watchdog] Check status: systemctl status umh-model-watchdog"
echo "[model-watchdog] View logs:    journalctl -u umh-model-watchdog -f"
echo "[model-watchdog] App logs:     tail -f /opt/OS/logs/model_watchdog.log"
echo "[model-watchdog] Target model: claude-fable-5 (override via MODEL_WATCHDOG_TARGET env)"
