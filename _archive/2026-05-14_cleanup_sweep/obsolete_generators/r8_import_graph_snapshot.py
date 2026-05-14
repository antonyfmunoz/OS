#!/usr/bin/env python3
"""Capture import graph snapshot for R8 migration verification.

Walks a Python package directory and records:
- Every importable module
- Direct imports (module-level `from X import Y` / `import X`)
- Lazy imports (inside function/method bodies)
- Cycle membership
- Topological sort order
- Module file sizes (as change-detection proxy)

Usage:
    python3 scripts/r8_import_graph_snapshot.py --root eos_ai --output data/migration/r8_pre_graph.json
"""
import ast
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

def find_modules(root_dir: str) -> list[str]:
    """Find all .py modules under root_dir, return as dotted paths."""
    base = Path(root_dir)
    modules = []
    for py_file in sorted(base.rglob("*.py")):
        if "__pycache__" in str(py_file):
            continue
        rel = py_file.relative_to(base.parent)
        parts = list(rel.parts)
        if parts[-1] == "__init__.py":
            parts = parts[:-1]
        else:
            parts[-1] = parts[-1].removesuffix(".py")
        if parts:
            modules.append(".".join(parts))
    return modules


def extract_imports(filepath: str, package_prefix: str) -> dict:
    """Extract module-level and lazy imports from a Python file."""
    try:
        source = Path(filepath).read_text(errors="replace")
        tree = ast.parse(source, filename=filepath)
    except (SyntaxError, UnicodeDecodeError):
        return {"module_level": [], "lazy": [], "parse_error": True}

    module_level = []
    lazy = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.ImportFrom) and node.module:
                target = node.module
            elif isinstance(node, ast.Import):
                target = node.names[0].name if node.names else ""
            else:
                continue

            if not target.startswith(package_prefix) and not target.startswith("core"):
                continue

            in_function = False
            for parent in ast.walk(tree):
                if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for child in ast.walk(parent):
                        if child is node:
                            in_function = True
                            break
                    if in_function:
                        break

            entry = {"target": target, "line": node.lineno}
            if in_function:
                lazy.append(entry)
            else:
                module_level.append(entry)

    return {"module_level": module_level, "lazy": lazy, "parse_error": False}


def detect_cycles(graph: dict[str, list[str]]) -> list[list[str]]:
    """Find all strongly connected components (cycles) using Tarjan's."""
    index_counter = [0]
    stack = []
    lowlink = {}
    index = {}
    on_stack = {}
    result = []

    def strongconnect(v):
        index[v] = index_counter[0]
        lowlink[v] = index_counter[0]
        index_counter[0] += 1
        stack.append(v)
        on_stack[v] = True

        for w in graph.get(v, []):
            if w not in index:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif on_stack.get(w, False):
                lowlink[v] = min(lowlink[v], index[w])

        if lowlink[v] == index[v]:
            component = []
            while True:
                w = stack.pop()
                on_stack[w] = False
                component.append(w)
                if w == v:
                    break
            if len(component) > 1:
                result.append(sorted(component))

    for v in sorted(graph.keys()):
        if v not in index:
            strongconnect(v)

    return result


def topological_sort(graph: dict[str, list[str]]) -> list[str]:
    """Best-effort topological sort (ignores back edges in cycles)."""
    visited = set()
    result = []

    def visit(node):
        if node in visited:
            return
        visited.add(node)
        for dep in sorted(graph.get(node, [])):
            visit(dep)
        result.append(node)

    for node in sorted(graph.keys()):
        visit(node)

    return result


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, help="Package directory (e.g., eos_ai)")
    parser.add_argument("--output", required=True, help="Output JSON path")
    parser.add_argument("--repo", default="/opt/OS", help="Repository root")
    args = parser.parse_args()

    os.chdir(args.repo)
    root_dir = args.root
    package_prefix = root_dir.replace("/", ".")

    modules = find_modules(root_dir)
    print(f"Found {len(modules)} modules in {root_dir}/")

    graph = {}
    dep_graph = defaultdict(list)
    module_data = {}

    for mod in modules:
        parts = mod.split(".")
        if parts[-1] == "__init__":
            filepath = os.path.join(*parts[:-1], "__init__.py")
        else:
            filepath = os.path.join(*parts) + ".py"
            if not os.path.exists(filepath):
                filepath = os.path.join(*parts, "__init__.py")

        if not os.path.exists(filepath):
            continue

        imports = extract_imports(filepath, package_prefix)
        file_size = os.path.getsize(filepath)

        all_targets = [i["target"] for i in imports["module_level"]] + \
                      [i["target"] for i in imports["lazy"]]

        dep_graph[mod] = sorted(set(all_targets))

        module_data[mod] = {
            "file": filepath,
            "size_bytes": file_size,
            "module_level_imports": imports["module_level"],
            "lazy_imports": imports["lazy"],
            "module_level_count": len(imports["module_level"]),
            "lazy_count": len(imports["lazy"]),
            "parse_error": imports["parse_error"],
        }

    cycles = detect_cycles(dict(dep_graph))
    topo_order = topological_sort(dict(dep_graph))

    cycle_members = set()
    for cycle in cycles:
        cycle_members.update(cycle)

    for mod in module_data:
        module_data[mod]["in_cycle"] = mod in cycle_members
        module_data[mod]["topo_position"] = topo_order.index(mod) if mod in topo_order else -1

    snapshot = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "root": root_dir,
        "package_prefix": package_prefix,
        "total_modules": len(modules),
        "total_module_level_imports": sum(d["module_level_count"] for d in module_data.values()),
        "total_lazy_imports": sum(d["lazy_count"] for d in module_data.values()),
        "cycle_count": len(cycles),
        "cycles": cycles,
        "cycle_member_count": len(cycle_members),
        "topological_order": topo_order,
        "modules": module_data,
    }

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(snapshot, f, indent=2)

    print(f"Modules: {len(modules)}")
    print(f"Module-level imports: {snapshot['total_module_level_imports']}")
    print(f"Lazy imports: {snapshot['total_lazy_imports']}")
    print(f"Cycles: {len(cycles)} ({len(cycle_members)} modules)")
    print(f"Written to {args.output}")


if __name__ == "__main__":
    main()
