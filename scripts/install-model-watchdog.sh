#!/usr/bin/env bash
set -euo pipefail

MODE="${1:---dry-run}"
ARG="${2:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${UMH_REPO_ROOT:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
SOURCE="${REPO_ROOT}/services/model_watchdog.py"
CPU_GATE_SOURCE="${REPO_ROOT}/substrate/execution/cpu_gate.py"
UNIT_SOURCE="${REPO_ROOT}/infra/systemd/umh-model-watchdog.service"
RUNTIME_ROOT="${UMH_MODEL_WATCHDOG_RUNTIME_ROOT:-/opt/umh/runtime/model-watchdog}"
RELEASES="${RUNTIME_ROOT}/releases"
CURRENT="${RUNTIME_ROOT}/current"
UNIT_DEST="${UMH_MODEL_WATCHDOG_UNIT_DEST:-/etc/systemd/system/umh-model-watchdog.service}"
SYSTEMCTL="${UMH_MODEL_WATCHDOG_SYSTEMCTL:-systemctl}"

sha256_file() {
  sha256sum "$1" | awk '{print $1}'
}

install_unit() {
  sed "s#/opt/umh/runtime/model-watchdog#${RUNTIME_ROOT}#g" "$UNIT_SOURCE" > "$UNIT_DEST"
  chmod 0644 "$UNIT_DEST"
}

git_sha() {
  git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo "unknown"
}

deployment_id() {
  if [[ -n "${UMH_MODEL_WATCHDOG_DEPLOYMENT_ID:-}" ]]; then
    printf '%s\n' "$UMH_MODEL_WATCHDOG_DEPLOYMENT_ID"
    return
  fi
  local src_sha
  src_sha="$(sha256_file "$SOURCE")"
  printf '%s-%s\n' "$(git_sha)" "${src_sha:0:16}"
}

render_manifest() {
  local release_dir="$1"
  local deploy_id="$2"
  local source_sha unit_sha
  source_sha="$(sha256_file "$SOURCE")"
  unit_sha="$(sha256_file "$UNIT_SOURCE")"
  cat >"${release_dir}/MANIFEST.json" <<EOF
{
  "deployment_id": "${deploy_id}",
  "source_commit": "$(git_sha)",
  "source_path": "${SOURCE}",
  "source_sha256": "${source_sha}",
  "cpu_gate_sha256": "$(sha256_file "$CPU_GATE_SOURCE")",
  "runtime_path": "${release_dir}/model_watchdog.py",
  "unit_source": "${UNIT_SOURCE}",
  "unit_sha256": "${unit_sha}",
  "installed_at_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
}

verify_release() {
  local release_dir="$1"
  test -f "${release_dir}/model_watchdog.py"
  test -f "${release_dir}/substrate/execution/cpu_gate.py"
  test -f "${release_dir}/MANIFEST.json"
  expected_sha="$(
    /usr/bin/python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8")).get("source_sha256", ""))' \
      "${release_dir}/MANIFEST.json"
  )"
  test -n "$expected_sha"
  test "$expected_sha" = "$(sha256_file "${release_dir}/model_watchdog.py")"
  /usr/bin/python3 -m py_compile "${release_dir}/model_watchdog.py"
  /usr/bin/python3 -m py_compile "${release_dir}/substrate/execution/cpu_gate.py"
}

case "$MODE" in
  --dry-run)
    deploy_id="$(deployment_id)"
    echo "source=${SOURCE}"
    echo "source_sha256=$(sha256_file "$SOURCE")"
    echo "unit_source=${UNIT_SOURCE}"
    echo "unit_sha256=$(sha256_file "$UNIT_SOURCE")"
    echo "release=${RELEASES}/${deploy_id}"
    echo "current=${CURRENT}"
    echo "unit_dest=${UNIT_DEST}"
    echo "execstart=/usr/bin/python3 ${CURRENT}/model_watchdog.py"
    ;;
  --install)
    deploy_id="$(deployment_id)"
    release_dir="${RELEASES}/${deploy_id}"
    install -d -m 0755 "$release_dir"
    install -d -m 0755 "${release_dir}/substrate/execution"
    install -m 0755 "$SOURCE" "${release_dir}/model_watchdog.py"
    install -m 0644 "$CPU_GATE_SOURCE" "${release_dir}/substrate/execution/cpu_gate.py"
    touch "${release_dir}/substrate/__init__.py" "${release_dir}/substrate/execution/__init__.py"
    render_manifest "$release_dir" "$deploy_id"
    verify_release "$release_dir"
    ln -sfn "$release_dir" "${CURRENT}.new"
    mv -Tf "${CURRENT}.new" "$CURRENT"
    install_unit
    "$SYSTEMCTL" daemon-reload
    "$SYSTEMCTL" restart umh-model-watchdog.service
    "$SYSTEMCTL" is-active --quiet umh-model-watchdog.service
    echo "installed=${deploy_id}"
    echo "runtime=${release_dir}/model_watchdog.py"
    echo "runtime_sha256=$(sha256_file "${release_dir}/model_watchdog.py")"
    ;;
  --verify)
    test -L "$CURRENT"
    release_dir="$(readlink -f "$CURRENT")"
    verify_release "$release_dir"
    "$SYSTEMCTL" is-active --quiet umh-model-watchdog.service
    if [[ -f "$UNIT_DEST" ]]; then
      grep -F "${CURRENT}/model_watchdog.py" "$UNIT_DEST" >/dev/null
    fi
    echo "verified=$(basename "$release_dir")"
    echo "runtime_sha256=$(sha256_file "${release_dir}/model_watchdog.py")"
    ;;
  --rollback)
    if [[ -z "$ARG" ]]; then
      echo "usage: $0 --rollback <release-id>" >&2
      exit 2
    fi
    release_dir="${RELEASES}/${ARG}"
    verify_release "$release_dir"
    ln -sfn "$release_dir" "${CURRENT}.new"
    mv -Tf "${CURRENT}.new" "$CURRENT"
    "$SYSTEMCTL" restart umh-model-watchdog.service
    "$SYSTEMCTL" is-active --quiet umh-model-watchdog.service
    echo "rolled_back=${ARG}"
    ;;
  *)
    echo "usage: $0 [--dry-run|--install|--verify|--rollback <release-id>]" >&2
    exit 2
    ;;
esac
