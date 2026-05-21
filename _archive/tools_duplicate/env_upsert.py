#!/usr/bin/env python3
"""
Idempotent .env key upsert.

Usage:
    env_upsert.py <path> KEY=VALUE [KEY=VALUE ...]

Semantics:
  - If KEY exists anywhere (uncommented), replace the line in place.
  - If KEY exists but is commented out, still append a new active line
    (we don't uncomment ambiguously).
  - If KEY does not exist, append at the end under an "# EOS Discord
    mode routing" marker (added once).
  - Never writes duplicate keys.
  - Preserves surrounding content, comments, and blank lines.

Exit 0 on success, 2 on malformed arguments.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

MARKER = "# --- EOS Discord mode routing (managed by scripts/env_upsert.py) ---"


def _parse_args(argv: list[str]) -> tuple[Path, list[tuple[str, str]]]:
    if len(argv) < 3:
        print("usage: env_upsert.py <path> KEY=VALUE [...]", file=sys.stderr)
        sys.exit(2)
    path = Path(argv[1])
    pairs: list[tuple[str, str]] = []
    for tok in argv[2:]:
        if "=" not in tok:
            print(f"bad KEY=VALUE token: {tok}", file=sys.stderr)
            sys.exit(2)
        k, v = tok.split("=", 1)
        k = k.strip()
        if not re.match(r"^[A-Z_][A-Z0-9_]*$", k):
            print(f"bad env key: {k}", file=sys.stderr)
            sys.exit(2)
        pairs.append((k, v))
    return path, pairs


def main() -> int:
    path, pairs = _parse_args(sys.argv)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("")
    original = path.read_text()
    lines = original.splitlines()

    updated: dict[str, bool] = {k: False for k, _ in pairs}
    pair_map = dict(pairs)

    out_lines: list[str] = []
    key_line_re = re.compile(r"^(\s*)([A-Z_][A-Z0-9_]*)\s*=.*$")

    for line in lines:
        m = key_line_re.match(line)
        if m:
            key = m.group(2)
            if key in pair_map and not updated[key]:
                out_lines.append(f"{key}={pair_map[key]}")
                updated[key] = True
                continue
        out_lines.append(line)

    to_append = [(k, v) for k, v in pairs if not updated[k]]
    if to_append:
        if out_lines and out_lines[-1].strip() != "":
            out_lines.append("")
        if MARKER not in original:
            out_lines.append(MARKER)
        for k, v in to_append:
            out_lines.append(f"{k}={v}")

    new_content = "\n".join(out_lines)
    if original and not original.endswith("\n"):
        # match existing trailing newline behavior: always end with \n
        pass
    if not new_content.endswith("\n"):
        new_content += "\n"

    if new_content == original:
        print(f"[env_upsert] no changes needed: {path}")
        return 0

    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(new_content)
    os.replace(tmp, path)
    print(
        f"[env_upsert] updated {path}: "
        f"replaced={sum(1 for k in updated if updated[k])} "
        f"appended={len(to_append)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
