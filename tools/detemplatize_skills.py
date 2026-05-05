#!/usr/bin/env python3
"""
Removes hardcoded venture data from all skills.
Replaces with BIS injection !`command` block.
Replaces inline hardcoded references with generic placeholders.
Run once. Idempotent.
"""

import os
import re

SKILLS_DIR = "/opt/OS/skills"

BIS_BLOCK = """!`python3 /opt/OS/scripts/bis_context.py --fields name,icp,offer,stage,primary_channel,binding_constraint,north_star`"""

# Patterns to detect hardcoded data (case-sensitive where needed)
HARDCODED_PATTERNS = [
    (r"Men 18-25", "the venture ICP"),
    (r"men 18-25", "the venture ICP"),
    (r"men aged 18-25", "the venture ICP"),
    (r"Initiate Arena at \$750", "the active offer at its price point"),
    (r"Initiate Arena", "the active offer"),
    (r"initiate arena", "the active offer"),
    (r"\$750", "the offer price"),
]

# Patterns for venture IDs (only in body, not frontmatter)
VENTURE_ID_PATTERNS = [
    (r"lyfe_institute", "the active venture"),
    (r"Lyfe Institute", "the active venture"),
    (r"empyrean_creative", "the active venture"),
    (r"Empyrean Creative", "the active venture"),
    (r"personal_brand", "the active venture"),
]


def has_hardcoded(content: str) -> bool:
    """Check if content has any hardcoded venture data."""
    for pattern, _ in HARDCODED_PATTERNS + VENTURE_ID_PATTERNS:
        if re.search(pattern, content):
            return True
    return False


def has_bis_injection(content: str) -> bool:
    """Check if already has the new-style BIS injection."""
    return "bis_context.py" in content


def has_old_bis(content: str) -> bool:
    """Check if has old-style broken BIS injection."""
    return "VENTURES_JSON" in content or "ACTIVE_VENTURE_ID" in content


def replace_old_bis_block(content: str) -> str:
    """Replace old-style broken !` command blocks with new bis_context.py call."""
    # Match !`python3 -c "..." blocks that reference context/ventures
    pattern = r'!`python3 -c "[^`]*(?:load_context_from_env|VENTURES_JSON|ACTIVE_VENTURE_ID)[^`]*"`'
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(pattern, BIS_BLOCK, content, flags=re.DOTALL)
    return content


def replace_hardcoded_in_body(content: str) -> str:
    """Replace hardcoded venture data in the body (not frontmatter)."""
    # Split frontmatter from body
    parts = content.split("---", 2)
    if len(parts) >= 3:
        frontmatter = "---" + parts[1] + "---"
        body = parts[2]
    else:
        frontmatter = ""
        body = content

    # Replace hardcoded patterns in body
    for pattern, replacement in HARDCODED_PATTERNS:
        body = re.sub(pattern, replacement, body)

    for pattern, replacement in VENTURE_ID_PATTERNS:
        body = re.sub(pattern, replacement, body)

    return frontmatter + body


def update_description(content: str) -> str:
    """Replace hardcoded data in frontmatter description field."""
    parts = content.split("---", 2)
    if len(parts) < 3:
        return content

    frontmatter = parts[1]

    # Replace in description field only
    for pattern, replacement in HARDCODED_PATTERNS:
        frontmatter = re.sub(pattern, replacement, frontmatter)

    for pattern, replacement in VENTURE_ID_PATTERNS:
        frontmatter = re.sub(pattern, replacement, frontmatter)

    return "---" + frontmatter + "---" + parts[2]


def ensure_bis_block(content: str) -> str:
    """Ensure the BIS injection block exists after frontmatter."""
    if has_bis_injection(content):
        return content

    # Replace old-style BIS if present
    if has_old_bis(content):
        content = replace_old_bis_block(content)
        if has_bis_injection(content):
            return content

    # Insert after frontmatter
    parts = content.split("---", 2)
    if len(parts) >= 3:
        # Check if there's already a !` block right after frontmatter
        body = parts[2]
        if body.lstrip().startswith("!`"):
            # Replace the existing !` block
            body_lines = body.lstrip().split("\n")
            # Find end of !` block
            in_block = False
            end_idx = 0
            for i, line in enumerate(body_lines):
                if line.strip().startswith("!`"):
                    in_block = True
                if in_block and "`" in line and i > 0:
                    end_idx = i + 1
                    break
                if in_block and line.strip().endswith('"`'):
                    end_idx = i + 1
                    break
            if end_idx > 0:
                remaining = "\n".join(body_lines[end_idx:])
                content = "---" + parts[1] + "---\n\n" + BIS_BLOCK + "\n" + remaining
            else:
                content = "---" + parts[1] + "---\n\n" + BIS_BLOCK + "\n" + body
        else:
            content = "---" + parts[1] + "---\n\n" + BIS_BLOCK + "\n" + body
    else:
        content = BIS_BLOCK + "\n\n" + content

    return content


def process_skill(path: str) -> tuple[bool, str]:
    """Process a single skill file. Returns (changed, reason)."""
    content = open(path).read()

    if not has_hardcoded(content) and not has_old_bis(content):
        return False, "no hardcoded data"

    if has_bis_injection(content) and not has_hardcoded(content):
        return False, "already detemplatized"

    original = content

    # Step 1: Update description in frontmatter
    content = update_description(content)

    # Step 2: Replace hardcoded data in body
    content = replace_hardcoded_in_body(content)

    # Step 3: Ensure BIS injection block exists
    content = ensure_bis_block(content)

    if content == original:
        return False, "no changes needed"

    open(path, "w").write(content)
    return True, "updated"


def main() -> None:
    updated = 0
    skipped = 0
    errors = 0

    for root, dirs, files in sorted(os.walk(SKILLS_DIR)):
        if "SKILL.md" not in files:
            continue
        path = os.path.join(root, "SKILL.md")
        name = os.path.relpath(root, SKILLS_DIR)
        try:
            changed, reason = process_skill(path)
            if changed:
                updated += 1
                print(f"  Updated: {name}")
            else:
                skipped += 1
        except Exception as e:
            errors += 1
            print(f"  Error: {name}: {e}")

    print()
    print(f"Updated: {updated}")
    print(f"Skipped: {skipped}")
    print(f"Errors: {errors}")


if __name__ == "__main__":
    main()
