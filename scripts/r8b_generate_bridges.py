#!/usr/bin/env python3
"""Generate temporary bridge modules in eos_ai/ that re-export from runtime/.

These bridges ensure external consumers (`from eos_ai.X import Y`) continue
working after the atomic move to runtime/. They are temporary — R8d replaces
them with validated generated shims.

Bridge format:
    # R8b bridge — replaced by R8d generated shim
    from runtime.{module} import *  # noqa: F401,F403
"""
import json
import os
import sys
import time
from pathlib import Path

REPO_ROOT = "/opt/OS"
RUNTIME_DIR = os.path.join(REPO_ROOT, "runtime")
EOS_AI_DIR = os.path.join(REPO_ROOT, "eos_ai")
HEADER = "# R8b bridge — replaced by R8d generated shim\n"


def main():
    os.chdir(REPO_ROOT)

    bridges_created = []
    special_cases = []
    errors = []

    # --- Top-level modules ---
    for py_file in sorted(Path(RUNTIME_DIR).glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        module = py_file.stem
        bridge_path = os.path.join(EOS_AI_DIR, f"{module}.py")
        content = f"{HEADER}from runtime.{module} import *  # noqa: F401,F403\n"
        os.makedirs(os.path.dirname(bridge_path), exist_ok=True)
        Path(bridge_path).write_text(content)
        bridges_created.append({
            "bridge": f"eos_ai/{module}.py",
            "target": f"runtime.{module}",
            "type": "top_level",
        })

    # --- transport/ submodules ---
    transport_dir = os.path.join(RUNTIME_DIR, "transport")
    eos_transport_dir = os.path.join(EOS_AI_DIR, "transport")
    os.makedirs(eos_transport_dir, exist_ok=True)

    # transport/__init__.py bridge
    init_content = f"{HEADER}from runtime.transport import *  # noqa: F401,F403\n"
    Path(os.path.join(eos_transport_dir, "__init__.py")).write_text(init_content)
    bridges_created.append({
        "bridge": "eos_ai/transport/__init__.py",
        "target": "runtime.transport",
        "type": "transport_init",
    })

    for py_file in sorted(Path(transport_dir).glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        module = py_file.stem
        bridge_path = os.path.join(eos_transport_dir, f"{module}.py")
        content = f"{HEADER}from runtime.transport.{module} import *  # noqa: F401,F403\n"
        Path(bridge_path).write_text(content)
        bridges_created.append({
            "bridge": f"eos_ai/transport/{module}.py",
            "target": f"runtime.transport.{module}",
            "type": "transport",
        })

    # --- substrate/ submodules (preserve shim chain: substrate -> transport) ---
    substrate_dir = os.path.join(RUNTIME_DIR, "substrate")
    eos_substrate_dir = os.path.join(EOS_AI_DIR, "substrate")
    os.makedirs(eos_substrate_dir, exist_ok=True)

    # substrate/__init__.py bridge
    sub_init_content = f"{HEADER}from runtime.substrate import *  # noqa: F401,F403\n"
    Path(os.path.join(eos_substrate_dir, "__init__.py")).write_text(sub_init_content)
    bridges_created.append({
        "bridge": "eos_ai/substrate/__init__.py",
        "target": "runtime.substrate",
        "type": "substrate_init",
    })

    for py_file in sorted(Path(substrate_dir).glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        module = py_file.stem
        bridge_path = os.path.join(eos_substrate_dir, f"{module}.py")
        # substrate bridges point to runtime.transport (preserving shim chain)
        content = f"{HEADER}from runtime.transport.{module} import *  # noqa: F401,F403\n"
        Path(bridge_path).write_text(content)
        bridges_created.append({
            "bridge": f"eos_ai/substrate/{module}.py",
            "target": f"runtime.transport.{module}",
            "type": "substrate_chain",
        })

    # --- runtime/ subdir (flattened: eos_ai.runtime.X -> runtime.X) ---
    eos_runtime_dir = os.path.join(EOS_AI_DIR, "runtime")
    os.makedirs(eos_runtime_dir, exist_ok=True)

    for flat_module in ["work_state", "provider_state"]:
        bridge_path = os.path.join(eos_runtime_dir, f"{flat_module}.py")
        content = f"{HEADER}from runtime.{flat_module} import *  # noqa: F401,F403\n"
        Path(bridge_path).write_text(content)
        bridges_created.append({
            "bridge": f"eos_ai/runtime/{flat_module}.py",
            "target": f"runtime.{flat_module}",
            "type": "depth_flattened",
        })
        special_cases.append(f"eos_ai/runtime/{flat_module}.py -> runtime.{flat_module} (depth change)")

    # --- interfaces/ ---
    interfaces_dir = os.path.join(RUNTIME_DIR, "interfaces")
    eos_interfaces_dir = os.path.join(EOS_AI_DIR, "interfaces")
    os.makedirs(eos_interfaces_dir, exist_ok=True)

    # interfaces/__init__.py (may not exist in runtime, create empty bridge)
    if os.path.exists(os.path.join(interfaces_dir, "__init__.py")):
        iface_init = f"{HEADER}from runtime.interfaces import *  # noqa: F401,F403\n"
    else:
        iface_init = f"{HEADER}# runtime.interfaces has no __init__.py\n"
    Path(os.path.join(eos_interfaces_dir, "__init__.py")).write_text(iface_init)

    for py_file in sorted(Path(interfaces_dir).glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        module = py_file.stem
        bridge_path = os.path.join(eos_interfaces_dir, f"{module}.py")
        content = f"{HEADER}from runtime.interfaces.{module} import *  # noqa: F401,F403\n"
        Path(bridge_path).write_text(content)
        bridges_created.append({
            "bridge": f"eos_ai/interfaces/{module}.py",
            "target": f"runtime.interfaces.{module}",
            "type": "interfaces",
        })

    # --- Manifest ---
    manifest = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "generator": "scripts/r8b_generate_bridges.py",
        "total_bridges": len(bridges_created),
        "by_type": {},
        "special_cases": special_cases,
        "errors": errors,
        "bridges": bridges_created,
    }

    for b in bridges_created:
        t = b["type"]
        manifest["by_type"][t] = manifest["by_type"].get(t, 0) + 1

    manifest_path = os.path.join(REPO_ROOT, "data/migration/r8b_bridge_manifest.json")
    Path(manifest_path).parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"Bridges created: {len(bridges_created)}")
    for t, c in sorted(manifest["by_type"].items()):
        print(f"  {t}: {c}")
    if special_cases:
        print(f"Special cases: {len(special_cases)}")
        for sc in special_cases:
            print(f"  {sc}")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
