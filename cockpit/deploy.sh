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

# ── Auto-refresh Fly.io deploy token from 1Password ──
# The fly-agent caches stale tokens and causes auth failures.
# Kill it and create a fresh deploy token every deploy.
if command -v op >/dev/null 2>&1; then
  pkill -9 -f "flyctl agent" 2>/dev/null || true
  rm -f "$HOME/.fly/fly-agent.sock" 2>/dev/null || true

  ORG_TOKEN=$(op read "op://${UMH_OP_VAULT:-UMH-Production}/Fly.io Org Token/credential" 2>/dev/null || true)
  if [ -n "$ORG_TOKEN" ]; then
    DEPLOY_TOKEN=$(FLY_API_TOKEN="$ORG_TOKEN" FLY_NO_UPDATE_CHECK=1 "$FLYCTL" tokens create deploy -a umh-cockpit 2>/dev/null || true)
    if [ -n "$DEPLOY_TOKEN" ]; then
      export FLY_API_TOKEN="$DEPLOY_TOKEN"
      echo -e "${GREEN}OK: Deploy token refreshed from 1Password${NC}"
    else
      echo -e "${RED}WARN: Could not create deploy token — using existing auth${NC}"
    fi
  else
    echo -e "${RED}WARN: 1Password unavailable — using existing auth${NC}"
  fi
fi

# ── Inject tenant build args (code/instance separation) ──
# fly.toml carries only placeholders; the display name + tenant Clerk key are
# resolved here from env / 1Password so no tenant identity is baked into source.
VITE_AI_NAME_VALUE="${VITE_AI_NAME:-}"
if [ -z "$VITE_AI_NAME_VALUE" ]; then
  VITE_AI_NAME_VALUE=$(UMH_ROOT="$REPO_ROOT" python3 -c "import sys; sys.path.insert(0,'$REPO_ROOT'); from substrate.state.business.business_instance import get_ai_name; print(get_ai_name() or '')" 2>/dev/null || true)
fi
VITE_CLERK_PK_VALUE="${VITE_CLERK_PUBLISHABLE_KEY:-}"
if [ -z "$VITE_CLERK_PK_VALUE" ] && command -v op >/dev/null 2>&1; then
  VITE_CLERK_PK_VALUE=$(op read "op://${UMH_OP_VAULT:-UMH-Production}/Clerk/publishable_key" 2>/dev/null || true)
fi

BUILD_ARGS=()
[ -n "$VITE_AI_NAME_VALUE" ] && BUILD_ARGS+=(--build-arg "VITE_AI_NAME=$VITE_AI_NAME_VALUE")
[ -n "$VITE_CLERK_PK_VALUE" ] && BUILD_ARGS+=(--build-arg "VITE_CLERK_PUBLISHABLE_KEY=$VITE_CLERK_PK_VALUE")

FLY_NO_UPDATE_CHECK=1 "$FLYCTL" deploy --remote-only "${BUILD_ARGS[@]}" "$@"
DEPLOY_EXIT=$?

if [ $DEPLOY_EXIT -ne 0 ]; then
  echo -e "${RED}=== Deploy failed (exit $DEPLOY_EXIT) ===${NC}"
  exit $DEPLOY_EXIT
fi

echo ""
echo "=== Post-Deploy Verification ==="
COCKPIT_URL="${COCKPIT_PUBLIC_URL:-https://universalmetaharness.tech}"
python3 "$REPO_ROOT/scripts/verify_deploy.py" \
  "umh-cockpit" \
  "$COCKPIT_URL" \
  --health-path "/healthz" \
  --health-timeout 60 || {
  echo -e "${RED}=== Post-deploy verification FAILED ===${NC}"
  echo "The deploy succeeded but verification detected issues."
  echo "Check the output above for details."
  exit 1
}

echo -e "${GREEN}=== Deploy + verification complete ===${NC}"
