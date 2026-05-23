"""Reconcile drafts with existing on-disk skill files.

Policy: never destructively overwrite human-authored content unless
``force_rewrite=True``. We detect whether an existing file is a
fresh scaffold (all placeholders) or real human work, and behave
accordingly.

Four scenarios:

  1. No skill on disk → scaffold + write full draft to both files.
  2. Scaffold on disk (placeholder-heavy) → overwrite best_practices.md
     with drafts; only populate SKILL.md body if it is still the
     template stub.
  3. Real human-authored skill on disk → preserve SKILL.md entirely;
     leave best_practices.md alone unless force_rewrite.
  4. force_rewrite=True → overwrite both files from drafts. Caller
     has accepted responsibility for the destructive write.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from .paths import SCAFFOLD_SCRIPT, SKILLS_TOOLS_DIR


SCAFFOLD_MARKER = "[To be filled"


@dataclass
class ReconcilePlan:
    """Describes what the reconciler intends to do on disk."""

    tool_slug: str
    skill_dir: Path
    skill_md: Path
    bp_md: Path
    skill_exists: bool
    is_scaffold: bool
    will_scaffold: bool
    will_write_skill_md: bool
    will_write_bp_md: bool
    preserved_reason: str = ""


def _looks_like_scaffold(bp_text: str) -> bool:
    """Heuristic: count placeholder markers.

    The scaffold writes ``[To be filled ...]`` under every section.
    A real skill rarely has more than zero of these. We treat 5+ as
    "still a scaffold" to be conservative — a human in the middle
    of filling sections one by one will still be protected unless
    all their work is placeholder stubs.
    """
    return bp_text.count(SCAFFOLD_MARKER) >= 5


def plan_reconciliation(
    tool_slug: str,
    *,
    force_rewrite: bool = False,
) -> ReconcilePlan:
    """Decide what to write on disk based on current state."""
    skill_dir = SKILLS_TOOLS_DIR / tool_slug
    skill_md = skill_dir / "SKILL.md"
    bp_md = skill_dir / "references" / "best_practices.md"

    skill_exists = skill_md.is_file()
    is_scaffold = False
    preserved_reason = ""

    if skill_exists and bp_md.is_file():
        try:
            bp_text = bp_md.read_text(encoding="utf-8")
        except OSError:
            bp_text = ""
        is_scaffold = _looks_like_scaffold(bp_text)

    if force_rewrite:
        will_scaffold = not skill_exists
        will_write_skill_md = True
        will_write_bp_md = True
    elif not skill_exists:
        will_scaffold = True
        will_write_skill_md = True
        will_write_bp_md = True
    elif is_scaffold:
        will_scaffold = False
        # Only rewrite SKILL.md body if it is ALSO a scaffold stub.
        # We leave the frontmatter to the research agent's handoff.
        try:
            skill_text = skill_md.read_text(encoding="utf-8")
            # Template leaves characteristic placeholder tokens.
            will_write_skill_md = "[To be filled" in skill_text or "## What This Tool Does" not in skill_text
        except OSError:
            will_write_skill_md = True
        will_write_bp_md = True
    else:
        # Real human-authored skill. Hands off.
        will_scaffold = False
        will_write_skill_md = False
        will_write_bp_md = False
        preserved_reason = (
            "existing skill appears human-authored; refusing to "
            "overwrite without force_rewrite=True"
        )

    return ReconcilePlan(
        tool_slug=tool_slug,
        skill_dir=skill_dir,
        skill_md=skill_md,
        bp_md=bp_md,
        skill_exists=skill_exists,
        is_scaffold=is_scaffold,
        will_scaffold=will_scaffold,
        will_write_skill_md=will_write_skill_md,
        will_write_bp_md=will_write_bp_md,
        preserved_reason=preserved_reason,
    )


def run_scaffold(tool_slug: str) -> tuple[bool, str]:
    """Shell out to the canonical scaffold script.

    Mirrors the Manager's pattern so the scaffold template stays a
    single source of truth.
    """
    if not SCAFFOLD_SCRIPT.is_file():
        return False, f"scaffold script missing at {SCAFFOLD_SCRIPT}"
    try:
        proc = subprocess.run(
            ["python3", str(SCAFFOLD_SCRIPT), tool_slug],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return False, "scaffold timed out"
    except Exception as e:  # defensive — subprocess edge cases
        return False, f"scaffold error: {type(e).__name__}: {e}"
    if proc.returncode != 0:
        return False, f"scaffold rc={proc.returncode}: {proc.stderr.strip()}"
    return True, proc.stdout.strip() or "scaffolded"


def replace_body_preserving_frontmatter(
    path: Path, new_body: str
) -> None:
    """Overwrite the body of a markdown file while keeping its YAML frontmatter.

    Used to rewrite a scaffolded SKILL.md without touching the
    frontmatter that the research agent's handoff just updated
    (source_url, last_researched).
    """
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        path.write_text(new_body, encoding="utf-8")
        return
    lines = text.splitlines()
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        path.write_text(new_body, encoding="utf-8")
        return
    frontmatter = "\n".join(lines[: end_idx + 1]) + "\n"
    path.write_text(frontmatter + "\n" + new_body, encoding="utf-8")
