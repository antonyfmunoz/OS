"""Verify the runtime template store is populated and valid."""
from __future__ import annotations

import json
import os
import sys

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
_TEMPLATE_DIR = os.path.join(_REPO_ROOT, "data", "umh", "organism", "templates")


def verify() -> bool:
    if not os.path.isdir(_TEMPLATE_DIR):
        print(f"FAIL: Template directory does not exist: {_TEMPLATE_DIR}")
        return False

    templates_path = os.path.join(_TEMPLATE_DIR, "templates.jsonl")
    if not os.path.isfile(templates_path):
        print(f"FAIL: templates.jsonl not found at {templates_path}")
        return False

    count = 0
    with open(templates_path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                if "template_id" not in data:
                    print(f"FAIL: template entry missing template_id")
                    return False
                if data.get("status") != "promoted":
                    continue
                count += 1
            except json.JSONDecodeError as e:
                print(f"FAIL: invalid JSON in templates.jsonl: {e}")
                return False

    if count < 1:
        print(f"FAIL: no promoted templates found (count={count})")
        return False

    print(f"OK: {count} promoted templates in store")
    return True


if __name__ == "__main__":
    sys.exit(0 if verify() else 1)
