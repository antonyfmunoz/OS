#!/usr/bin/env python3
"""
sync_skills_to_neon.py — Canonical Tool Mastery Engine → Neon sync.

Scans /opt/OS/skills/tools/, extracts metadata + full SKILL.md content,
upserts rows into the `skills` table under the active org_id.

Usage:
    python3 scripts/sync_skills_to_neon.py --all [--dry-run]
    python3 scripts/sync_skills_to_neon.py --skill notion [--dry-run]
    python3 scripts/sync_skills_to_neon.py --all --verbose

Behavior:
    - name column holds the skill slug (e.g. "notion")
    - content column holds the full SKILL.md text (frontmatter + body)
    - version is bumped by 1 on content change, preserved otherwise
    - no UNIQUE(org_id, name) constraint exists, so we SELECT then
      UPDATE-or-INSERT (idempotent, no duplicate rows)
    - dry-run prints the diff plan without touching Neon

Exit codes:
    0 — success
    1 — fatal error (db connection, missing skill, etc.)
    2 — one or more skills failed to parse (sync continues for the rest)
"""
from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

sys.path.insert(0, "/opt/OS")

from scripts._tme_common import (  # noqa: E402
    SkillRecord,
    all_skill_slugs,
    eprint,
    load_skill,
)

from umh.environments.system_context import load_context_from_env  # noqa: E402
from umh.storage.adapters.neon import get_conn  # noqa: E402


def _raw_text(rec: SkillRecord) -> str:
    return rec.skill_md.read_text(encoding="utf-8")


def _fetch_existing(cur, org_id: str, name: str) -> tuple[str, str, int] | None:
    cur.execute(
        "SELECT id, content, version FROM skills WHERE org_id = %s AND name = %s",
        (org_id, name),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return str(row["id"]), row["content"] or "", int(row["version"] or 1)


def _sync_one(cur, org_id: str, rec: SkillRecord, dry_run: bool) -> str:
    """Return action string: 'insert' | 'update' | 'unchanged' | 'skip'."""
    if not rec.exists:
        return "skip"
    new_content = _raw_text(rec)
    existing = _fetch_existing(cur, org_id, rec.slug)
    if existing is None:
        if not dry_run:
            cur.execute(
                """
                INSERT INTO skills (id, org_id, name, content, version)
                VALUES (%s, %s, %s, %s, 1)
                """,
                (str(uuid.uuid4()), org_id, rec.slug, new_content),
            )
        return "insert"
    _id, old_content, old_version = existing
    if old_content == new_content:
        return "unchanged"
    if not dry_run:
        cur.execute(
            "UPDATE skills SET content = %s, version = %s WHERE id = %s",
            (new_content, old_version + 1, _id),
        )
    return "update"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="sync every tool skill")
    group.add_argument("--skill", metavar="SLUG", help="sync a single skill")
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="show what would change without writing to Neon",
    )
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    if args.all:
        slugs = all_skill_slugs()
    else:
        slugs = [args.skill]

    if not slugs:
        eprint("No skills found under /opt/OS/skills/tools/")
        return 1

    ctx = load_context_from_env()

    parse_failures: list[str] = []
    counts = {"insert": 0, "update": 0, "unchanged": 0, "skip": 0}
    changes: list[tuple[str, str]] = []

    try:
        with get_conn(ctx.org_id) as cur:
            for slug in slugs:
                rec = load_skill(slug)
                if not rec.exists:
                    eprint(f"[SKIP] {slug}: SKILL.md missing")
                    counts["skip"] += 1
                    continue
                if rec.parse_error:
                    eprint(f"[WARN] {slug}: {rec.parse_error}")
                    parse_failures.append(slug)
                action = _sync_one(cur, ctx.org_id, rec, args.dry_run)
                counts[action] += 1
                changes.append((slug, action))
                if args.verbose or action in ("insert", "update"):
                    prefix = "[DRY]" if args.dry_run else "[OK] "
                    print(f"{prefix} {action:9s} {slug}")
            if args.dry_run:
                # Rollback any accidental writes (there shouldn't be any)
                cur.execute("ROLLBACK")
    except Exception as e:
        eprint(f"[FATAL] {e}")
        return 1

    print("---")
    print(
        f"Summary: insert={counts['insert']} update={counts['update']} "
        f"unchanged={counts['unchanged']} skip={counts['skip']} "
        f"total={sum(counts.values())}"
    )
    if args.dry_run:
        print("(dry-run — no changes persisted)")
    if parse_failures:
        eprint(f"Parse warnings for: {', '.join(parse_failures)}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
