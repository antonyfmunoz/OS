#!/usr/bin/env python3
"""Phase 75A — Auto-classify UMH modules by PRD domain and MVP status."""

import ast
import json
from pathlib import Path

ROOT = Path("/opt/OS")
UMH = ROOT / "umh"

# Package -> PRD domain mapping
PKG_TO_DOMAIN = {
    "umh.actions": "execution",
    "umh.adapters": "adapters",
    "umh.agents": "capabilities",
    "umh.analytics": "learning",
    "umh.attention": "interpretation",
    "umh.brains": "profiles",
    "umh.capabilities": "capabilities",
    "umh.capability": "capabilities",
    "umh.cells": "execution",
    "umh.context": "interpretation",
    "umh.control": "core",
    "umh.core": "core",
    "umh.decision": "interpretation",
    "umh.environments": "environments",
    "umh.events": "core",
    "umh.execution": "execution",
    "umh.feedback": "learning",
    "umh.gateway": "core",
    "umh.goals": "planning",
    "umh.governance": "governance",
    "umh.intent": "interpretation",
    "umh.interfaces": "interface",
    "umh.jobs": "execution",
    "umh.learning": "learning",
    "umh.memory": "memory",
    "umh.model": "profiles",
    "umh.nodes": "runtime",
    "umh.objectives": "planning",
    "umh.orchestrator": "planning",
    "umh.patterns": "learning",
    "umh.persistence_layer": "storage",
    "umh.planning": "planning",
    "umh.policy": "governance",
    "umh.prediction": "learning",
    "umh.primitives": "ontology",
    "umh.protocols": "protocols",
    "umh.reasoning": "interpretation",
    "umh.runtime": "runtime",
    "umh.runtime_engine": "runtime",
    "umh.runtime_loop": "execution",
    "umh.scheduler": "execution",
    "umh.security": "security",
    "umh.signal": "interpretation",
    "umh.stages": "execution",
    "umh.storage": "storage",
    "umh.strategy": "planning",
    "umh.substrate": "presence",
    "umh.tools": "capabilities",
    "umh.workflows": "execution",
    "umh.workstation": "workstation",
    "umh.world": "world_model",
}

# MVP_CORE: modules required for the minimum working 9-stage run loop
MVP_CORE_PACKAGES = {
    "umh.core", "umh.signal", "umh.intent", "umh.world",
    "umh.capability", "umh.governance", "umh.execution",
    "umh.feedback", "umh.context", "umh.gateway",
    "umh.protocols", "umh.storage", "umh.events",
    "umh.decision", "umh.goals", "umh.memory",
}

# MVP_CORE specific files outside core packages
MVP_CORE_FILES = {
    "umh.run", "umh.__init__", "umh.__main__",
    "umh.control.api", "umh.control.identity", "umh.control.cli",
    "umh.adapters.base", "umh.adapters.contracts", "umh.adapters.registry",
    "umh.adapters.llm", "umh.adapters.null", "umh.adapters.stubs",
    "umh.adapters.bridge",
    "umh.planning.planner", "umh.planning.models",
    "umh.planning.validator", "umh.planning.quality",
}

# MVP_SUPPORT: valuable for MVP but not on critical path
MVP_SUPPORT_PACKAGES = {
    "umh.planning", "umh.adapters", "umh.control",
    "umh.stages", "umh.strategy", "umh.attention",
    "umh.security",
}

# FUTURE: intentionally deferred
FUTURE_PACKAGES = {
    "umh.nodes", "umh.cells",
    "umh.workflows",
}

# DELETE_CANDIDATE patterns (file-name heuristics)
DELETE_CANDIDATE_PATTERNS = []


def module_from_path(p: Path) -> str:
    rel = p.relative_to(ROOT)
    parts = list(rel.parts)
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1].removesuffix(".py")
    return ".".join(parts)


def get_purpose(filepath: Path) -> str:
    """Extract first line of docstring."""
    try:
        source = filepath.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(filepath))
        docstring = ast.get_docstring(tree)
        if docstring:
            first_line = docstring.strip().split("\n")[0]
            return first_line[:120]
    except (SyntaxError, ValueError):
        pass
    return ""


def classify(mod: str, filepath: Path) -> str:
    """Classify module as MVP_CORE/MVP_SUPPORT/KEEP/FUTURE/DELETE_CANDIDATE."""
    if mod in MVP_CORE_FILES:
        return "MVP_CORE"

    pkg = ".".join(mod.split(".")[:2])

    if pkg in MVP_CORE_PACKAGES:
        return "MVP_CORE"

    if mod in MVP_CORE_FILES:
        return "MVP_CORE"

    if pkg in FUTURE_PACKAGES:
        return "FUTURE"

    if pkg in MVP_SUPPORT_PACKAGES:
        return "MVP_SUPPORT"

    # runtime_engine is legacy EOS — mostly KEEP, some MVP_SUPPORT
    if pkg == "umh.runtime_engine":
        name = mod.split(".")[-1]
        # Core runtime_engine files needed for MVP
        mvp_re = {
            "cognitive_loop", "agent_runtime", "model_router", "gateway",
            "session_runtime", "execution_spine", "execution_engine",
            "context_builder", "context_engine",
        }
        if name in mvp_re:
            return "MVP_SUPPORT"
        return "KEEP"

    # runtime (intelligence kernel) is KEEP — enhances but not required for MVP
    if pkg == "umh.runtime":
        return "KEEP"

    # substrate is mostly presence/operator — MVP_SUPPORT for core, KEEP for rest
    if pkg == "umh.substrate":
        name = mod.split(".")[-1]
        mvp_sub = {
            "execution_adapter", "execution_authority", "execution_control",
            "execution_router", "execution_worker", "execution_constraints",
            "operator_session", "operator_state",
        }
        if name in mvp_sub:
            return "MVP_SUPPORT"
        return "KEEP"

    # Default classification
    if pkg == "umh.interfaces":
        return "MVP_SUPPORT"

    if pkg in {"umh.analytics", "umh.reasoning", "umh.prediction",
               "umh.patterns", "umh.model", "umh.brains",
               "umh.objectives", "umh.policy"}:
        return "KEEP"

    if pkg == "umh.persistence_layer":
        return "MVP_SUPPORT"

    if pkg == "umh.primitives":
        return "KEEP"

    if pkg == "umh.workstation":
        return "MVP_SUPPORT"

    if pkg == "umh.learning":
        return "KEEP"

    if pkg == "umh.orchestrator":
        return "MVP_SUPPORT"

    return "KEEP"


def get_domain(mod: str) -> str:
    pkg = ".".join(mod.split(".")[:2])
    return PKG_TO_DOMAIN.get(pkg, "unknown")


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


def main():
    dep_data = json.loads((ROOT / "docs/system/dependency_data.json").read_text())
    mod_dependents = dep_data.get("module_dependents", {})

    files = sorted(
        p for p in UMH.rglob("*.py")
        if "__pycache__" not in str(p)
    )

    inventory = []
    counts = {"MVP_CORE": 0, "MVP_SUPPORT": 0, "KEEP": 0, "FUTURE": 0, "DELETE_CANDIDATE": 0, "UNKNOWN": 0}

    for f in files:
        mod = module_from_path(f)
        cls = classify(mod, f)
        domain = get_domain(mod)
        purpose = get_purpose(f)
        deps = extract_imports(f)
        dependents = sorted(mod_dependents.get(mod, []))

        counts[cls] = counts.get(cls, 0) + 1

        entry = {
            "path": str(f.relative_to(ROOT)),
            "module": mod,
            "prd_domain": domain,
            "classification": cls,
            "purpose": purpose,
            "dependencies": deps,
            "dependents": dependents,
            "overlaps_with": [],
            "notes": ""
        }
        inventory.append(entry)

    out_path = ROOT / "docs/system/module_inventory.json"
    out_path.write_text(json.dumps(inventory, indent=2))
    print(f"Wrote {out_path} ({len(inventory)} modules)")

    print("\n=== Classification Counts ===")
    for cls, count in sorted(counts.items()):
        print(f"  {cls}: {count}")

    # Domain counts
    domain_counts = {}
    for entry in inventory:
        d = entry["prd_domain"]
        domain_counts[d] = domain_counts.get(d, 0) + 1
    print("\n=== PRD Domain Counts ===")
    for d, c in sorted(domain_counts.items(), key=lambda x: -x[1]):
        print(f"  {d}: {c}")


if __name__ == "__main__":
    main()
