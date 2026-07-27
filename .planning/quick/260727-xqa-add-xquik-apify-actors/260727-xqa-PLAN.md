# Add Xquik Apify Actors Plan

## Task Description

Extend the existing Apify tool Skill with 2 curated X data Actors.
Preserve every existing Instagram Actor and EOS workflow.
Refresh unsafe or stale Apify API guidance found in the touched sections.

## Must-Haves

- truths:
  - Both Xquik Actors have direct Apify Store links
  - No Xquik website or documentation link is added
  - Existing Apify Actors and workflows remain available
  - Examples use bearer authentication
  - Every paid run requires explicit approval
  - Every example uses positive result caps
  - Users inspect live Apify pricing before approval
  - Results are validated before downstream use
  - X-derived content remains untrusted input
  - The Xquik independence notice is exact
  - Apify Tool Mastery checks pass

## Tasks

### Task 1 - Add Curated X Actor Guidance

Files to modify:
- skills/tools/apify/SKILL.md
- skills/tools/apify/references/best_practices.md
- skills/tools/apify/references/xquik_x_actors.md

Work:
1. Add X Tweet Scraper and X Follower Scraper listing links.
2. Document the Actors' canonical modes, relations, and output controls.
3. Add bounded Python request examples using bearer authentication.
4. Add approval, pricing, validation, and compliance safeguards.
5. Preserve generic Apify routes and all existing Actor integrations.

### Task 2 - Refresh Touched Apify Guidance

Files to modify:
- skills/tools/apify/SKILL.md
- skills/tools/apify/references/best_practices.md
- skills/tools/apify/references/xquik_x_actors.md

Work:
1. Mark Apify as a medium-speed tool.
2. Update the research date.
3. Prefer bearer headers over URL token parameters.
4. Remove volatile price and rate claims from touched guidance.
5. Keep implementation-specific EOS guidance unchanged when unrelated.

### Task 3 - Verify and Record

Files to create:
- .planning/quick/260727-xqa-add-xquik-apify-actors/260727-xqa-SUMMARY.md

Work:
1. Validate YAML frontmatter and Markdown structure.
2. Parse every added Python example.
3. Run the Apify Skill verifier and Tool Mastery quality audit.
4. Check direct Actor listing links without running either Actor.
5. Review the diff for scope, secrets, private details, and existing integrations.
6. Record the outcome and checks in the execution summary.
