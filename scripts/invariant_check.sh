#!/usr/bin/env bash
# Invariant checks for UMH substrate unification.
# Checks 10 invariants from the spec. Exit 1 on any failure.
set -e

PASS=0
FAIL=0
cd "$(dirname "$0")/.."

check() {
    local name="$1"
    local result="$2"
    if [ "$result" -eq 0 ]; then
        echo "  PASS: $name"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $name"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== UMH Substrate Invariant Check ==="
echo ""

# 1. Control plane exclusivity — no adapter call outside spine
count=$(grep -rn "call_with_fallback" substrate/ --include="*.py" 2>/dev/null | grep -v "execution/spine.py" | grep -v "test_" | grep -v "__pycache__" | wc -l)
check "1. Control plane exclusivity (no adapter call outside spine)" "$count"

# 2. Single execution spine — only spine.py calls adapters
count=$(grep -rn "adapter\.execute\|\.execute(.*AdapterRequest" substrate/ --include="*.py" 2>/dev/null | grep -v "spine.py" | grep -v "test_" | grep -v "__pycache__" | wc -l)
check "2. Single execution spine" "$count"

# 3. Governance before execution — classify before execute in router
has_gov=$(grep -c "governance.*classify\|classify.*governance" substrate/control_plane/router.py 2>/dev/null || echo 0)
[ "$has_gov" -gt 0 ] && r=0 || r=1
check "3. Governance before execution" "$r"

# 4. Trace everything — TraceRecord used in router and spine
trace_router=$(grep -c "TraceRecord\|trace" substrate/control_plane/router.py 2>/dev/null || echo 0)
trace_spine=$(grep -c "TraceRecord\|trace" substrate/execution/spine.py 2>/dev/null || echo 0)
[ "$trace_router" -gt 0 ] && [ "$trace_spine" -gt 0 ] && r=0 || r=1
check "4. Trace everything" "$r"

# 5. Memory discipline — no raw SQL in substrate/control_plane/
count=$(grep -rn "cur.execute\|psycopg2" substrate/control_plane/ --include="*.py" 2>/dev/null | grep -v "__pycache__" | wc -l)
check "5. Memory discipline (no raw SQL in control plane)" "$count"

# 6. Registry as truth — ComponentRegistry protocol exists
has_reg=$(grep -c "class ComponentRegistry" substrate/control_plane/registry.py 2>/dev/null || echo 0)
[ "$has_reg" -gt 0 ] && r=0 || r=1
check "6. Registry as truth" "$r"

# 7. Feedback closes loops — FeedbackCapture used in router/spine
fb_count=$(grep -rn "feedback\|FeedbackCapture" substrate/control_plane/router.py substrate/execution/spine.py --include="*.py" 2>/dev/null | wc -l)
[ "$fb_count" -gt 0 ] && r=0 || r=1
check "7. Feedback closes loops" "$r"

# 8. Public API boundary — Substrate class in __init__.py
has_substrate=$(grep -c "class Substrate" substrate/__init__.py 2>/dev/null || echo 0)
[ "$has_substrate" -gt 0 ] && r=0 || r=1
check "8. Public API boundary" "$r"

# 9. Zero dead code — delegate to dead_code_check.py
python3 scripts/dead_code_check.py > /dev/null 2>&1 && r=0 || r=1
check "9. Zero dead code" "$r"

# 10. Pydantic only — no raw dict types in substrate type definitions
count=$(grep -n "TypedDict\|namedtuple\|dataclass" substrate/types.py 2>/dev/null | grep -v "# " | wc -l)
check "10. Pydantic only (no TypedDict/namedtuple/dataclass in types)" "$count"

echo ""
echo "Results: $PASS passed, $FAIL failed"
if [ "$FAIL" -gt 0 ]; then
    exit 1
else
    echo "All invariants satisfied."
    exit 0
fi
