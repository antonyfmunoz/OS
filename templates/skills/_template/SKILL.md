---
name: [skill-name]
description: "[When Claude should auto-invoke this skill. Be specific about the trigger.]"
allowed-tools: "Read, Bash"
version: 1.0
instantiated_from: templates/skills/_template/
---

# Skill: [Name]
<!--
SKILL TEMPLATE v1.0
Follows Anthropic Agent Skills open standard.
Progressive disclosure: only name/description loads at startup.
Full content on invocation.
Move detailed docs to references/.
Move executable code to scripts/.
-->

## Purpose
[One sentence starting with a verb.]

## Outcome
[What a successful execution produces.
Specific about deliverable format.]

## Decision Criteria
[When to run this skill.
When NOT to run it.]

## Execution Steps
[Numbered. Specific. Ordered.
Reference scripts/ files if needed:
  python3 $SKILL_DIR/scripts/script.py]

## Failure Modes
[Specific failure patterns. Not warnings.]

## Measurement
[How to know it worked.
What metric improves this skill over time.]

See references/ for detailed documentation.
