#!/usr/bin/env bash
# dc-up.sh — Start Docker services with secrets from 1Password
#
# Generates ephemeral .env files from 1Password references, starts containers,
# then shreds the plaintext files. Containers retain env vars in process memory.
#
# Usage: bash infra/scripts/dc-up.sh [docker compose args...]
# Examples:
#   bash infra/scripts/dc-up.sh                    # start all services
#   bash infra/scripts/dc-up.sh os-discord          # start one service
#   bash infra/scripts/dc-up.sh --build             # rebuild + start
set -euo pipefail

UMH_ROOT="${UMH_ROOT:-/opt/OS}"
cd "$UMH_ROOT"

SERVICES_TPL="services/.env.tpl"
UMH_TPL="infra/docker/umh.env.tpl"
SERVICES_ENV="services/.env"
UMH_ENV="infra/docker/umh.env"

cleanup() {
    shred -u "$SERVICES_ENV" "$UMH_ENV" 2>/dev/null || true
}
trap cleanup EXIT

if ! command -v op &>/dev/null; then
    echo "[dc-up] ERROR: 1Password CLI (op) not found. Install it first."
    exit 1
fi

if ! op whoami &>/dev/null; then
    echo "[dc-up] ERROR: 1Password CLI not authenticated."
    echo "  Set OP_SERVICE_ACCOUNT_TOKEN or run 'op signin'."
    exit 1
fi

echo "[dc-up] Resolving secrets from 1Password..."
op inject -f -i "$SERVICES_TPL" -o "$SERVICES_ENV"
op inject -f -i "$UMH_TPL" -o "$UMH_ENV"
chmod 600 "$SERVICES_ENV" "$UMH_ENV"

# Allow Docker bridge traffic to reach voice server on host port 8096.
# os-operator proxies voice WS via host.docker.internal — blocked by UFW without this.
VOICE_BRIDGE=$(docker network inspect os_eos_network -f '{{index .Options "com.docker.network.bridge.name"}}' 2>/dev/null || true)
if [ -z "$VOICE_BRIDGE" ]; then
    VOICE_BRIDGE=$(ip -o link show type bridge | grep -o 'br-[a-f0-9]*' | head -1)
fi
if [ -n "$VOICE_BRIDGE" ] && ! iptables -C INPUT -i "$VOICE_BRIDGE" -p tcp --dport 8096 -j ACCEPT 2>/dev/null; then
    iptables -I INPUT -i "$VOICE_BRIDGE" -p tcp --dport 8096 -j ACCEPT -m comment --comment "voice-server-from-docker"
    echo "[dc-up] Added iptables rule: Docker bridge → voice server :8096"
fi

# ── Security hardening: close permissive iptables rules ─────────────────
# Remove any 0.0.0.0/0 ACCEPT rules for Ollama and voice server.
# Only Docker bridge, localhost, and Tailscale should reach these ports.
for PORT in 11434 8096; do
    # Remove ALL broad 0.0.0.0/0 ACCEPT rules for this port (loop until none remain)
    while iptables -L INPUT -n 2>/dev/null | grep -q "0\.0\.0\.0/0.*0\.0\.0\.0/0.*tcp dpt:${PORT}"; do
        RULE_NUM=$(iptables -L INPUT -n --line-numbers 2>/dev/null | grep "0\.0\.0\.0/0.*0\.0\.0\.0/0.*tcp dpt:${PORT}" | tail -1 | awk '{print $1}')
        [ -n "$RULE_NUM" ] && iptables -D INPUT "$RULE_NUM" 2>/dev/null || break
    done
    # Add restrictive ACCEPT rules if not present
    for SRC in 172.16.0.0/12 127.0.0.0/8 100.64.0.0/10; do
        iptables -C INPUT -s "$SRC" -p tcp --dport "$PORT" -j ACCEPT 2>/dev/null || \
            iptables -I INPUT -s "$SRC" -p tcp --dport "$PORT" -j ACCEPT \
                -m comment --comment "port-${PORT}-from-${SRC}"
    done
    # Explicit DROP after ACCEPT rules — catches traffic even if UFW default policy leaks
    iptables -C INPUT -p tcp --dport "$PORT" -j DROP -m comment --comment "block-${PORT}-public" 2>/dev/null || \
        iptables -A INPUT -p tcp --dport "$PORT" -j DROP -m comment --comment "block-${PORT}-public"
done

# Defense-in-depth: restrict Docker-published ports via DOCKER-USER chain.
# Even with 127.0.0.1 binding, this blocks if Docker config reverts.
for PORT in 8080 8091 8765; do
    iptables -C DOCKER-USER -p tcp --dport "$PORT" -j DROP 2>/dev/null || \
        iptables -A DOCKER-USER -p tcp --dport "$PORT" -j DROP \
            -m comment --comment "block-external-${PORT}"
    for SRC in 127.0.0.0/8 172.16.0.0/12 100.64.0.0/10; do
        iptables -C DOCKER-USER -s "$SRC" -p tcp --dport "$PORT" -j ACCEPT 2>/dev/null || \
            iptables -I DOCKER-USER -s "$SRC" -p tcp --dport "$PORT" -j ACCEPT \
                -m comment --comment "allow-${SRC}-to-${PORT}"
    done
done
echo "[dc-up] Firewall hardening applied"

echo "[dc-up] Starting containers..."
docker compose up -d "$@"

echo "[dc-up] Waiting for containers to load env vars..."
sleep 3

echo "[dc-up] Shredding ephemeral .env files..."
# cleanup runs via trap

echo "[dc-up] Done. Verify with: docker compose ps"
