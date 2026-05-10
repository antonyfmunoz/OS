#!/bin/bash
# ================================================
# EntrepreneurOS — One-line installer
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/[repo]/main/install.sh | bash
# ================================================

set -e

echo ""
echo "╔════════════════════════════════════╗"
echo "║     EntrepreneurOS — Installing    ║"
echo "╚════════════════════════════════════╝"
echo ""

# Check prerequisites
echo "→ Checking prerequisites..."

command -v docker >/dev/null 2>&1 || {
  echo "✗ Docker required."
  echo "  Install: https://docs.docker.com/get-docker/"
  exit 1
}

command -v python3 >/dev/null 2>&1 || {
  echo "✗ Python 3.11+ required."
  exit 1
}

PYTHON_VERSION=$(python3 -c "import sys; print(sys.version_info.minor)")
if [ "$PYTHON_VERSION" -lt 11 ]; then
  echo "✗ Python 3.11+ required. Found 3.$PYTHON_VERSION"
  exit 1
fi

echo "✅ Prerequisites met"
echo ""

# Clone or update
if [ -d "${UMH_ROOT:-/opt/OS}" ]; then
  echo "→ Updating existing installation..."
  cd ${UMH_ROOT:-/opt/OS}
  git pull
else
  echo "→ Installing to ${UMH_ROOT:-/opt/OS}..."
  git clone https://github.com/[repo]/eos ${UMH_ROOT:-/opt/OS}
  cd ${UMH_ROOT:-/opt/OS}
fi

# Setup env files
if [ ! -f "eos/.env" ]; then
  mkdir -p eos_ai services
  cp .env.example eos/.env
  cp .env.example services/.env
  echo "✅ Environment files created"
  echo ""
  echo "┌─────────────────────────────────────┐"
  echo "│  Next steps:                        │"
  echo "│  1. Edit eos/.env with your keys │"
  echo "│  2. Run: bash setup.sh              │"
  echo "│  3. Run: docker compose up -d       │"
  echo "└─────────────────────────────────────┘"
else
  echo "✅ Environment files already exist"
  echo "→ Run: bash setup.sh to configure"
fi

echo ""
echo "✅ Installation complete"
