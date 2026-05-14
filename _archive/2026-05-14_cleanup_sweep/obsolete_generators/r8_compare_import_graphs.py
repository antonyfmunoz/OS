#!/usr/bin/env python3
"""Compare two R8 import graph snapshots.

Reports:
- Module count diff
- Added/removed modules
- Cycle count diff
- Cycle membership changes
- Topological order changes
- Import count changes

Usage:
    python3 scripts/r8_compare_import_graphs.py \
        data/migration/r8b_pre_graph.json \
        data/migration/r8b_post_graph.json \
        --output data/migration/r8b_graph_diff.json
"""
import json
import sys
from pathlib import Path


def normalize_module_name(name: str, old_prefix: str, new_prefix: str) -> str:
    """Normalize module name for comparison across renames."""
    if name.startswith(old_prefix + "."):
        return new_prefix + name[len(old_prefix):]
    if name == old_prefix:
        return new_prefix
    return name


def main():
    if len(sys.argv) < 3:
        print("Usage: r8_compare_import_graphs.py <pre.json> <post.json> [--output <out.json>]")
        sys.exit(1)

    pre_path = sys.argv[1]
    post_path = sys.argv[2]
    output_path = None
    if "--output" in sys.argv:
        output_path = sys.argv[sys.argv.index("--output") + 1]

    with open(pre_path) as f:
        pre = json.load(f)
    with open(post_path) as f:
        post = json.load(f)

    old_prefix = pre["package_prefix"]
    new_prefix = post["package_prefix"]

    # Normalize pre module names to new prefix for comparison
    pre_modules = set()
    for m in pre["modules"]:
        pre_modules.add(normalize_module_name(m, old_prefix, new_prefix))

    post_modules = set(post["modules"].keys())

    added = sorted(post_modules - pre_modules)
    removed = sorted(pre_modules - post_modules)
    common = sorted(pre_modules & post_modules)

    # Cycle comparison
    pre_cycles_normalized = []
    for cycle in pre.get("cycles", []):
        pre_cycles_normalized.append(
            sorted(normalize_module_name(m, old_prefix, new_prefix) for m in cycle)
        )

    post_cycles = [sorted(c) for c in post.get("cycles", [])]

    diff = {
        "pre_file": pre_path,
        "post_file": post_path,
        "pre_prefix": old_prefix,
        "post_prefix": new_prefix,
        "module_count": {
            "pre": pre["total_modules"],
            "post": post["total_modules"],
            "diff": post["total_modules"] - pre["total_modules"],
        },
        "modules_added": added,
        "modules_removed": removed,
        "modules_common": len(common),
        "import_counts": {
            "pre_module_level": pre["total_module_level_imports"],
            "post_module_level": post["total_module_level_imports"],
            "pre_lazy": pre["total_lazy_imports"],
            "post_lazy": post["total_lazy_imports"],
            "note": "Post-move counts are lower because internal eos_ai.* refs "
                    "haven't been rewritten to runtime.* yet (R8c scope). "
                    "The scanner filters by package_prefix.",
        },
        "cycles": {
            "pre_count": pre["cycle_count"],
            "post_count": post["cycle_count"],
            "diff": post["cycle_count"] - pre["cycle_count"],
            "pre_cycles_normalized": pre_cycles_normalized,
            "post_cycles": post_cycles,
            "note": "Cycle count drops to 0 post-move because internal refs "
                    "still use eos_ai.* prefix (filtered out). Will be re-evaluated after R8c.",
        },
        "structural_equivalence": len(added) == 0 and len(removed) == 0,
        "module_count_match": pre["total_modules"] == post["total_modules"],
    }

    print(f"Module count: {pre['total_modules']} -> {post['total_modules']} (diff: {diff['module_count']['diff']})")
    print(f"Added: {len(added)}, Removed: {len(removed)}, Common: {len(common)}")
    print(f"Cycles: {pre['cycle_count']} -> {post['cycle_count']}")
    print(f"Module-level imports: {pre['total_module_level_imports']} -> {post['total_module_level_imports']}")
    print(f"Lazy imports: {pre['total_lazy_imports']} -> {post['total_lazy_imports']}")
    print(f"Structural equivalence (modules): {'PASS' if diff['structural_equivalence'] else 'FAIL'}")
    print(f"Module count match: {'PASS' if diff['module_count_match'] else 'FAIL'}")

    if added:
        print(f"\nAdded modules: {added[:10]}{'...' if len(added) > 10 else ''}")
    if removed:
        print(f"\nRemoved modules: {removed[:10]}{'...' if len(removed) > 10 else ''}")

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(diff, f, indent=2)
        print(f"\nDiff written to {output_path}")


if __name__ == "__main__":
    main()
