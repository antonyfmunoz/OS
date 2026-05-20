#!/usr/bin/env bash
# sync_all.sh — cross-device git sync check and fast-forward
#
# Usage:
#   scripts/sync_all.sh              # report sync state (read-only)
#   scripts/sync_all.sh --dry-run    # same as no-arg (explicit)
#   scripts/sync_all.sh --pull       # fast-forward strictly-behind clones
#
# When run from VPS, also checks Windows clones via SSH (requires
# Tailscale connectivity and SSH key auth).
#
# Exit codes:
#   0 — all clones in sync (or successfully pulled)
#   1 — drift detected (dry-run) or pull failed
#   2 — configuration error

set -euo pipefail

# --- Configuration -----------------------------------------------------------

UMH_ROOT="${UMH_ROOT:-/opt/OS}"
WINDOWS_IP="100.74.199.102"
WINDOWS_USER="antonys beast pc"
WINDOWS_DEV="C:\\Users\\antonys beast pc\\dev"
WINDOWS_GIT="C:\\Program Files\\Git\\cmd\\git.exe"
LOG_DIR="${UMH_ROOT}/logs"
LOG_FILE="${LOG_DIR}/sync_all.log"

# Repos to check on VPS (path, expected_branch)
VPS_REPOS=(
    "${UMH_ROOT}:main"
    "${UMH_ROOT}/data/repos/creatoros:main"
    "${UMH_ROOT}/data/repos/lyfeos:main"
    "${UMH_ROOT}/data/repos/entrepreneuros:main"
)

# Repos to check on Windows (directory_name, expected_branch)
WIN_REPOS=(
    "OS:main"
    "CreatorOS:main"
    "LyfeOS:main"
    "EntrepreneurOS:feature/company-system"
)

# --- Helpers -----------------------------------------------------------------

mkdir -p "$LOG_DIR"

MODE="dry-run"
if [[ "${1:-}" == "--pull" ]]; then
    MODE="pull"
elif [[ "${1:-}" == "--dry-run" || -z "${1:-}" ]]; then
    MODE="dry-run"
else
    echo "Usage: scripts/sync_all.sh [--dry-run | --pull]"
    exit 2
fi

DRIFT_COUNT=0
PULL_FAIL=0
TIMESTAMP=$(date -u '+%Y-%m-%d %H:%M:%S UTC')

log() {
    echo "$*"
    echo "[$TIMESTAMP] $*" >> "$LOG_FILE"
}

log_only() {
    echo "[$TIMESTAMP] $*" >> "$LOG_FILE"
}

# Check a single VPS repo. Returns 0 if in sync, 1 if drifted.
check_vps_repo() {
    local repo_path="$1"
    local expected_branch="$2"
    local label
    label=$(basename "$repo_path")
    [[ "$repo_path" == "$UMH_ROOT" ]] && label="OS"

    if [[ ! -d "$repo_path/.git" ]]; then
        log "  [$label] SKIP — not a git repo at $repo_path"
        return 0
    fi

    cd "$repo_path"

    local current_branch
    current_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "DETACHED")

    if [[ "$current_branch" != "$expected_branch" ]]; then
        log "  [$label] WARN — on branch '$current_branch', expected '$expected_branch'"
    fi

    git fetch origin --quiet 2>/dev/null || {
        log "  [$label] WARN — fetch failed (network?)"
        return 1
    }

    local local_sha remote_sha
    local_sha=$(git rev-parse HEAD 2>/dev/null)
    remote_sha=$(git rev-parse "origin/$expected_branch" 2>/dev/null || echo "UNKNOWN")

    if [[ "$remote_sha" == "UNKNOWN" ]]; then
        log "  [$label] WARN — origin/$expected_branch does not exist"
        return 1
    fi

    if [[ "$local_sha" == "$remote_sha" ]]; then
        log "  [$label] OK — ${local_sha:0:8} (in sync)"
        return 0
    fi

    local behind ahead
    behind=$(git rev-list --count HEAD.."origin/$expected_branch" 2>/dev/null || echo "?")
    ahead=$(git rev-list --count "origin/$expected_branch"..HEAD 2>/dev/null || echo "?")

    if [[ "$ahead" != "0" && "$ahead" != "?" ]]; then
        log "  [$label] DRIFT — $ahead ahead, $behind behind origin/$expected_branch"
        return 1
    fi

    if [[ "$behind" != "0" && "$behind" != "?" ]]; then
        if [[ "$MODE" == "pull" ]]; then
            local dirty
            dirty=$(git status --porcelain 2>/dev/null | head -1)
            if [[ -n "$dirty" ]]; then
                log "  [$label] BLOCKED — $behind behind but working tree dirty"
                return 1
            fi
            git merge --ff-only "origin/$expected_branch" --quiet 2>/dev/null && {
                log "  [$label] PULLED — fast-forwarded $behind commits"
                return 0
            } || {
                log "  [$label] FAIL — ff-only merge failed"
                return 1
            }
        else
            log "  [$label] BEHIND — $behind commits behind origin/$expected_branch"
            return 1
        fi
    fi

    log "  [$label] DRIFT — local ${local_sha:0:8} vs remote ${remote_sha:0:8}"
    return 1
}

# Check Windows repos via SSH. Requires Tailscale + SSH key auth.
check_windows_repos() {
    if ! ping -c 1 -W 3 "$WINDOWS_IP" > /dev/null 2>&1; then
        log "  [Windows] OFFLINE — $WINDOWS_IP unreachable"
        return 0
    fi

    for entry in "${WIN_REPOS[@]}"; do
        local dir_name="${entry%%:*}"
        local expected_branch="${entry##*:}"
        local repo_path="${WINDOWS_DEV}\\${dir_name}"

        local git_cmd="\"${WINDOWS_GIT}\""
        local cmd="${git_cmd} -C \"${repo_path}\" rev-parse --abbrev-ref HEAD 2>&1"

        local current_branch
        current_branch=$(ssh -o ConnectTimeout=5 -o BatchMode=yes \
            "${WINDOWS_USER}@${WINDOWS_IP}" "$cmd" 2>/dev/null) || {
            log "  [$dir_name] SKIP — SSH or git failed"
            continue
        }
        current_branch=$(echo "$current_branch" | tr -d '\r\n')

        if [[ "$current_branch" != "$expected_branch" ]]; then
            log "  [$dir_name] WARN — on '$current_branch', expected '$expected_branch'"
        fi

        local sha_cmd="${git_cmd} -C \"${repo_path}\" rev-parse HEAD 2>&1"
        local win_sha
        win_sha=$(ssh -o ConnectTimeout=5 -o BatchMode=yes \
            "${WINDOWS_USER}@${WINDOWS_IP}" "$sha_cmd" 2>/dev/null) || {
            log "  [$dir_name] SKIP — could not get HEAD SHA"
            continue
        }
        win_sha=$(echo "$win_sha" | tr -d '\r\n')

        local fetch_cmd="${git_cmd} -C \"${repo_path}\" fetch origin --quiet 2>&1"
        ssh -o ConnectTimeout=5 -o BatchMode=yes \
            "${WINDOWS_USER}@${WINDOWS_IP}" "$fetch_cmd" 2>/dev/null || true

        local remote_cmd="${git_cmd} -C \"${repo_path}\" rev-parse origin/${expected_branch} 2>&1"
        local win_remote
        win_remote=$(ssh -o ConnectTimeout=5 -o BatchMode=yes \
            "${WINDOWS_USER}@${WINDOWS_IP}" "$remote_cmd" 2>/dev/null) || {
            log "  [$dir_name] WARN — origin/$expected_branch not found on Windows"
            continue
        }
        win_remote=$(echo "$win_remote" | tr -d '\r\n')

        if [[ "$win_sha" == "$win_remote" ]]; then
            log "  [$dir_name] OK — ${win_sha:0:8} (in sync)"
        else
            local behind_cmd="${git_cmd} -C \"${repo_path}\" rev-list --count HEAD..origin/${expected_branch} 2>&1"
            local win_behind
            win_behind=$(ssh -o ConnectTimeout=5 -o BatchMode=yes \
                "${WINDOWS_USER}@${WINDOWS_IP}" "$behind_cmd" 2>/dev/null || echo "?")
            win_behind=$(echo "$win_behind" | tr -d '\r\n')

            if [[ "$MODE" == "pull" && "$win_behind" != "0" && "$win_behind" != "?" ]]; then
                local dirty_cmd="${git_cmd} -C \"${repo_path}\" status --porcelain 2>&1"
                local win_dirty
                win_dirty=$(ssh -o ConnectTimeout=5 -o BatchMode=yes \
                    "${WINDOWS_USER}@${WINDOWS_IP}" "$dirty_cmd" 2>/dev/null || echo "")
                win_dirty=$(echo "$win_dirty" | tr -d '\r\n')

                if [[ -n "$win_dirty" ]]; then
                    log "  [$dir_name] BLOCKED — $win_behind behind but dirty"
                    DRIFT_COUNT=$((DRIFT_COUNT + 1))
                    continue
                fi

                local pull_cmd="${git_cmd} -C \"${repo_path}\" merge --ff-only origin/${expected_branch} 2>&1"
                local pull_result
                pull_result=$(ssh -o ConnectTimeout=5 -o BatchMode=yes \
                    "${WINDOWS_USER}@${WINDOWS_IP}" "$pull_cmd" 2>/dev/null) && {
                    log "  [$dir_name] PULLED — fast-forwarded $win_behind commits"
                } || {
                    log "  [$dir_name] FAIL — ff-only merge failed on Windows"
                    PULL_FAIL=$((PULL_FAIL + 1))
                }
            else
                log "  [$dir_name] BEHIND — $win_behind commits behind"
                DRIFT_COUNT=$((DRIFT_COUNT + 1))
            fi
        fi
    done
}

# --- Main --------------------------------------------------------------------

log "=== sync_all.sh ($MODE) — $TIMESTAMP ==="
log ""
log "VPS repos:"

for entry in "${VPS_REPOS[@]}"; do
    repo_path="${entry%%:*}"
    expected_branch="${entry##*:}"
    check_vps_repo "$repo_path" "$expected_branch" || DRIFT_COUNT=$((DRIFT_COUNT + 1))
done

log ""
log "Windows repos:"
check_windows_repos

log ""

if [[ $PULL_FAIL -gt 0 ]]; then
    log "RESULT: $PULL_FAIL pull(s) failed. Manual intervention needed."
    exit 1
elif [[ $DRIFT_COUNT -gt 0 && "$MODE" == "dry-run" ]]; then
    log "RESULT: $DRIFT_COUNT repo(s) out of sync. Run with --pull to fast-forward."
    exit 1
else
    log "RESULT: All repos in sync."
    exit 0
fi
