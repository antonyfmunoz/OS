#!/bin/bash
# Phase C module migration helper
# Usage: ./scripts/migrate_module.sh <module_name> <target_layer> <target_subpath>
# Example: ./scripts/migrate_module.sh ai_identity control_plane identity

set -euo pipefail

MODULE="$1"
TARGET_LAYER="$2"
TARGET_SUB="$3"
REPO="/opt/OS"

SRC="${REPO}/runtime/${MODULE}.py"
DEST_DIR="${REPO}/${TARGET_LAYER}/${TARGET_SUB}"
DEST="${DEST_DIR}/${MODULE}.py"
OLD_IMPORT="runtime.${MODULE}"
NEW_IMPORT="${TARGET_LAYER}.${TARGET_SUB}.${MODULE}"

if [ ! -f "$SRC" ]; then
    echo "ERROR: Source file not found: $SRC"
    exit 1
fi

# Create target directory + __init__.py if needed
mkdir -p "$DEST_DIR"
for dir in "${REPO}/${TARGET_LAYER}" "$DEST_DIR"; do
    if [ ! -f "${dir}/__init__.py" ]; then
        touch "${dir}/__init__.py"
        git add "${dir}/__init__.py"
    fi
done

# Move the file
git mv "$SRC" "$DEST"

# Update context imports in the moved file to canonical
sed -i "s|from runtime\.context import|from state.context.context import|g" "$DEST"
sed -i "s|from runtime\.context |from state.context.context |g" "$DEST"

# Update all callers across the tree
grep -rln "from ${OLD_IMPORT} \|from ${OLD_IMPORT}$" \
    --include="*.py" \
    --exclude-dir=_archive --exclude-dir=__pycache__ --exclude-dir=archive \
    "$REPO" 2>/dev/null | while read -r file; do
    sed -i "s|from ${OLD_IMPORT} |from ${NEW_IMPORT} |g" "$file"
    sed -i "s|from ${OLD_IMPORT}$|from ${NEW_IMPORT}|g" "$file"
done

# Handle 'import runtime.module as ...' style
grep -rln "import ${OLD_IMPORT} \|import ${OLD_IMPORT}$" \
    --include="*.py" \
    --exclude-dir=_archive --exclude-dir=__pycache__ --exclude-dir=archive \
    "$REPO" 2>/dev/null | while read -r file; do
    sed -i "s|import ${OLD_IMPORT} |import ${NEW_IMPORT} |g" "$file"
    sed -i "s|import ${OLD_IMPORT}$|import ${NEW_IMPORT}|g" "$file"
done

# Count remaining references (should be 0)
REMAINING=$(grep -rn "from runtime\.${MODULE} \|from runtime\.${MODULE}$\|import runtime\.${MODULE} \|import runtime\.${MODULE}$" \
    --include="*.py" \
    --exclude-dir=_archive --exclude-dir=__pycache__ --exclude-dir=archive \
    "$REPO" 2>/dev/null | wc -l)

# Count context shim callers reduced in this file
CTX_REDUCED=$(git diff --cached -- "$DEST" 2>/dev/null | grep -c "^-.*from runtime\.context" || echo 0)

echo "MODULE: ${MODULE}"
echo "MOVED: runtime/${MODULE}.py -> ${TARGET_LAYER}/${TARGET_SUB}/${MODULE}.py"
echo "REMAINING_OLD_REFS: ${REMAINING}"
echo "CTX_SHIM_REDUCED: ${CTX_REDUCED}"

if [ "$REMAINING" -gt 0 ]; then
    echo "WARNING: ${REMAINING} references still using old import path!"
    grep -rn "from runtime\.${MODULE} \|from runtime\.${MODULE}$" \
        --include="*.py" \
        --exclude-dir=_archive --exclude-dir=__pycache__ --exclude-dir=archive \
        "$REPO" 2>/dev/null || true
fi
