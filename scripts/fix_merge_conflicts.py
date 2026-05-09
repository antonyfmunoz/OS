#!/usr/bin/env python3
"""Fix merge conflicts in files with <<<<<<< Updated upstream pattern.

Keeps the upstream portion (between the first conflict marker and =======).
Discards the stashed portion (between ======= and >>>>>>> Stashed changes).
"""

import os
import sys

FILES = [
    "eos_ai/cognitive_loop.py",
    "eos_ai/agent_runtime.py",
    "eos_ai/model_router.py",
    "eos_ai/cc_sdk.py",
    "eos_ai/media_processor.py",
    "eos_ai/event_bus.py",
    "eos_ai/orchestrator.py",
    "services/handlers/intent_handler.py",
    "services/dm_monitor.py",
    "scripts/_tme_common.py",
    "scripts/session_start_context.py",
    "docker-compose.yml",
]

os.chdir("/opt/OS")

for filepath in FILES:
    if not os.path.exists(filepath):
        print(f"SKIP: {filepath} (not found)")
        continue

    with open(filepath) as f:
        lines = f.readlines()

    if not lines or "<<<<<<< Updated upstream" not in lines[0]:
        print(f"SKIP: {filepath} (no conflict marker on line 1)")
        continue

    sep_idx = None
    for i, line in enumerate(lines):
        if line.strip() == "=======":
            sep_idx = i
            break

    if sep_idx is None:
        print(f"SKIP: {filepath} (no ======= separator)")
        continue

    upstream = lines[1:sep_idx]
    with open(filepath, "w") as f:
        f.writelines(upstream)
    print(f"FIXED: {filepath} — {len(upstream)} lines (was {len(lines)})")

print("\nDone. Run py_compile on each to verify.")
