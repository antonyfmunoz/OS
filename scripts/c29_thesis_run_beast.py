#!/usr/bin/env python3
"""Beast launcher for C29.5 Thesis Validation Runner.

Injects CLERK_PASSWORD from 1Password and runs the thesis runner.
Same pattern as c29_run_beast.py for the Class B runner.

Usage (on Beast):
  python scripts/c29_thesis_run_beast.py --all
  python scripts/c29_thesis_run_beast.py --test continuity
  python scripts/c29_thesis_run_beast.py --test governance
"""

import os
import subprocess
import sys

os.environ["UMH_ROOT"] = r"C:\dev\dev\OS"

result = subprocess.run(
    [
        "op",
        "item",
        "get",
        "Cockpit-Clerk-Login",
        "--vault",
        os.getenv("UMH_OP_VAULT", "UMH-Production"),
        "--reveal",
        "--fields",
        "password",
    ],
    capture_output=True,
    text=True,
)

if result.returncode != 0:
    print(f"1Password error: {result.stderr}", file=sys.stderr)
    sys.exit(1)

os.environ["CLERK_PASSWORD"] = result.stdout.strip()

sys.exit(
    subprocess.run(
        [sys.executable, "scripts/c29_thesis_runner.py"] + sys.argv[1:],
    ).returncode
)
