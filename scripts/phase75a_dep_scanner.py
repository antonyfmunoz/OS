#!/usr/bin/env python3
"""Phase 75A — AST-based dependency scanner for UMH.

Extracts internal imports among umh.* modules, identifies:
- internal import graph (who imports whom)
- circular imports
- high fan-in modules (most imported)
- high fan-out modules (most imports)
- boundary violations
"""

import ast
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path("/opt/OS")
UMH = ROOT / "umh"


def find_python_files(base: Path) -> list[Path]:
    return sorted(
        p for p in base.rglob("*.py")
        if "__pycache__" not in str(p)
    )


def module_from_path(p: Path) -> str:
    rel = p.relative_to(ROOT)
    parts = list(rel.parts)
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1].removesuffix(".py")
    return ".".join(parts)


def extract_imports(filepath: Path) -> list[str]:
    try:
        source = filepath.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, ValueError):
        return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("umh"):
                    imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("umh"):
                imports.append(node.module)
    return sorted(set(imports))


def normalize_to_package(mod: str) -> str:
    parts = mod.split(".")
    if len(parts) >= 2:
        return ".".join(parts[:2])
    return mod


def find_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    visited = set()
    on_stack = set()
    stack = []
    cycles = []

    def dfs(node):
        visited.add(node)
        on_stack.add(node)
        stack.append(node)
        for neighbor in graph.get(node, set()):
            if neighbor not in visited:
                dfs(neighbor)
            elif neighbor in on_stack:
                idx = stack.index(neighbor)
                cycle = stack[idx:] + [neighbor]
                cycles.append(cycle)
        stack.pop()
        on_stack.discard(node)

    for node in sorted(graph):
        if node not in visited:
            dfs(node)
    return cycles


def detect_sensitive_imports(files: list[Path], mod_map: dict[str, str]) -> list[dict]:
    """Check for subprocess/docker imports outside allowed layers."""
    violations = []
    allowed_pkgs = {"umh.environments", "umh.adapters", "umh.substrate", "umh.nodes", "umh.execution"}
    sensitive_names = {"subprocess", "docker"}

    for f in files:
        mod = module_from_path(f)
        pkg = normalize_to_package(mod)
        if pkg in allowed_pkgs:
            continue
        try:
            source = f.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=str(f))
        except (SyntaxError, ValueError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in sensitive_names:
                        violations.append({
                            "type": "env_import_violation",
                            "source": mod,
                            "target": alias.name,
                            "rule": f"{alias.name} import outside allowed layer"
                        })
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module in sensitive_names:
                    violations.append({
                        "type": "env_import_violation",
                        "source": mod,
                        "target": node.module,
                        "rule": f"{node.module} import outside allowed layer"
                    })
    return violations


def main():
    files = find_python_files(UMH)
    print(f"Scanning {len(files)} Python files in umh/...")

    mod_imports: dict[str, list[str]] = {}
    mod_dependents: dict[str, set[str]] = defaultdict(set)

    for f in files:
        mod = module_from_path(f)
        imps = extract_imports(f)
        mod_imports[mod] = imps
        for imp in imps:
            mod_dependents[imp].add(mod)

    # Package-level graph
    pkg_graph: dict[str, set[str]] = defaultdict(set)
    for mod, imps in mod_imports.items():
        src_pkg = normalize_to_package(mod)
        for imp in imps:
            dst_pkg = normalize_to_package(imp)
            if src_pkg != dst_pkg:
                pkg_graph[src_pkg].add(dst_pkg)

    # Fan-in / fan-out
    fan_in: dict[str, int] = defaultdict(int)
    fan_out: dict[str, int] = defaultdict(int)
    for mod, imps in mod_imports.items():
        external = [i for i in imps if normalize_to_package(i) != normalize_to_package(mod)]
        fan_out[mod] = len(external)
        for imp in external:
            fan_in[imp] += 1

    top_fan_in = sorted(fan_in.items(), key=lambda x: -x[1])[:30]
    top_fan_out = sorted(fan_out.items(), key=lambda x: -x[1])[:30]

    # Cycles at package level
    cycles = find_cycles(pkg_graph)

    # Boundary violations
    violations = []
    scoring_mods = {m for m in mod_imports if "scoring" in m or "score" in m}
    pattern_mods = {m for m in mod_imports if "pattern" in m}

    for mod, imps in mod_imports.items():
        for imp in imps:
            if mod in scoring_mods and ("execution" in imp or "execute" in imp):
                violations.append({
                    "type": "scoring_executes",
                    "source": mod,
                    "target": imp,
                    "rule": "scoring modules must not directly execute"
                })
            if mod in pattern_mods and "memory" in imp and "store" in imp:
                violations.append({
                    "type": "pattern_mutates_memory",
                    "source": mod,
                    "target": imp,
                    "rule": "pattern modules must not mutate historical records"
                })

    violations.extend(detect_sensitive_imports(files, {}))

    result = {
        "total_modules": len(mod_imports),
        "total_internal_edges": sum(len(v) for v in mod_imports.values()),
        "package_graph": {k: sorted(v) for k, v in sorted(pkg_graph.items())},
        "top_fan_in": top_fan_in,
        "top_fan_out": top_fan_out,
        "package_cycles": cycles,
        "violations": violations,
        "module_imports": {k: v for k, v in sorted(mod_imports.items())},
        "module_dependents": {k: sorted(v) for k, v in sorted(mod_dependents.items())},
    }

    out_path = ROOT / "docs" / "system" / "dependency_data.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2))
    print(f"Wrote {out_path}")

    print(f"\n=== DEPENDENCY GRAPH SUMMARY ===")
    print(f"Modules scanned: {len(mod_imports)}")
    print(f"Internal import edges: {sum(len(v) for v in mod_imports.values())}")
    print(f"Packages: {len(pkg_graph)}")
    print(f"Package-level cycles: {len(cycles)}")
    print(f"Boundary violations: {len(violations)}")
    print(f"\nTop 15 fan-in (most imported):")
    for mod, count in top_fan_in[:15]:
        print(f"  {count:3d} <- {mod}")
    print(f"\nTop 15 fan-out (most imports):")
    for mod, count in top_fan_out[:15]:
        print(f"  {count:3d} -> {mod}")
    if cycles:
        print(f"\nPackage cycles:")
        for c in cycles[:10]:
            print(f"  {'->'.join(c)}")
    if violations:
        print(f"\nBoundary violations:")
        for v in violations[:20]:
            print(f"  [{v['type']}] {v['source']} -> {v['target']}: {v['rule']}")

    return result


if __name__ == "__main__":
    main()
