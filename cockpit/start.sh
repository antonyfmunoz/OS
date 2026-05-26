#!/bin/sh

# Start nginx first so Fly health checks pass immediately.
# API proxy returns 502 until Tailscale bridge is up.
nginx -g 'daemon on;'

# Start tailscaled in userspace networking mode (no TUN needed in container)
tailscaled --state=/var/lib/tailscale/tailscaled.state \
  --socket=/var/run/tailscale/tailscaled.sock \
  --tun=userspace-networking &

sleep 2

# Connect to tailnet (non-fatal — nginx already serving static assets)
tailscale up --authkey="${TAILSCALE_AUTHKEY}" --hostname=umh-cockpit --accept-routes || true

sleep 2

# Bridge localhost:8091 → VPS:8091 through Tailscale's userspace network.
# socat binds a local TCP listener and pipes each connection through
# "tailscale nc" which routes through the Tailscale tunnel.
VPS_IP="100.77.233.50"
VPS_PORT="8091"
socat TCP-LISTEN:8091,fork,reuseaddr EXEC:"tailscale nc ${VPS_IP} ${VPS_PORT}",nofork &

# Keep container alive — wait on all background jobs
wait
