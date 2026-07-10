#!/usr/bin/env python3
"""Refresh Fly.io deploy token using the org token from 1Password.

The org token (fo1_ prefix) is long-lived and creates deploy macaroons
(fm2_ prefix) via `flyctl tokens create deploy`. The macaroon is what
the Machines API needs for `flyctl deploy`.

Usage:
    python3 scripts/refresh_fly_token.py
    export FLY_API_TOKEN=$(grep access_token /root/.fly/config.yml | awk '{print $2}')
    bash cockpit/deploy.sh
"""
import os
import subprocess
import sys

FLYCTL = "/root/.fly/bin/flyctl"
_V = os.getenv("UMH_OP_VAULT", "UMH-Production")
OP_URI = f"op://{_V}/Fly.io Org Token/credential"
AGENT_SOCK = os.path.expanduser("~/.fly/fly-agent.sock")

# Kill stale fly-agent — it caches old tokens and causes auth failures
subprocess.run(["pkill", "-9", "-f", "flyctl agent"], capture_output=True)
if os.path.exists(AGENT_SOCK):
    os.remove(AGENT_SOCK)

org_result = subprocess.run(
    ["op", "read", OP_URI],
    capture_output=True, text=True,
)
if org_result.returncode != 0:
    print(f"Error reading org token from 1Password: {org_result.stderr.strip()}")
    sys.exit(1)

org_token = org_result.stdout.strip()
if not org_token:
    print("Error: empty org token from 1Password")
    sys.exit(1)

result = subprocess.run(
    [FLYCTL, "tokens", "create", "deploy", "-a", "umh-cockpit"],
    capture_output=True, text=True,
    env={**os.environ, "FLY_API_TOKEN": org_token},
)

if result.returncode != 0:
    print(f"Error creating deploy token: {result.stderr.strip()}")
    sys.exit(1)

token = result.stdout.strip()
if not token:
    print("Error: empty deploy token returned")
    sys.exit(1)

with open("/root/.fly/config.yml", "w") as f:
    f.write(f"access_token: {token}\n")

print("Deploy token refreshed and saved to /root/.fly/config.yml")
