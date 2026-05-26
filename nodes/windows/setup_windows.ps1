# UMH Node Daemon — Windows Setup Script
# Run from PowerShell as Administrator

$ErrorActionPreference = "Stop"
$UMH_DIR = "$env:PROGRAMDATA\UMH"

Write-Host "=== UMH Node Daemon Setup ===" -ForegroundColor Cyan

# Create directory structure
New-Item -ItemType Directory -Force -Path $UMH_DIR | Out-Null
New-Item -ItemType Directory -Force -Path "$UMH_DIR\logs" | Out-Null

# Prompt for configuration
$VPS_HOST = Read-Host "VPS Tailscale IP (e.g., 100.77.233.50)"
$NODE_ID = Read-Host "Node ID (e.g., windows-desktop)"
$TOKEN = Read-Host "Node token (from VPS config)"
$HOSTNAME = $env:COMPUTERNAME

# Write .env
@"
UMH_VPS_HOST=$VPS_HOST
UMH_VPS_PORT=8094
UMH_NODE_TOKEN=$TOKEN
UMH_NODE_ID=$NODE_ID
UMH_HOSTNAME=$HOSTNAME
"@ | Set-Content "$UMH_DIR\.env"

# Write default config
@"
[connection]
vps_host = "$VPS_HOST"
vps_port = 8094
reconnect_max_backoff_s = 60

[identity]
node_id = "$NODE_ID"
hostname = "$HOSTNAME"

[capabilities.shell]
enabled = true
max_risk_class = "IRREVERSIBLE_WRITE"

[capabilities.filesystem]
enabled = true
max_risk_class = "IRREVERSIBLE_WRITE"
allowed_paths = ["C:\\Users\\$env:USERNAME"]

[capabilities.desktop]
enabled = true
max_risk_class = "IRREVERSIBLE_WRITE"

[capabilities.clipboard]
enabled = true
max_risk_class = "SAFE_WRITE"

[signals.metrics]
interval_s = 30

[signals.workspace]
enabled = true
debounce_s = 2

[signals.filewatch]
enabled = false
paths = []
"@ | Set-Content "$UMH_DIR\umh_node.toml"

Write-Host "`nConfig written to $UMH_DIR" -ForegroundColor Green
Write-Host "  .env: $UMH_DIR\.env"
Write-Host "  config: $UMH_DIR\umh_node.toml"

# Install Python dependencies
Write-Host "`nInstalling dependencies..." -ForegroundColor Yellow
pip install -r requirements-windows.txt

Write-Host "`n=== Setup Complete ===" -ForegroundColor Cyan
Write-Host "To run the service:  python -m nodes.windows.umh_node.service"
Write-Host "To run the tray:     python -m nodes.windows.umh_desktop.tray"
Write-Host "To install as Windows Service: python -m nodes.windows.umh_node.service install"
