#!/usr/bin/env bash
# Canonical sovereignty grep for UMH codebase.
#
# Searches for external-name attribution that should have been renamed
# during Layer 3.1 sovereignty cleanup. Exclusions are documented at:
#   10_Wiki/SOVEREIGNTY_GREP_EXCLUSIONS.md
#
# Usage:
#   scripts/sovereignty-grep.sh          # full audit
#   scripts/sovereignty-grep.sh --count  # hit count only

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

PATTERN='buyback.rate|drip.matrix|perfect.week|martell|camcorder.method|time.assassin|131.rule|hormozi|Dan Martell|Buy ?Back|DRIP Matrix|Perfect Week|Camcorder Method|Time Assassin'

EXCLUDES=(
  # Tooling / infrastructure
  --glob '!.git/'
  --glob '!node_modules/'
  --glob '!.claude/worktrees/'
  --glob '!__pycache__/'
  --glob '!*.pyc'

  # Session records / retrospective (meta-references to cleanup itself)
  --glob '!handoffs/'
  --glob '!10_Wiki/LAYER_3.1*'

  # Conversation transcripts (external names discussed, not claimed)
  --glob '!vault/memory/conversations/'

  # Historical archives (frozen pre-sovereignty snapshots, all DATA)
  --glob '!_archive/'

  # Frozen historical snapshots (migration round checkpoints)
  --glob '!data/migration/'

  # Ingestion pipeline artifacts (external names in ingested content)
  --glob '!data/runtime/'

  # Runtime trace store (content signal labels)
  --glob '!data/umh/traces/'

  # Auto-generated indices (regenerate, don't strip)
  --glob '!data/merged_graph.json'
  --glob '!data/codebase_graph_merged.json'
  --glob '!data/node_summaries.json'
  --glob '!data/semantic_space/'
)

if command -v rg &>/dev/null; then
  CMD=(rg -n -E "$PATTERN" "${EXCLUDES[@]}" "$ROOT")
else
  # Fallback to grep with equivalent exclusions
  CMD=(grep -rnE "$PATTERN"
    --include='*.py' --include='*.md' --include='*.json'
    --include='*.txt' --include='*.yaml' --include='*.yml'
    --exclude-dir=.git --exclude-dir=node_modules
    --exclude-dir=__pycache__
    "$ROOT")
fi

if [[ "${1:-}" == "--count" ]]; then
  "${CMD[@]}" 2>/dev/null | wc -l
else
  "${CMD[@]}" 2>/dev/null || true
fi
