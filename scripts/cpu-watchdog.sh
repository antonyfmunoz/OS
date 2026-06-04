#!/bin/bash
# UMH CPU Watchdog — last-resort defense against Hostinger throttling.
#
# Runs every 30 seconds via systemd timer. Checks 1-minute load average.
# If load per core exceeds threshold, takes progressive action:
#
#   Level 1 (load/core > 2.0): Log warning
#   Level 2 (load/core > 3.0): SIGSTOP heaviest non-essential processes
#   Level 3 (load/core > 4.0): SIGKILL runaway processes
#
# Protected processes (never killed): systemd, sshd, dockerd, containerd,
#   tailscaled, Claude Code interactive sessions (pts/* terminals).
#
# Install: bash scripts/install-cpu-watchdog.sh

set -euo pipefail

LOG="/opt/OS/logs/cpu_watchdog.log"
CORES=$(nproc 2>/dev/null || echo 4)
LOAD=$(awk '{print $1}' /proc/loadavg)
LOAD_INT=$(echo "$LOAD * 100 / $CORES" | bc 2>/dev/null || echo 0)

# Thresholds as percentages of per-core load (200 = 2.0 load/core)
WARN_THRESHOLD=200
STOP_THRESHOLD=300
KILL_THRESHOLD=400

timestamp() { date '+%Y-%m-%d %H:%M:%S'; }

if [ "$LOAD_INT" -lt "$WARN_THRESHOLD" ]; then
    exit 0
fi

echo "$(timestamp) [WARN] load=$LOAD cores=$CORES ($(echo "scale=1; $LOAD / $CORES" | bc)/core)" >> "$LOG"

# Find top CPU consumers, exclude protected processes
get_top_offenders() {
    ps aux --sort=-%cpu | awk 'NR>1 && $3+0 > 25.0 {print $2, $11, $3}' | \
    while read -r PID CMD CPU; do
        # Skip protected processes
        case "$CMD" in
            *sshd*|*systemd*|*dockerd*|*containerd*|*tailscaled*|*kworker*|*ksoftirq*)
                continue ;;
        esac
        # Skip interactive Claude Code sessions (user is actively using them)
        TTY=$(ps -o tty= -p "$PID" 2>/dev/null || echo "?")
        if [[ "$TTY" == pts/* ]]; then
            continue
        fi
        echo "$PID $CMD $CPU"
    done
}

if [ "$LOAD_INT" -ge "$KILL_THRESHOLD" ]; then
    echo "$(timestamp) [KILL] load/core > 4.0 — killing runaway processes" >> "$LOG"
    get_top_offenders | while read -r PID CMD CPU; do
        echo "$(timestamp) [KILL] pid=$PID cmd=$CMD cpu=${CPU}%" >> "$LOG"
        kill -9 "$PID" 2>/dev/null || true
    done
elif [ "$LOAD_INT" -ge "$STOP_THRESHOLD" ]; then
    echo "$(timestamp) [STOP] load/core > 3.0 — pausing heavy processes" >> "$LOG"
    get_top_offenders | while read -r PID CMD CPU; do
        echo "$(timestamp) [STOP] pid=$PID cmd=$CMD cpu=${CPU}%" >> "$LOG"
        kill -STOP "$PID" 2>/dev/null || true
        # Auto-resume after 60 seconds
        (sleep 60 && kill -CONT "$PID" 2>/dev/null) &
    done
fi

# Trim log to last 1000 lines
if [ -f "$LOG" ] && [ "$(wc -l < "$LOG")" -gt 1000 ]; then
    tail -500 "$LOG" > "${LOG}.tmp" && mv "${LOG}.tmp" "$LOG"
fi
