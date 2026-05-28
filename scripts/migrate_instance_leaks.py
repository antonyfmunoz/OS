#!/usr/bin/env python3
"""Bulk migration tool: mechanically replaces instance-specific values in substrate/ code.

This script reads the instance config (data/umh/instance.json) to know what values
are instance-specific, then scans substrate/ for hardcoded occurrences and applies
safe, mechanical replacements.

Categories of replacement:
  1. Session prefixes ("dex_builder_main") → make_session_name("builder", "main")
  2. Hardcoded IPs → os.environ.get("ENV_VAR", "")
  3. handled_by='dex_*' → handler name prefix derived from self_model at runtime
  4. Identity prompts ("You are DEX, EA to Antony") → self_model queries
  5. AI name defaults ("DEX") → empty string or get_ai_name()
  6. Founder/company names in code → self_model/BIS runtime lookups
  7. Account IDs (GitHub usernames) → env vars

Modes:
  --scan     Show all leaks with proposed fixes (default)
  --fix      Apply all safe mechanical replacements
  --report   Generate a migration report to stdout

Usage:
  python3 scripts/migrate_instance_leaks.py --scan
  python3 scripts/migrate_instance_leaks.py --fix
  python3 scripts/migrate_instance_leaks.py --report > migration_report.md

UMH substrate subsystem. Domain-agnostic.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))


def _load_instance_config() -> dict:
    config_path = _REPO_ROOT / "data" / "umh" / "instance.json"
    if config_path.exists():
        return json.loads(config_path.read_text(encoding="utf-8"))
    return {}


# ── Replacement Rules ───────────────────────────────────────────────────────
# Each rule: (compiled_regex, category, replacement_fn_or_string, description)
# replacement can be a string or a callable(match, line, filepath) -> str

_SESSION_PREFIX_PATTERN = re.compile(r'"dex_(builder_main|product_main|main|discord|unnamed)"')
_SESSION_PREFIX_SINGLE = re.compile(r"'dex_(builder_main|product_main|main|discord|unnamed)'")

_HANDLED_BY_PATTERN = re.compile(r"handled_by='dex_(\w+)'")
_HANDLED_BY_DQ = re.compile(r'handled_by="dex_(\w+)"')

_EVENT_TYPE_PATTERN = re.compile(r"event_type='dex_(\w+)'")
_EVENT_TYPE_DQ = re.compile(r'event_type="dex_(\w+)"')

_IP_VPS = re.compile(r'"100\.77\.233\.50"')
_IP_BEAST = re.compile(r'"100\.74\.199\.102"')
_IP_VPS_SQ = re.compile(r"'100\.77\.233\.50'")
_IP_BEAST_SQ = re.compile(r"'100\.74\.199\.102'")

_GITHUB_USER = re.compile(r'antonyfmunoz')

# AI name in string defaults
_DEX_DEFAULT_DQ = re.compile(r'"DEX"')
_DEX_DEFAULT_SQ = re.compile(r"'DEX'")

# Identity prompts
_IDENTITY_PROMPT = re.compile(r'You are DEX,?\s*(?:EA|Executive Assistant)\s*to\s*Antony(?:\s*F\.?)?\s*Munoz', re.IGNORECASE)


class Replacement:
    def __init__(self, pattern: re.Pattern, category: str, description: str,
                 replacement: str | None = None):
        self.pattern = pattern
        self.category = category
        self.description = description
        self.replacement = replacement


# These are safe mechanical replacements — they change string literals
# without altering logic.

SAFE_REPLACEMENTS: list[Replacement] = [
    # IPs → env var lookups
    Replacement(_IP_VPS, "infra_ip",
                "Hardcoded VPS IP → env var",
                'os.environ.get("TAILSCALE_VPS_IP", "")'),
    Replacement(_IP_BEAST, "infra_ip",
                "Hardcoded Beast IP → env var",
                'os.environ.get("EOS_LOCAL_BRIDGE_IP", "")'),
    Replacement(_IP_VPS_SQ, "infra_ip",
                "Hardcoded VPS IP (single quotes) → env var",
                "os.environ.get('TAILSCALE_VPS_IP', '')"),
    Replacement(_IP_BEAST_SQ, "infra_ip",
                "Hardcoded Beast IP (single quotes) → env var",
                "os.environ.get('EOS_LOCAL_BRIDGE_IP', '')"),
]


def _scan_file(filepath: Path) -> list[dict]:
    """Find all instance leaks in a file."""
    findings: list[dict] = []
    rel = str(filepath.relative_to(_REPO_ROOT))

    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    lines = content.splitlines()
    for line_no, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue

        # Session prefixes
        for pat in [_SESSION_PREFIX_PATTERN, _SESSION_PREFIX_SINGLE]:
            m = pat.search(line)
            if m:
                findings.append({
                    "file": rel, "line": line_no, "category": "session_prefix",
                    "match": m.group(0), "content": stripped[:120],
                    "fix": f'make_session_name("{m.group(1).replace("_", '", "')}")',
                })

        # handled_by with dex_ prefix
        for pat in [_HANDLED_BY_PATTERN, _HANDLED_BY_DQ]:
            m = pat.search(line)
            if m:
                findings.append({
                    "file": rel, "line": line_no, "category": "handler_prefix",
                    "match": m.group(0), "content": stripped[:120],
                    "fix": f"Use f'{{_ai_prefix}}{m.group(1)}' with _ai_prefix from self_model",
                })

        # event_type with dex_ prefix
        for pat in [_EVENT_TYPE_PATTERN, _EVENT_TYPE_DQ]:
            m = pat.search(line)
            if m:
                findings.append({
                    "file": rel, "line": line_no, "category": "event_type_prefix",
                    "match": m.group(0), "content": stripped[:120],
                    "fix": f"Use f'{{_ai_prefix}}{m.group(1)}' with _ai_prefix from self_model",
                })

        # Hardcoded IPs
        for pat, name in [(_IP_VPS, "VPS IP"), (_IP_BEAST, "Beast IP"),
                          (_IP_VPS_SQ, "VPS IP"), (_IP_BEAST_SQ, "Beast IP")]:
            if pat.search(line):
                findings.append({
                    "file": rel, "line": line_no, "category": "infra_ip",
                    "match": pat.search(line).group(0), "content": stripped[:120],
                    "fix": f"Use os.environ.get() for {name}",
                })

        # GitHub username
        if _GITHUB_USER.search(line) and not stripped.startswith("#"):
            findings.append({
                "file": rel, "line": line_no, "category": "account_id",
                "match": "antonyfmunoz", "content": stripped[:120],
                "fix": "Use os.environ.get('GITHUB_USER', '') or config",
            })

        # Identity prompts
        m = _IDENTITY_PROMPT.search(line)
        if m:
            findings.append({
                "file": rel, "line": line_no, "category": "identity_prompt",
                "match": m.group(0), "content": stripped[:120],
                "fix": "Build identity prompt from self_model at runtime",
            })

        # DEX as string literal (not in comments, not in variable names)
        for pat in [_DEX_DEFAULT_DQ, _DEX_DEFAULT_SQ]:
            if pat.search(line) and "dex_" not in line.lower():
                findings.append({
                    "file": rel, "line": line_no, "category": "ai_name",
                    "match": pat.search(line).group(0), "content": stripped[:120],
                    "fix": "Use get_ai_name() or empty string default",
                })

    return findings


def scan_all() -> list[dict]:
    """Scan all substrate/ files for instance leaks."""
    findings: list[dict] = []
    for p in sorted((_REPO_ROOT / "substrate").rglob("*.py")):
        if "__pycache__" in str(p):
            continue
        findings.extend(_scan_file(p))
    return findings


def report(findings: list[dict]) -> str:
    """Generate a markdown migration report."""
    lines = [
        "# Instance Leak Migration Report",
        f"\nTotal findings: {len(findings)}",
        f"Files affected: {len(set(f['file'] for f in findings))}",
        "",
    ]

    by_cat: dict[str, list[dict]] = {}
    for f in findings:
        by_cat.setdefault(f["category"], []).append(f)

    for cat in sorted(by_cat):
        items = by_cat[cat]
        lines.append(f"\n## {cat} ({len(items)} occurrences)")
        lines.append("")
        for item in items:
            lines.append(f"- `{item['file']}:{item['line']}` — {item['content'][:80]}")
            lines.append(f"  Fix: {item['fix']}")

    return "\n".join(lines)


def main() -> int:
    args = sys.argv[1:]
    mode = "scan"
    if "--fix" in args:
        mode = "fix"
    elif "--report" in args:
        mode = "report"

    findings = scan_all()

    if mode == "report":
        print(report(findings))
        return 0

    if mode == "scan":
        if not findings:
            print("No instance leaks found in substrate/")
            return 0

        print(f"\nInstance leaks found: {len(findings)}")
        print(f"Files affected: {len(set(f['file'] for f in findings))}\n")

        by_cat: dict[str, list[dict]] = {}
        for f in findings:
            by_cat.setdefault(f["category"], []).append(f)

        for cat in sorted(by_cat):
            items = by_cat[cat]
            print(f"── {cat} ({len(items)}) ──")
            for item in items:
                print(f"  {item['file']}:{item['line']}")
                print(f"    {item['content'][:100]}")
                print(f"    → {item['fix']}")
            print()

        print(f"Run with --fix to apply safe mechanical replacements")
        print(f"Run with --report to generate a markdown report")
        return 1

    if mode == "fix":
        # Apply safe mechanical replacements
        fixed_count = 0
        files_modified: set[str] = set()

        for p in sorted((_REPO_ROOT / "substrate").rglob("*.py")):
            if "__pycache__" in str(p):
                continue
            try:
                content = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            original = content
            for repl in SAFE_REPLACEMENTS:
                content = repl.pattern.sub(repl.replacement, content)

            if content != original:
                p.write_text(content, encoding="utf-8")
                rel = str(p.relative_to(_REPO_ROOT))
                files_modified.add(rel)
                fixed_count += 1
                print(f"  Fixed: {rel}")

        print(f"\nApplied safe replacements to {fixed_count} files")
        if files_modified:
            print(f"Modified: {', '.join(sorted(files_modified))}")

        # Re-scan to show remaining
        remaining = scan_all()
        if remaining:
            print(f"\nRemaining leaks requiring manual migration: {len(remaining)}")
            by_cat = {}
            for f in remaining:
                by_cat.setdefault(f["category"], []).append(f)
            for cat in sorted(by_cat):
                print(f"  {cat}: {len(by_cat[cat])}")
        else:
            print("\nAll instance leaks resolved!")

        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
