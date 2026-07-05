#!/usr/bin/env python3
"""Pre-commit gate: enforce the ontology-home map (WP-P3 ontology consolidation).

Complements check_ontology_layers.py. That gate keeps L3 CONTENTS out of the L2
SURFACE. This gate keeps the set of ontology/reality/domain/world-model HOMES
unambiguous — it prevents new, unclassified ontology homes and competing
domain-model/ontology registries from appearing silently.

UMH ontology-home map (see docs/audits/UMH_P3_ONTOLOGY_HOME_CONSOLIDATION.md and
.claude/rules/ontology-layers.md):
  L1  external/current reality      → substrate/reality_model/
  L1  reality reflection (read)     → substrate/organism/reality_graph.py
  L2  metamodel laws/primitives     → substrate/ontology/, substrate/types.py
  L2r primitive-decomposition/reason→ substrate/understanding/ontology/  (distinct concern)
  L4  semantic grounding / bridges  → substrate/understanding/domains/
  L4  governed reality write path   → substrate/reality_model/canonical_reality_write.py
  organism self-model               → substrate/organism/world_model.py    (distinct concern)
  understanding world model         → substrate/understanding/world_model/  (distinct concern)
  execution-policy domain registry  → substrate/organism/domain_registry.py (NOT an ontology registry)

This gate enforces two invariants:

1. HOME SET IS FROZEN (shrink-only). The Python modules that define ontology/
   reality/domain/world-model homes are enumerated in FROZEN_ONTOLOGY_HOMES. A
   NEW .py file under the guarded home directories that is not in the ledger is
   blocked — add it deliberately (with a layer classification) rather than
   letting a new ambiguous home appear. The ledger may only SHRINK or grow by
   an explicit, reviewed edit; the non-growth test freezes today's set.

2. NO NEW COMPETING ONTOLOGY/DOMAIN-MODEL REGISTRY. A new class matching an
   ontology/domain-MODEL registry pattern (OntologyRegistry, DomainModelRegistry,
   MetamodelRegistry, or a second DomainRegistry) outside the one canonical
   home (substrate/organism/domain_registry.py) is blocked. Ordinary registries
   (TemplateRegistry, DeviceRegistry, DecisionRegistry, ...) are NOT flagged.

Exit codes:
  0 — clean
  1 — a new unclassified home or competing ontology/domain-model registry

Usage:
  python3 scripts/check_ontology_homes.py           # staged files
  python3 scripts/check_ontology_homes.py --all      # scan the guarded homes
  python3 scripts/check_ontology_homes.py --file X    # one file

UMH substrate subsystem. Domain-agnostic.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent

# ── Directories whose ontology-home membership is frozen ──────────────────────
# A new .py under any of these must be added to FROZEN_ONTOLOGY_HOMES deliberately.
_GUARDED_HOME_DIRS = (
    "substrate/ontology/",
    "substrate/reality_model/",
    "substrate/understanding/ontology/",
    "substrate/understanding/world_model/",
    "substrate/understanding/domains/",
)

# ── Frozen ontology-home set (shrink-only) ────────────────────────────────────
# Every .py that legitimately defines an ontology/reality/domain/world-model home
# today, classified by layer. Frozen at WP-P3 ontology consolidation (main
# 85cf1206e). A new home must be added here on purpose. The non-growth test in
# tests/test_ontology_home_map.py holds this set to today's membership.
FROZEN_ONTOLOGY_HOMES: dict[str, str] = {
    # L1 — external/current reality model
    "substrate/reality_model/__init__.py": "L1",
    "substrate/reality_model/canonical.py": "L1",
    "substrate/reality_model/instance.py": "L1",
    "substrate/reality_model/reality_intelligence.py": "L1",
    "substrate/reality_model/reality_mutation.py": "L1",
    "substrate/reality_model/reality_query.py": "L1",
    "substrate/reality_model/simulation.py": "L1",
    "substrate/reality_model/canonical_reality_write.py": "L4-write",
    # L2 — metamodel laws / primitives / relationships
    "substrate/ontology/__init__.py": "L2",
    "substrate/ontology/laws.py": "L2",
    "substrate/ontology/primitives.py": "L2",
    "substrate/ontology/relationships.py": "L2",
    # substrate/ontology/domains/ — compat re-export shim of the L4 home
    "substrate/ontology/domains/__init__.py": "L4-shim",
    "substrate/ontology/domains/contract.py": "L4-shim",
    "substrate/ontology/domains/creator.py": "L4-shim",
    "substrate/ontology/domains/life.py": "L4-shim",
    # understanding/ontology/ — mixed; classified per-file (see FROZEN_ONTOLOGY_COMPETITORS)
    "substrate/understanding/ontology/__init__.py": "package-marker",
    # primitives.py RELOCATED (WP-P3 primitives relocation) → substrate/state/
    # business/primitives.py. It was L3 business-rule logic in an ontology dir;
    # evicted to its L3 state home. No longer a frozen home here (26).
    # primitive_decomposition_v1.py is a parallel L2 metamodel (frozen competitor)
    "substrate/understanding/ontology/primitive_decomposition_v1.py": "L2-parallel-frozen",
    # understanding world model (distinct concern from organism self-model)
    "substrate/understanding/world_model/__init__.py": "understanding-world-model",
    "substrate/understanding/world_model/world_model.py": "understanding-world-model",
    # L4 — semantic grounding / domain bridges / entity resolution
    "substrate/understanding/domains/__init__.py": "L4",
    "substrate/understanding/domains/contract.py": "L4",
    "substrate/understanding/domains/registry.py": "L4",
    "substrate/understanding/domains/business.py": "L4",
    "substrate/understanding/domains/creator.py": "L4",
    "substrate/understanding/domains/life.py": "L4",
}

# ── Shrink-only frozen ontology-home competitors / leaks ──────────────────────
# Known ontology-home ambiguities frozen at WP-P3 ontology consolidation. This
# packet does NOT resolve them (no domain-object relocation; directional calls
# deferred to a later, owner-ruled packet). Each carries owner + rationale +
# sunset. The non-growth test holds this set — it may only SHRINK. Adding a new
# entry here to hide a fresh leak is forbidden; new leaks must be fixed, not
# frozen.
# Format: relative path → (disposition, sunset/follow-on).
FROZEN_ONTOLOGY_COMPETITORS: dict[str, tuple[str, str]] = {
    # RESOLVED (WP-P3 primitives relocation): understanding/ontology/primitives.py
    # was L3 business-rule logic (KnowledgePrimitive / stage-aware reasoning) in an
    # ontology/ dir importing substrate.state.context. Resolution was RELOCATION,
    # not disambiguation: git-moved whole to substrate/state/business/primitives.py
    # (co-located with its BusinessInstanceManager dependency), the 6 lazy imports
    # (5 consumers) + the new-primitive skill re-pointed, no shim. Removed from this
    # ledger, shrinking it 2 → 1. The move is downward-legal (substrate→substrate).
    # Parallel L2 metamodel: redefines PrimitiveType/RelationshipType/
    # PrimitiveObservation instead of importing substrate.types. Owner: developer.
    # Rationale: 11 importers (the understanding→domains→adapter perception
    # pipeline) vs substrate.ontology's 3; collapsing onto substrate.types is a
    # type-system dedup requiring its own regression pass. Sunset: P3 metamodel
    # dedup packet → re-point to substrate.types.
    "substrate/understanding/ontology/primitive_decomposition_v1.py": (
        "parallel-L2-metamodel",
        "P3 metamodel dedup packet",
    ),
    # RESOLVED (WP-P3 world-model sunset): substrate/understanding/world_model/
    # world_model.py was the third frozen competitor (name-collision with
    # organism/world_model.py). It is not a competitor — it is a distinct concern
    # (domain-knowledge world model vs organism self-model). Resolution was
    # disambiguation, not relocation: both modules now carry reciprocal docstrings
    # stating they are distinct concerns, and it remains a classified home in
    # FROZEN_ONTOLOGY_HOMES ("understanding-world-model"). Removed from this ledger,
    # shrinking it 3 → 2. Deprecation was rejected: context_builder is a live
    # consumer (WorldModel(org_id=...).get_context_for_prompt(...)).
}

# ── Competing ontology/domain-MODEL registry patterns ─────────────────────────
# Narrow on purpose: only ontology / domain-MODEL / metamodel registries, plus a
# SECOND DomainRegistry. Ordinary registries (Template/Device/Session/Decision/
# Executor/Profile/Projection/Knowledge...) are intentionally NOT matched.
_COMPETING_REGISTRY_RE = re.compile(
    r"^class\s+(\w*Ontology\w*Registry|DomainModelRegistry|MetamodelRegistry|DomainRegistry)\b"
)
# The one canonical execution-policy domain registry home.
_CANONICAL_DOMAIN_REGISTRY = "substrate/organism/domain_registry.py"
# Where a competing ontology/domain-model registry would most plausibly sneak in.
_REGISTRY_SCAN_DIRS = ("substrate/organism/", "substrate/ontology/", "substrate/understanding/")


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(_REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _under_guarded_home_dir(rel: str) -> bool:
    return any(rel.startswith(d) for d in _GUARDED_HOME_DIRS)


def _in_registry_scan(rel: str) -> bool:
    return any(rel.startswith(d) for d in _REGISTRY_SCAN_DIRS)


def _check_file(path: Path) -> list[str]:
    rel = _rel(path)
    if path.suffix != ".py":
        return []
    if "__pycache__" in rel:
        return []
    violations: list[str] = []

    # Invariant 1: no new unclassified ontology home.
    if _under_guarded_home_dir(rel) and rel not in FROZEN_ONTOLOGY_HOMES:
        violations.append(
            f"{rel}: new ontology-home module not in FROZEN_ONTOLOGY_HOMES. "
            f"Classify it by layer (L1/L2/L4/...) and add it to the ledger in "
            f"scripts/check_ontology_homes.py deliberately, or place it outside "
            f"the guarded ontology homes."
        )

    # Invariant 2: no new competing ontology/domain-model registry.
    if _in_registry_scan(rel) and rel != _CANONICAL_DOMAIN_REGISTRY:
        try:
            for i, line in enumerate(
                path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1
            ):
                if _COMPETING_REGISTRY_RE.match(line):
                    cls = _COMPETING_REGISTRY_RE.match(line).group(1)
                    violations.append(
                        f"{rel}:{i}: competing ontology/domain-model registry '{cls}'. "
                        f"The one execution-policy domain registry is "
                        f"{_CANONICAL_DOMAIN_REGISTRY}; ontology/domain-model registration "
                        f"must not fork. Reconcile as adapter/bridge or extend the canonical home."
                    )
        except OSError:
            pass

    return violations


def _staged_files() -> list[Path]:
    try:
        out = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
            capture_output=True,
            text=True,
            cwd=str(_REPO_ROOT),
        )
    except OSError:
        return []
    files = []
    for line in out.stdout.splitlines():
        line = line.strip()
        if line.endswith(".py"):
            p = _REPO_ROOT / line
            if p.exists():
                files.append(p)
    return files


def _all_files() -> list[Path]:
    files: list[Path] = []
    for d in set(_GUARDED_HOME_DIRS + _REGISTRY_SCAN_DIRS):
        base = _REPO_ROOT / d
        if base.is_dir():
            files.extend(base.rglob("*.py"))
    return files


def main() -> int:
    args = sys.argv[1:]
    if "--all" in args:
        targets = _all_files()
    elif "--file" in args:
        idx = args.index("--file")
        targets = [Path(args[idx + 1])]
    else:
        targets = _staged_files()

    violations: list[str] = []
    for p in targets:
        violations.extend(_check_file(p))

    print("Ontology-home map gate")
    print("=" * 50)
    if violations:
        print(f"\n✗ {len(violations)} ontology-home violation(s):\n")
        for v in violations:
            print(f"  - {v}")
        print("\nSee docs/audits/UMH_P3_ONTOLOGY_HOME_CONSOLIDATION.md")
        return 1
    if "--all" in args:
        print(
            f"\n✓ PASS — {len(FROZEN_ONTOLOGY_HOMES)} frozen homes; no new ambiguous home or competing registry"
        )
    else:
        print("\n✓ PASS — ontology homes unambiguous")
    return 0


if __name__ == "__main__":
    sys.exit(main())
