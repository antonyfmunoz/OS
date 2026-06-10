#!/bin/bash
set -euo pipefail

COCKPIT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$COCKPIT_DIR/.." && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

CRITICAL_FILES=(
  "cockpit/nginx.conf.template"
  "cockpit/Dockerfile"
  "cockpit/start.sh"
)

FORBIDDEN_FILES=(
  "cockpit/nginx.conf"
)

echo "=== Cockpit Pre-Deploy Gate ==="

errors=0

for f in "${FORBIDDEN_FILES[@]}"; do
  if [ -f "$REPO_ROOT/$f" ]; then
    echo -e "${RED}BLOCKED: $f exists — stale file from before auth migration.${NC}"
    echo "  This file was replaced by nginx.conf.template (commit 1680083f)."
    echo "  Remove it: rm $REPO_ROOT/$f"
    errors=$((errors + 1))
  fi
done

for f in "${CRITICAL_FILES[@]}"; do
  if [ ! -f "$REPO_ROOT/$f" ]; then
    echo -e "${RED}BLOCKED: $f is missing.${NC}"
    errors=$((errors + 1))
    continue
  fi

  main_hash=$(git -C "$REPO_ROOT" show main:"$f" 2>/dev/null | sha256sum | cut -d' ' -f1)
  local_hash=$(sha256sum "$REPO_ROOT/$f" | cut -d' ' -f1)

  if [ "$main_hash" != "$local_hash" ]; then
    echo -e "${RED}BLOCKED: $f differs from main branch.${NC}"
    echo "  These files control auth, proxy, and container startup."
    echo "  Sync from main: git checkout main -- $f"
    errors=$((errors + 1))
  else
    echo -e "${GREEN}OK: $f matches main${NC}"
  fi
done

if ! grep -q "nginx.conf.template" "$COCKPIT_DIR/Dockerfile"; then
  echo -e "${RED}BLOCKED: Dockerfile does not reference nginx.conf.template${NC}"
  errors=$((errors + 1))
else
  echo -e "${GREEN}OK: Dockerfile references nginx.conf.template${NC}"
fi

if grep -q "UMH_WS_TOKEN\|UMH_OPERATOR_API_KEY" "$COCKPIT_DIR/nginx.conf.template"; then
  echo -e "${RED}BLOCKED: nginx.conf.template still injects secrets — use Clerk JWT auth${NC}"
  errors=$((errors + 1))
else
  echo -e "${GREEN}OK: nginx.conf.template has no injected secrets${NC}"
fi

if grep -q "X-API-Key" "$COCKPIT_DIR/nginx.conf.template"; then
  echo -e "${RED}BLOCKED: nginx.conf.template still injects X-API-Key — security hole${NC}"
  errors=$((errors + 1))
else
  echo -e "${GREEN}OK: nginx.conf.template does not inject X-API-Key (Clerk JWT auth)${NC}"
fi

if [ ! -f "$REPO_ROOT/transports/api/cockpit_auth.py" ]; then
  echo -e "${RED}BLOCKED: transports/api/cockpit_auth.py missing — no server-side auth${NC}"
  errors=$((errors + 1))
else
  echo -e "${GREEN}OK: cockpit_auth.py exists${NC}"
fi

if [ $errors -gt 0 ]; then
  echo ""
  echo -e "${RED}=== DEPLOY BLOCKED: $errors issue(s) found ===${NC}"
  echo "Fix the issues above, then re-run."
  exit 1
fi

echo ""
echo -e "${GREEN}=== All checks passed — deploying ===${NC}"
echo ""

cd "$COCKPIT_DIR"

FLYCTL=$(command -v flyctl 2>/dev/null || echo "/root/.fly/bin/flyctl")
exec "$FLYCTL" deploy --remote-only "$@"
