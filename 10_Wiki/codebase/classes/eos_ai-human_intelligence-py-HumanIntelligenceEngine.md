---
type: codebase-class
file: eos_ai/human_intelligence.py
line: 47
generated: 2026-04-12
---

# HumanIntelligenceEngine

**File:** [[eos_ai-human_intelligence-py]] | **Line:** 47

*No docstring.*

## Methods

- [[eos_ai-human_intelligence-py-HumanIntelligenceEngine-__init__]]`(ctx) → None` — 
- [[eos_ai-human_intelligence-py-HumanIntelligenceEngine-_find_lead_file]]`(username) → str | None` — Find the most recent lead file for a username.
- [[eos_ai-human_intelligence-py-HumanIntelligenceEngine-_all_lead_files]]`() → list[str]` — Return all lead files, excluding the index.
- [[eos_ai-human_intelligence-py-HumanIntelligenceEngine-_parse_lead_file]]`(filepath) → dict` — Parse frontmatter + body of a lead .md file.
- [[eos_ai-human_intelligence-py-HumanIntelligenceEngine-_store_profile]]`(username, venture_id_slug, profile) → None` — Upsert profile into Neon human_profiles. venture_id_slug is a string like 'lyfe_
- [[eos_ai-human_intelligence-py-HumanIntelligenceEngine-_fetch_profile_row]]`(username, venture_id) → dict | None` — 
- [[eos_ai-human_intelligence-py-HumanIntelligenceEngine-_is_stale]]`(updated_at) → bool` — 
- [[eos_ai-human_intelligence-py-HumanIntelligenceEngine-_build_profile_prompt]]`(lead) → str` — 
- [[eos_ai-human_intelligence-py-HumanIntelligenceEngine-build_profile]]`(username) → dict` — Read the lead file, synthesize via AI, store in memory.db, return profile.
- [[eos_ai-human_intelligence-py-HumanIntelligenceEngine-get_profile]]`(username, venture_id) → dict | None` — Return stored profile dict, or None if not yet built.
- [[eos_ai-human_intelligence-py-HumanIntelligenceEngine-get_adapted_message]]`(username, base_message) → str` — Adapt a base outreach message to this specific person's communication
- [[eos_ai-human_intelligence-py-HumanIntelligenceEngine-run_profile_cycle]]`() → dict` — Loop all lead files. Build or refresh profiles older than 48 hours.
- [[eos_ai-human_intelligence-py-HumanIntelligenceEngine-profile_all_crm_leads]]`() → dict` — Alias for run_profile_cycle. Profiles all leads in 03_CRM/Leads/,
- [[eos_ai-human_intelligence-py-HumanIntelligenceEngine-profile_team_member]]`(user_id, org_id) → dict` — Profile a team member from their org_members entry and interaction
- [[eos_ai-human_intelligence-py-HumanIntelligenceEngine-adapt_communication]]`(target_human, human_type, message, context) → str` — Adapt a message to this specific human's style and role context.
- [[eos_ai-human_intelligence-py-HumanIntelligenceEngine-get_relationship_context]]`(username) → str` — Returns a brief for any human in the system:
