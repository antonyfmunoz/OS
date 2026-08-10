#!/usr/bin/env bash
# Dispatch a Remotion render to the Beast and pull the result back.
#
# The VPS never renders video (node-role discipline: orchestrator only).
# The Beast holds the project at C:\dev\dev\OS\knowledge\skills\marketing\
# content\remotion with node_modules installed (2026-08-10, remotion 4.0.436).
#
# Usage:
#   scripts/beast_remotion_render.sh <composition_id> <output_name.mp4> [props.json]
#
#   composition_id  e.g. MyComp (see src/Root.tsx on the Beast mirror)
#   output_name     filename only; lands in data/renders/ on the VPS
#   props.json      optional local JSON file passed as input props
#
# Requires: Tailscale up, Beast SSH reachable (reference_windows_ssh).
set -euo pipefail

BEAST="antonys beast pc@100.74.199.102"
REMOTE_DIR='C:\dev\dev\OS\knowledge\skills\marketing\content\remotion'
LOCAL_OUT_DIR="${UMH_ROOT:-/opt/OS}/data/renders"

COMP="${1:?usage: beast_remotion_render.sh <composition_id> <out.mp4> [props.json]}"
OUT="${2:?output filename required}"
PROPS_FILE="${3:-}"

# NOTE: scp cannot parse the space in the Beast username ("antonys beast pc"),
# so file transfer uses base64 over ssh instead. PowerShell emits CRLF line
# endings — tr strips them before decoding.

PROPS_ARG=""
if [ -n "$PROPS_FILE" ]; then
  # Ship props to the Beast beside the project (base64 over ssh, scp-safe).
  base64 -w0 "$PROPS_FILE" | ssh -o BatchMode=yes "$BEAST" \
    "powershell -Command \"[IO.File]::WriteAllBytes('$REMOTE_DIR\\props_dispatch.json',[Convert]::FromBase64String([Console]::In.ReadToEnd()))\""
  PROPS_ARG="--props=props_dispatch.json"
fi

echo "[dispatch] rendering $COMP -> $OUT on Beast..."
ssh -o ConnectTimeout=10 -o BatchMode=yes "$BEAST" \
  "cd /d $REMOTE_DIR && npx remotion render src/index.ts $COMP out\\$OUT $PROPS_ARG --log=error"

mkdir -p "$LOCAL_OUT_DIR"
TMP_B64="$(mktemp)"
trap 'rm -f "$TMP_B64"' EXIT
ssh -o ConnectTimeout=10 -o BatchMode=yes "$BEAST" \
  "powershell -Command \"[Convert]::ToBase64String([IO.File]::ReadAllBytes('$REMOTE_DIR\\out\\$OUT'))\"" \
  > "$TMP_B64"
tr -d '\r\n' < "$TMP_B64" | base64 -d > "$LOCAL_OUT_DIR/$OUT"
echo "[dispatch] done -> $LOCAL_OUT_DIR/$OUT"
ls -la "$LOCAL_OUT_DIR/$OUT"
file "$LOCAL_OUT_DIR/$OUT"
