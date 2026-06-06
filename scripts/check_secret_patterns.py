#!/usr/bin/env python3
"""Pre-commit hook: reject commits containing secret patterns.

Scans staged files for patterns that look like API keys, tokens, or passwords.
Prevents accidental secret leakage after migration to 1Password.

Usage (in .git/hooks/pre-commit or via pre-commit framework):
    python3 scripts/check_secret_patterns.py
"""
from __future__ import annotations

import re
import subprocess
import sys

SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Anthropic API key", re.compile(r"sk-ant-api\d{2}-[A-Za-z0-9_-]{20,}")),
    ("Anthropic OAuth token", re.compile(r"sk-ant-oat\d{2}-[A-Za-z0-9_-]{20,}")),
    ("OpenAI API key", re.compile(r"sk-proj-[A-Za-z0-9_-]{20,}")),
    ("Groq API key", re.compile(r"gsk_[A-Za-z0-9]{20,}")),
    ("Perplexity API key", re.compile(r"pplx-[A-Za-z0-9]{20,}")),
    ("Notion API key", re.compile(r"ntn_[A-Za-z0-9]{20,}")),
    ("Notion token (legacy)", re.compile(r"secret_ntn_[A-Za-z0-9]{20,}")),
    ("Apify API token", re.compile(r"apify_api_[A-Za-z0-9]{20,}")),
    ("Apify proxy password", re.compile(r"apify_proxy_[A-Za-z0-9]{20,}")),
    ("Neon DB password", re.compile(r"npg_[A-Za-z0-9]{10,}")),
    ("Discord bot token", re.compile(r"MTQ[A-Za-z0-9]{20,}\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{20,}")),
    ("Google API key", re.compile(r"AIzaSy[A-Za-z0-9_-]{33}")),
    ("PostgreSQL URL with password", re.compile(r"postgresql://[^:]+:[^@]+@[^/]+/")),
]

IGNORE_PATHS = {
    ".env.example",
    ".env.tpl",
    "infra/docker/.env.example",
    "scripts/check_secret_patterns.py",
}


def get_staged_files() -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True, text=True,
    )
    return [f for f in result.stdout.strip().split("\n") if f]


def check_file(path: str) -> list[str]:
    if any(path.endswith(ignore) for ignore in IGNORE_PATHS):
        return []

    try:
        result = subprocess.run(
            ["git", "show", f":{path}"],
            capture_output=True, text=True,
        )
        content = result.stdout
    except Exception:
        return []

    violations = []
    for line_num, line in enumerate(content.split("\n"), 1):
        if line.strip().startswith("#"):
            continue
        if "op://" in line:
            continue
        for name, pattern in SECRET_PATTERNS:
            if pattern.search(line):
                violations.append(f"  {path}:{line_num} — {name} detected")
    return violations


def main() -> int:
    files = get_staged_files()
    all_violations: list[str] = []

    for path in files:
        all_violations.extend(check_file(path))

    if all_violations:
        print("BLOCKED: Secret patterns found in staged files:\n")
        for v in all_violations:
            print(v)
        print("\nSecrets belong in 1Password, not in committed files.")
        print("Use op:// references in .env.tpl files instead.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
