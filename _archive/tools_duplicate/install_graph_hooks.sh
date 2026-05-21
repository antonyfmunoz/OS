#!/usr/bin/env bash
# install_graph_hooks.sh — wire pre-commit + post-merge hooks into .git/hooks.
#
# Safe to re-run. Existing hooks are backed up to <name>.bak-YYYYMMDDHHMMSS.

set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
SRC="$ROOT/scripts/graph_hooks"
DST="$ROOT/.git/hooks"
STAMP="$(date +%Y%m%d%H%M%S)"

for hook in pre-commit post-merge; do
  target="$DST/$hook"
  if [[ -f "$target" && ! -L "$target" ]]; then
    mv "$target" "$target.bak-$STAMP"
    echo "backed up existing $hook -> $target.bak-$STAMP"
  fi
  ln -sfn "$SRC/$hook" "$target"
  chmod +x "$SRC/$hook"
  echo "installed: $target -> $SRC/$hook"
done

echo "done. run 'git commit' or 'git pull' to exercise the hooks."
