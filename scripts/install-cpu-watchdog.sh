#!/bin/bash
# Install the UMH CPU watchdog as a systemd timer.
# Runs every 30 seconds, checks CPU load, takes action if needed.
set -euo pipefail

SCRIPT="/opt/OS/scripts/cpu-watchdog.sh"
chmod +x "$SCRIPT"

# Create systemd service
cat > /etc/systemd/system/umh-cpu-watchdog.service << 'EOF'
[Unit]
Description=UMH CPU Watchdog
After=network.target

[Service]
Type=oneshot
ExecStart=/opt/OS/scripts/cpu-watchdog.sh
Nice=19
EOF

# Create systemd timer (every 30 seconds)
cat > /etc/systemd/system/umh-cpu-watchdog.timer << 'EOF'
[Unit]
Description=UMH CPU Watchdog Timer

[Timer]
OnBootSec=60
OnUnitActiveSec=30
AccuracySec=5

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now umh-cpu-watchdog.timer

echo "[cpu-watchdog] Installed and started."
echo "[cpu-watchdog] Check status: systemctl status umh-cpu-watchdog.timer"
echo "[cpu-watchdog] View logs: cat /opt/OS/logs/cpu_watchdog.log"
