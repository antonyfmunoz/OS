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
# Protected processes identified by /proc/<pid>/exe realpath (not argv).
# PID-reuse guard: process start time checked before and after scan.
#
# Install: bash scripts/install-cpu-watchdog.sh

set -euo pipefail

LOG="/opt/OS/logs/cpu_watchdog.log"
CORES=$(nproc 2>/dev/null || echo 4)
LOAD=$(awk '{print $1}' /proc/loadavg)
LOAD_INT=$(echo "$LOAD * 100 / $CORES" | bc 2>/dev/null || echo 0)

WARN_THRESHOLD=200
STOP_THRESHOLD=300
KILL_THRESHOLD=400

timestamp() { date '+%Y-%m-%d %H:%M:%S'; }

if [ "$LOAD_INT" -lt "$WARN_THRESHOLD" ]; then
    exit 0
fi

echo "$(timestamp) [WARN] load=$LOAD cores=$CORES ($(echo "scale=1; $LOAD / $CORES" | bc)/core)" >> "$LOG"

# Protected binaries identified by /proc/<pid>/exe realpath
PROTECTED_EXES="/usr/sbin/sshd|/usr/bin/sshd|/usr/lib/systemd/systemd|/usr/bin/dockerd|/usr/sbin/dockerd|/usr/bin/containerd|/usr/sbin/containerd|/usr/sbin/tailscaled"

get_proc_starttime() {
    awk '{print $22}' "/proc/$1/stat" 2>/dev/null || echo ""
}

is_protected() {
    local pid="$1"
    local exe
    exe=$(readlink -f "/proc/$pid/exe" 2>/dev/null || echo "")
    if echo "$exe" | grep -qE "$PROTECTED_EXES"; then
        return 0
    fi
    # Skip interactive sessions (user's terminal)
    local tty
    tty=$(ps -o tty= -p "$pid" 2>/dev/null || echo "?")
    if [[ "$tty" == pts/* ]]; then
        return 0
    fi
    return 1
}

safe_signal() {
    local sig="$1" pid="$2" starttime="$3"
    local current_starttime
    current_starttime=$(get_proc_starttime "$pid")
    if [ -z "$current_starttime" ] || [ "$current_starttime" != "$starttime" ]; then
        return 1
    fi
    kill "-$sig" "$pid" 2>/dev/null || true
}

get_top_offenders() {
    ps aux --sort=-%cpu | awk 'NR>1 && $3+0 > 25.0 {print $2, $3}' | \
    while read -r PID CPU; do
        if is_protected "$PID"; then
            continue
        fi
        local STARTTIME
        STARTTIME=$(get_proc_starttime "$PID")
        if [ -z "$STARTTIME" ]; then
            continue
        fi
        local CMD
        CMD=$(readlink -f "/proc/$PID/exe" 2>/dev/null || ps -o comm= -p "$PID" 2>/dev/null || echo "unknown")
        echo "$PID $STARTTIME $CMD $CPU"
    done
}

if [ "$LOAD_INT" -ge "$KILL_THRESHOLD" ]; then
    echo "$(timestamp) [KILL] load/core > 4.0 — killing runaway processes" >> "$LOG"
    get_top_offenders | while read -r PID STARTTIME CMD CPU; do
        echo "$(timestamp) [KILL] pid=$PID cmd=$CMD cpu=${CPU}%" >> "$LOG"
        safe_signal 9 "$PID" "$STARTTIME"
    done
elif [ "$LOAD_INT" -ge "$STOP_THRESHOLD" ]; then
    echo "$(timestamp) [STOP] load/core > 3.0 — pausing heavy processes" >> "$LOG"
    get_top_offenders | while read -r PID STARTTIME CMD CPU; do
        echo "$(timestamp) [STOP] pid=$PID cmd=$CMD cpu=${CPU}%" >> "$LOG"
        safe_signal STOP "$PID" "$STARTTIME"
        (sleep 60 && safe_signal CONT "$PID" "$STARTTIME") &
    done
fi

# Trim log
if [ -f "$LOG" ] && [ "$(wc -l < "$LOG")" -gt 1000 ]; then
    tail -500 "$LOG" > "${LOG}.tmp" && mv "${LOG}.tmp" "$LOG"
fi
