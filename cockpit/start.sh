#!/bin/sh

# Copy nginx template — no secrets to inject (Clerk JWT auth handled by backend).
cp /etc/nginx/conf.d/default.conf.template /etc/nginx/conf.d/default.conf

# Start browse proxy for in-app browser (before nginx so it's ready for requests)
node /app/browse-proxy.mjs &

# Start nginx first so Fly health checks pass immediately.
# API proxy returns 502 until the SSH tunnel is up.
nginx -g 'daemon on;'

# Write SSH key from Fly secret to file if not already present.
if [ -n "$MESH_KEY" ] && [ ! -f /tmp/mesh_key ]; then
  printf '%s\n' "$MESH_KEY" > /tmp/mesh_key
  chmod 600 /tmp/mesh_key
fi

# Start tailscaled in userspace networking mode (no TUN needed in container)
tailscaled --state=/var/lib/tailscale/tailscaled.state \
  --socket=/var/run/tailscale/tailscaled.sock \
  --tun=userspace-networking &

sleep 2

# Connect to tailnet (non-fatal — nginx already serving static assets)
tailscale up --authkey="${TAILSCALE_AUTHKEY}" --hostname=umh-cockpit --accept-routes || true

sleep 2

# Persistent SSH tunnel replaces per-request socat+tailscale nc.
# SSH multiplexes all TCP connections over a single tailscale nc pipe.
# ProxyCommand routes through Tailscale's userspace network.
VPS_IP="${UMH_VPS_IP:-}"
KEY_FILE="/tmp/mesh_key"

if [ ! -f "$KEY_FILE" ]; then
  echo "[tunnel] MESH_KEY not set — no SSH tunnel, API will 502"
  wait
  exit 1
fi

if [ -z "$VPS_IP" ]; then
  echo "[tunnel] UMH_VPS_IP not set — no SSH tunnel, API will 502"
  wait
  exit 1
fi

KNOWN_HOSTS="/tmp/known_hosts"
if [ -n "$VPS_HOST_KEY" ]; then
  printf '%s\n' "$VPS_HOST_KEY" > "$KNOWN_HOSTS"
  chmod 600 "$KNOWN_HOSTS"
  HOST_CHECK_OPTS="-o StrictHostKeyChecking=yes -o UserKnownHostsFile=$KNOWN_HOSTS"
else
  echo "[tunnel] WARNING: VPS_HOST_KEY not set — falling back to no host verification"
  HOST_CHECK_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
fi

tunnel_loop() {
  delay=1
  while true; do
    echo "[tunnel] connecting to ${VPS_IP}:22 via tailscale nc..."
    ssh -o ProxyCommand="tailscale nc %h %p" \
        $HOST_CHECK_OPTS \
        -o ServerAliveInterval=15 \
        -o ServerAliveCountMax=3 \
        -o ExitOnForwardFailure=yes \
        -i "$KEY_FILE" \
        -N \
        -L 8091:127.0.0.1:8091 \
        -L 8097:127.0.0.1:8097 \
        -L 7880:127.0.0.1:7880 \
        -L 5173:127.0.0.1:5173 \
        -L 8086:127.0.0.1:8086 \
        -L 8095:127.0.0.1:8095 \
        -L 8100:127.0.0.1:8100 \
        "root@${VPS_IP}"
    echo "[tunnel] SSH exited ($?), reconnecting in ${delay}s..."
    sleep "$delay"
    if [ "$delay" -lt 30 ]; then
      delay=$((delay * 2))
    fi
  done
}

tunnel_loop &

# Keep container alive — wait on all background jobs
wait
