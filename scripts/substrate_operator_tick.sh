#!/usr/bin/env bash
# Substrate operator tick — smallest safe drain+reconcile cycle for the
# local workstation loop. Repeatable; safe to run on a lightweight cron.
#
# Usage:
#   scripts/substrate_operator_tick.sh                       # default node
#   scripts/substrate_operator_tick.sh antony-workstation other-node
#   SUBSTRATE_NODES="a b" scripts/substrate_operator_tick.sh
#   scripts/substrate_operator_tick.sh --quiet               # suppress JSON
#   scripts/substrate_operator_tick.sh --install-cron        # print cron line
#   scripts/substrate_operator_tick.sh --help
#
# What it does (idempotent):
#   1. drain_all() each node inbox (events + results, one atomic read)
#   2. reconcile_recent() to mirror outcomes onto ritual.outputs
#   3. emit a lightweight report (store stats, recent failures, outcomes)
#
# This script does NOT loop. Put it behind cron/systemd-timer/etc if you
# want periodic ticks. Exit code propagates from the Python entrypoint:
# non-zero only on ingestion errors (malformed entries do not count).

set -euo pipefail

SCRIPT_PATH="$(readlink -f "$0" 2>/dev/null || echo "$0")"
REPO_DIR="${UMH_ROOT:-/opt/OS}"
LOG_DIR="${SUBSTRATE_TICK_LOG_DIR:-${UMH_ROOT:-/opt/OS}/logs}"
LOG_FILE="${LOG_DIR}/substrate_operator_tick.log"

print_help() {
    cat <<EOF
substrate_operator_tick.sh — drain + reconcile + report

Flags:
  --quiet              Redirect output to \$LOG_FILE (default ${LOG_FILE})
  --install-cron       Print a recommended crontab line and exit
  --help               This message

Positional args: one or more node ids (default: antony-workstation)
Env:
  SUBSTRATE_NODES      Space-separated node ids (lower priority than argv)
  SUBSTRATE_TICK_LOG_DIR  Override log directory for --quiet mode
EOF
}

print_cron() {
    cat <<EOF
# Recommended crontab (every 5 minutes, quiet, log rotated manually):
*/5 * * * * ${SCRIPT_PATH} --quiet

# Install with:
#   ( crontab -l 2>/dev/null; echo "*/5 * * * * ${SCRIPT_PATH} --quiet" ) | crontab -
# Inspect logs:
#   tail -f ${LOG_FILE}
EOF
}

QUIET=0
NODES=()
for arg in "$@"; do
    case "$arg" in
        --help|-h) print_help; exit 0 ;;
        --install-cron) print_cron; exit 0 ;;
        --quiet) QUIET=1 ;;
        --*) echo "unknown flag: $arg" >&2; exit 2 ;;
        *) NODES+=("$arg") ;;
    esac
done

if [ "${#NODES[@]}" -eq 0 ] && [ -n "${SUBSTRATE_NODES:-}" ]; then
    # shellcheck disable=SC2206
    NODES=(${SUBSTRATE_NODES})
fi
if [ "${#NODES[@]}" -eq 0 ]; then
    NODES=(antony-workstation)
fi

cd "$REPO_DIR"

ARGS=()
for n in "${NODES[@]}"; do
    ARGS+=(--node "$n")
done

run_py() {
    python3 ${UMH_ROOT:-/opt/OS}/scripts/substrate_drain_station.py \
        "${ARGS[@]}" \
        --reconcile \
        --reconcile-limit 20 \
        --report
}

# Print a tiny human-readable readiness banner alongside the JSON. Bounded,
# best-effort, never blocks the tick. Reads NodeRegistry + ResultStore only.
print_readiness_banner() {
    python3 - "${NODES[@]}" <<'PY' 2>/dev/null || true
import json
import sys
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
try:
    from eos_ai.substrate.result_query import station_readiness_report
except Exception as e:
    print(f"[readiness] import failed: {e}")
    raise SystemExit(0)

print("--- station readiness ---")
for node_id in sys.argv[1:]:
    try:
        rep = station_readiness_report(node_id)
    except Exception as e:
        print(f"  {node_id}: ERROR {e}")
        continue
    cls = rep.get("classification", "?")
    rec_obj = rep.get("recommended_scene") or {}
    rec = rec_obj.get("scene") or "(none)"
    inferred = rep.get("inferred_mode") or {}
    inf_scene = inferred.get("scene") or "(none)"
    inf_src = inferred.get("source") or "?"
    age = rep.get("heartbeat_age_s")
    age_s = f"{int(age)}s" if isinstance(age, (int, float)) else "n/a"
    fr = rep.get("fail_ratio", 0.0)
    rt = rep.get("recent_total", 0)
    miss = rep.get("missing_capabilities") or []
    miss_tag = f" missing={','.join(miss)}" if miss else ""
    reasons = rep.get("reasons") or []
    head = reasons[0] if reasons else ""
    print(
        f"  {node_id}: {cls}  scene={rec} (inferred={inf_scene}/{inf_src})  "
        f"hb_age={age_s}  recent={rt}  fail={fr:.0%}{miss_tag}  — {head}"
    )
PY
}

if [ "$QUIET" -eq 1 ]; then
    mkdir -p "$LOG_DIR"
    {
        echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) tick nodes=${NODES[*]} ==="
        print_readiness_banner
        run_py || echo "[tick] non-zero exit"
    } >>"$LOG_FILE" 2>&1
else
    print_readiness_banner
    run_py
fi
