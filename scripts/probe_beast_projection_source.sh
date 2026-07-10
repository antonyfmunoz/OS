#!/usr/bin/env bash
# Beast projection source-truth probe — READ-ONLY.
#
# Contract (docs/PROJECTION_SOURCE_TRUTH.md): establishes tier-2 (Beast working
# tree) source truth by directly observing the Windows node filesystem over SSH.
# Records git remote/branch/HEAD/dirty/upstream + client/server/schema presence
# per projection. Copies NO code into UMH. Writes only an evidence file.
#
# If the Beast is unreachable, prints UNREACHABLE and exits non-zero WITHOUT
# writing false VERIFIED status — the caller must mark rows UNVERIFIED/UNREACHABLE
# in data/umh/projection_reconciliation/projection_source_truth.json.
#
# Usage: scripts/probe_beast_projection_source.sh [OUTFILE]
set -uo pipefail  # not -e: a missing field must not abort the per-projection loop

BEAST="${BEAST_SSH:-}"
[ -z "$BEAST" ] && { echo "set BEAST_SSH"; exit 1; }
ROOT='C:\dev\dev'
OUT="${1:-/dev/stdout}"
REPOS=("EntrepreneurOS:eos" "CreatorOS:cos" "LyfeOS:lyfeos")

ssh_beast() { timeout 20 ssh -o BatchMode=yes -o ConnectTimeout=6 "$BEAST" "$1" 2>/dev/null; }

# Reachability gate — never claim VERIFIED without a live probe.
if ! ssh_beast "echo BEAST_SSH_OK" | grep -q BEAST_SSH_OK; then
  echo "BEAST_STATUS: UNREACHABLE (ssh failed) at $(cat /dev/null; echo probe-attempt)"
  exit 1
fi

echo "BEAST_STATUS: REACHABLE" > "$OUT"; echo "BEAST_STATUS: REACHABLE"
for pair in "${REPOS[@]}"; do
  name="${pair%%:*}"; pid="${pair##*:}"; dir="$ROOT\\$name"
  remote=$(ssh_beast "cd /d \"$dir\" 2>nul && git config --get remote.origin.url" | tr -d '\r')
  branch=$(ssh_beast "cd /d \"$dir\" 2>nul && git rev-parse --abbrev-ref HEAD" | tr -d '\r')
  head=$(ssh_beast "cd /d \"$dir\" 2>nul && git rev-parse --short HEAD" | tr -d '\r')
  dirty=$(ssh_beast "cd /d \"$dir\" 2>nul && git status --porcelain | find /c /v \"\"" | tr -d '\r ')
  upstream=$(ssh_beast "cd /d \"$dir\" 2>nul && git status -sb | findstr /B \"##\"" | head -1 | tr -d '\r')
  client=$(ssh_beast "cd /d \"$dir\" 2>nul && if exist client echo yes" | tr -d '\r')
  server=$(ssh_beast "cd /d \"$dir\" 2>nul && if exist server echo yes" | tr -d '\r')
  line="PROJECTION: $pid ($name) remote=$remote branch=$branch head=$head dirty=${dirty:-?} upstream=[$upstream] client=${client:-no} server=${server:-no}"
  echo "$line" | tee -a "$OUT"
done
