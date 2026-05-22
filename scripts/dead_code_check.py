#!/usr/bin/env python3
"""Check for dead code in the substrate package.

Every .py file under substrate/ (excluding __init__.py) should be
imported by at least one other file. This is invariant #9.
"""

import os
import re
import sys


def main():
    substrate_files = []
    for root, dirs, files in os.walk("substrate"):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", "tests")]
        for f in files:
            if f.endswith(".py") and f != "__init__.py":
                path = os.path.join(root, f)
                substrate_files.append(path)

    dead = []
    for path in substrate_files:
        module = path.replace("/", ".").replace(".py", "")
        pattern = re.compile(rf"from\s+{re.escape(module)}|import\s+{re.escape(module)}")
        found = False
        for root, dirs, files in os.walk("."):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", ".claude", "_archive")]
            for f in files:
                if f.endswith(".py"):
                    fpath = os.path.join(root, f)
                    if fpath == f"./{path}":
                        continue
                    try:
                        with open(fpath) as fp:
                            content = fp.read()
                        if pattern.search(content):
                            found = True
                            break
                    except Exception:
                        continue
            if found:
                break
        if not found:
            dead.append(path)

    if dead:
        print(f"DEAD CODE FOUND ({len(dead)} files):")
        for d in sorted(dead):
            print(f"  {d}")
        sys.exit(1)
    else:
        print(f"OK: all {len(substrate_files)} substrate files are imported")
        sys.exit(0)


if __name__ == "__main__":
    main()
