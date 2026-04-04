"""Scaffold a new tool skill directory from the canonical template.

Usage:
    python3 scaffold_tool_skill.py <tool_name> [--display-name "Tool Name"]

Creates:
    /opt/OS/skills/tools/{tool_name}/SKILL.md
    /opt/OS/skills/tools/{tool_name}/references/best_practices.md
"""

import re
import sys
from datetime import date
from pathlib import Path

TOOLS_DIR = Path("/opt/OS/skills/tools")
TEMPLATE_DIR = Path("/opt/OS/templates/tools/_template")

# All 19 sections for creator-level best_practices.md
BEST_PRACTICES_SECTIONS = [
    # Tier 1 — Technical Mastery
    "## Authentication",
    "## Core Operations with Exact Signatures",
    "## Pagination Patterns",
    "## Rate Limits",
    "## Error Codes and Recovery",
    "## SDK Idioms",
    "## Anti-Patterns",
    "## Data Model",
    "## Webhooks and Events",
    "## Limits",
    "## Cost Model",
    "## Version Pinning",
    # Tier 2 — Creator Intelligence
    "## Design Intent and Tradeoffs",
    "## Problem-Solution Map and Hidden Capabilities",
    "## Operational Behavior and Edge Cases",
    "## Ecosystem Position and Composition",
    "## Trajectory and Evolution",
    "## Conceptual Model and Solution Recipes",
    "## Industry Expert and Cutting-Edge Usage",
]


def normalize_to_snake_case(name: str) -> str:
    """Convert tool name to snake_case directory name."""
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    return name.strip("_")


def title_case(snake: str) -> str:
    """Convert snake_case to Title Case."""
    return " ".join(w.capitalize() for w in snake.split("_"))


def main() -> None:
    if len(sys.argv) < 2:
        print(
            "Usage: python3 scaffold_tool_skill.py <tool_name> [--display-name 'Tool Name']"
        )
        sys.exit(1)

    raw_name = sys.argv[1]
    tool_id = normalize_to_snake_case(raw_name)

    display_name = title_case(tool_id)
    if "--display-name" in sys.argv:
        idx = sys.argv.index("--display-name")
        if idx + 1 < len(sys.argv):
            display_name = sys.argv[idx + 1]

    tool_dir = TOOLS_DIR / tool_id
    refs_dir = tool_dir / "references"

    if tool_dir.exists():
        print(f"SKIP: {tool_dir} already exists. Use the existing skill.")
        sys.exit(0)

    # Read template
    template_skill = TEMPLATE_DIR / "SKILL.md"
    if not template_skill.exists():
        print(f"ERROR: Template not found at {template_skill}")
        sys.exit(1)

    skill_content = template_skill.read_text()
    today = date.today().isoformat()

    # Replace placeholders
    skill_content = skill_content.replace("[tool-name]", tool_id)
    skill_content = skill_content.replace("[Tool Name]", display_name)
    skill_content = skill_content.replace("[Tool]", display_name)
    skill_content = skill_content.replace("[Official documentation URL]", "")
    skill_content = skill_content.replace("[YYYY-MM-DD]", today)

    # Add api_version, sdk_version, speed_category to frontmatter
    skill_content = skill_content.replace(
        "instantiated_from: templates/tools/_template/",
        f'instantiated_from: templates/tools/_template/\napi_version: ""\nsdk_version: ""\nspeed_category: ""',
    )

    # Create best_practices.md with all 19 section headers
    bp_lines = [
        f"# {display_name} — Creator-Level Best Practices",
        f"Source: ",
        f"API Version: ",
        f"SDK Version: ",
        f"Last Researched: {today}",
        "",
        "---",
        "",
        "# Tier 1 — Technical Mastery",
        "",
    ]
    for section in BEST_PRACTICES_SECTIONS[:12]:
        bp_lines.append(section)
        bp_lines.append("[To be filled from official documentation]")
        bp_lines.append("")

    bp_lines.append("---")
    bp_lines.append("")
    bp_lines.append("# Tier 2 — Creator Intelligence")
    bp_lines.append("")

    for section in BEST_PRACTICES_SECTIONS[12:]:
        bp_lines.append(section)
        bp_lines.append(
            "[To be filled from creator content, expert blogs, and frontier research]"
        )
        bp_lines.append("")

    bp_lines.append("---")
    bp_lines.append("")
    bp_lines.append("## EOS Usage Patterns")
    bp_lines.append("[How EOS specifically uses this tool. Updated from production.]")
    bp_lines.append("")
    bp_lines.append("## Gotchas")
    bp_lines.append("[Real failures encountered. This section compounds over time.]")
    bp_lines.append("")

    # Write files
    refs_dir.mkdir(parents=True, exist_ok=True)
    (tool_dir / "SKILL.md").write_text(skill_content)
    (refs_dir / "best_practices.md").write_text("\n".join(bp_lines))

    print(f"CREATED: {tool_dir}/SKILL.md")
    print(f"CREATED: {refs_dir}/best_practices.md")
    print(f"")
    print(f"Next steps:")
    print(f"  1. Read references/research_protocol.md for the 19-section standard")
    print(f"  2. Research {display_name} official docs exhaustively")
    print(f"  3. Fill SKILL.md with tool identity, auth, quick reference")
    print(f"  4. Fill best_practices.md — all 19 sections")
    print(f"  5. Add action-verb trigger description to SKILL.md frontmatter")
    print(f"  6. Sync to Neon")
    print(f"  7. Run verification")


if __name__ == "__main__":
    main()
