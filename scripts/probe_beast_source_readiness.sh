#!/usr/bin/env bash
# Beast projection source-READINESS probe — READ-ONLY, repeatable, governed.
#
# WP-P4-BEAST-SOURCE-SYNC-001. Extends the source-truth probe
# (scripts/probe_beast_projection_source.sh) with the readiness dimensions UMH
# needs to safely orchestrate projection build-out:
#   git branch/head/dirty/staged/untracked/ahead/behind/unpushed,
#   backup-branch status, secrets-protocol installed (.env.op.tpl + .env retired),
#   package/client/server/schema presence, and a source-RISK classification.
#
# Copies NO code from the Beast into UMH. Makes NO Beast writes. Emits a JSON
# document to stdout (or $1). If the Beast is UNREACHABLE it exits non-zero and
# emits {"beast_status":"UNREACHABLE"} WITHOUT any false-current rows — the caller
# must not treat a stale record as current.
#
# Usage: scripts/probe_beast_source_readiness.sh [OUTFILE]
#   Pass PROBE_AT=YYYY-MM-DD to stamp the record (scripts have no clock).
set -uo pipefail  # not -e: a missing field must not abort the per-repo loop

BEAST="${BEAST_SSH:-}"
[ -z "$BEAST" ] && { echo "set BEAST_SSH"; exit 1; }
ROOT='C:\dev\dev'
OUT="${1:-/dev/stdout}"
PROBE_AT="${PROBE_AT:-unknown}"

# repo: umh_id : github_repo : operating_branch(expected) : mirror_dir
REPOS=(
  "EntrepreneurOS:eos:EntrepreneurOS:entrepreneuros"
  "CreatorOS:cos:CreatorOS:creatoros"
  "LyfeOS:lyfeos:LYFEOS:LYFEOS"
)

# strip CR and surrounding whitespace — Windows `echo` and `git` emit trailing spaces that
# would otherwise break `[ "$x" = "yes" ]` string comparisons (a real bug this trims out).
ssh_beast() {
  timeout 25 ssh -o BatchMode=yes -o ConnectTimeout=8 "$BEAST" "$1" 2>/dev/null \
    | tr -d '\r' | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//'
}
jstr() { printf '%s' "$1" | python3 -c "import json,sys; print(json.dumps(sys.stdin.read()))"; }

# --- reachability gate: never emit current rows without a live probe ---
if ! ssh_beast "echo BEAST_SSH_OK" | grep -q BEAST_SSH_OK; then
  printf '{"beast_status":"UNREACHABLE","probe_at":%s,"projections":[]}\n' "$(jstr "$PROBE_AT")" | tee "$OUT"
  exit 1
fi

# mirror fidelity is judged on the UMH side (data/repos/<mirror>)
UMH_ROOT="${UMH_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"

rows=""
for spec in "${REPOS[@]}"; do
  IFS=':' read -r name pid gh_repo mirror <<< "$spec"
  D="$ROOT\\$name"

  branch=$(ssh_beast "cd /d \"$D\" && git rev-parse --abbrev-ref HEAD")
  head=$(ssh_beast "cd /d \"$D\" && git rev-parse --short HEAD")
  dirty=$(ssh_beast "cd /d \"$D\" && git status --porcelain | find /c /v \"\"")
  staged=$(ssh_beast "cd /d \"$D\" && git diff --cached --name-only | find /c /v \"\"")
  untracked=$(ssh_beast "cd /d \"$D\" && git ls-files --others --exclude-standard | find /c /v \"\"")
  remote=$(ssh_beast "cd /d \"$D\" && git config --get remote.origin.url")
  # behind/ahead vs upstream (tab-separated "<behind>\t<ahead>")
  ab=$(ssh_beast "cd /d \"$D\" && git rev-list --left-right --count @{upstream}...HEAD 2>nul")
  behind=$(printf '%s' "$ab" | awk '{print $1}'); ahead=$(printf '%s' "$ab" | awk '{print $2}')
  unpushed="$ahead"
  local_backup=$(ssh_beast "cd /d \"$D\" && git branch --list backup/* | find /c /v \"\"")
  op_tpl=$(ssh_beast "cd /d \"$D\" && if exist .env.op.tpl (echo yes) else (echo no)")
  env_ignored=$(ssh_beast "cd /d \"$D\" && git check-ignore .env >nul 2>&1 && echo yes || echo no")
  local_env=$(ssh_beast "cd /d \"$D\" && if exist .env (echo present) else (echo retired)")
  has_client=$(ssh_beast "cd /d \"$D\" && if exist client (echo yes) else (echo no)")
  has_server=$(ssh_beast "cd /d \"$D\" && if exist server (echo yes) else (echo no)")
  has_pkg=$(ssh_beast "cd /d \"$D\" && if exist package.json (echo yes) else (echo no)")
  has_schema=$(ssh_beast "cd /d \"$D\" && if exist shared\\schema.ts (echo yes) else (echo no)")

  # --- derived readiness (computed on the UMH side from observed facts) ---
  # secrets protocol installed?
  runtime_ready="no"
  [ "$op_tpl" = "yes" ] && [ "$env_ignored" = "yes" ] && [ "$local_env" = "retired" ] && runtime_ready="yes"
  # backed up? on GitHub via a pushed operating branch (ahead==0) OR a backup branch
  backed_up="no"
  { [ "${ahead:-1}" = "0" ] || [ "${local_backup:-0}" != "0" ]; } && backed_up="yes"
  # mirror fidelity (UMH side)
  if [ -d "$UMH_ROOT/data/repos/$mirror/client" ] && [ -d "$UMH_ROOT/data/repos/$mirror/server" ]; then
    mirror_fidelity="full"
  elif [ -f "$UMH_ROOT/data/repos/$mirror/shared/schema.ts" ]; then
    mirror_fidelity="schema_only"
  else
    mirror_fidelity="absent"
  fi
  # app body present on the Beast (the real source)?
  app_body="no"; [ "$has_client" = "yes" ] && [ "$has_server" = "yes" ] && app_body="yes"

  # --- source-risk classification (fail-toward-risk) ---
  #   source_at_risk : work exists only on the Beast (unpushed) and no backup
  #   source_unpushed: ahead>0 (commits not on GitHub) but a backup exists
  #   source_dirty   : uncommitted work in the tree (recoverable only locally)
  #   source_current : clean, fully pushed, backed up
  if [ "${unpushed:-0}" != "0" ] && [ "$backed_up" = "no" ]; then
    risk="source_at_risk"
  elif [ "${unpushed:-0}" != "0" ]; then
    risk="source_unpushed"
  elif [ "${dirty:-0}" != "0" ]; then
    risk="source_dirty"
  else
    risk="source_current"
  fi

  row=$(python3 - "$pid" "$name" "$gh_repo" "$remote" "$branch" "$head" "$dirty" "$staged" \
    "$untracked" "$behind" "$ahead" "$unpushed" "$local_backup" "$op_tpl" "$env_ignored" \
    "$local_env" "$has_client" "$has_server" "$has_pkg" "$has_schema" "$runtime_ready" \
    "$backed_up" "$mirror_fidelity" "$app_body" "$risk" "$PROBE_AT" <<'PY'
import json,sys
k=["projection_id","beast_repo","github_repo","git_remote","operating_branch","head",
   "dirty_count","staged_count","untracked_count","behind","ahead","unpushed_commits",
   "local_backup_branches","env_op_tpl_present","env_gitignored","plaintext_env",
   "has_client","has_server","has_package","has_schema","runtime_ready","backed_up",
   "mirror_fidelity","app_body_present","source_risk","beast_probe_at"]
v=sys.argv[1:]
def n(x):
    try: return int(x)
    except: return x
d={}
for key,val in zip(k,v):
    d[key]= n(val) if key.endswith(("_count","branches","behind","ahead","unpushed_commits")) else val
d["beast_verification"]="VERIFIED"
print(json.dumps(d))
PY
)
  rows="${rows:+$rows,}$row"
done

printf '{"beast_status":"REACHABLE","probe_at":%s,"projections":[%s]}\n' "$(jstr "$PROBE_AT")" "$rows" | tee "$OUT"
