#!/bin/bash
# ================================================
# EntrepreneurOS — First-run setup
# Run after editing .env with your API keys
# ================================================

set -e

echo ""
echo "╔════════════════════════════════════╗"
echo "║   EntrepreneurOS — Setup Wizard    ║"
echo "╚════════════════════════════════════╝"
echo ""

# Verify .env exists
if [ ! -f "eos_ai/.env" ]; then
  echo "✗ eos_ai/.env not found"
  echo "  Run install.sh first"
  exit 1
fi

# Check for required keys
source eos_ai/.env 2>/dev/null || true

if [ -z "$DATABASE_URL" ]; then
  echo "⚠ DATABASE_URL not set in eos_ai/.env"
  echo "  Get a free database at neon.tech"
  echo "  Then add DATABASE_URL to eos_ai/.env"
  exit 1
fi

# Install Python dependencies
echo "→ Installing Python dependencies..."
pip3 install -r services/requirements.txt \
  --break-system-packages -q 2>/dev/null || \
pip3 install -r services/requirements.txt -q
echo "✅ Dependencies installed"

# Install Ollama if not present
if ! command -v ollama >/dev/null 2>&1; then
  echo "→ Installing Ollama (free local AI)..."
  curl -fsSL https://ollama.ai/install.sh | sh
  echo "→ Downloading Qwen2.5:3b model..."
  ollama pull qwen2.5:3b
  echo "✅ Local AI ready"
else
  echo "✅ Ollama already installed"
fi

# Run Python setup wizard
echo ""
echo "→ Configuring your instance..."
echo ""
python3 -c "
import sys
import os; sys.path.insert(0, os.environ.get('UMH_ROOT') or '/opt/OS')
from eos_ai.setup_wizard import run_setup
run_setup()
"

echo ""
echo "✅ Setup complete"
echo ""
echo "→ Start EOS: docker compose up -d"
echo "→ View logs: docker compose logs -f"
