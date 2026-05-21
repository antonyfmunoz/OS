#!/usr/bin/env python3
"""Replace hardcoded 'Antony' founder references with generic 'the founder' in skills."""
import os
import re

SKILLS_DIR = "/opt/OS/skills"
FOUNDER_BIS = "!" + "`python3 /opt/OS/scripts/bis_context.py --founder`"

updated = 0
for root, dirs, files in sorted(os.walk(SKILLS_DIR)):
    if "SKILL.md" not in files:
        continue
    path = os.path.join(root, "SKILL.md")
    content = open(path).read()

    if not re.search(r"(?i)\bantony\b", content):
        continue

    original = content

    # Replace founder name references (order matters — longer patterns first)
    content = content.replace("Antony Munoz", "the founder")
    content = content.replace("ANTONY", "FOUNDER")
    content = content.replace("Antony's", "the founder's")
    content = content.replace("Antony can ", "The founder can ")
    content = content.replace("Antony will ", "the founder will ")
    content = content.replace("Antony must ", "the founder must ")
    content = content.replace("Antony has ", "the founder has ")
    content = content.replace("Antony wants ", "the founder wants ")
    content = content.replace("Antony marks ", "the founder marks ")
    content = content.replace("for Antony", "for the founder")
    content = content.replace("to Antony", "to the founder")
    content = content.replace("like Antony", "like the founder")
    content = content.replace("## the founder's", "## The Founder's")
    content = content.replace("[the founder/DEX]", "[Founder/DEX]")
    # Remaining standalone Antony
    content = re.sub(r"\bAntony\b", "the founder", content)

    # Ensure BIS block for those that don't have one
    if "bis_context.py" not in content:
        parts = content.split("---", 2)
        if len(parts) >= 3:
            content = "---" + parts[1] + "---\n\n" + FOUNDER_BIS + "\n" + parts[2]

    if content != original:
        open(path, "w").write(content)
        name = os.path.relpath(root, SKILLS_DIR)
        updated += 1
        print(f"  Updated: {name}")

print(f"\nUpdated: {updated}")
