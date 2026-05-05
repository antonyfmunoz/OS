---
type: codebase-class
file: eos_ai/research_engine.py
line: 45
generated: 2026-04-12
---

# ResearchEngine

**File:** [[eos_ai-research_engine-py]] | **Line:** 45

Autonomous knowledge gap detection and research.

Finds gaps in interaction quality by querying Neon (authoritative source —
fallback), researches them from first principles, and stores findings
as permanent skills in the Neon skills table.

## Methods

- [[eos_ai-research_engine-py-ResearchEngine-__init__]]`(ctx)` — 
- [[eos_ai-research_engine-py-ResearchEngine-detect_knowledge_gaps]]`() → list[str]` — Query interaction history for patterns where deeper knowledge would
- [[eos_ai-research_engine-py-ResearchEngine-_query_neon_interactions]]`(cutoff) → list[dict]` — Query Neon interactions table. Returns [] on any failure.
- [[eos_ai-research_engine-py-ResearchEngine-_query_local_interactions]]`(cutoff) → list[dict]` — Retired: memory.db is no longer active. Returns empty list.
- [[eos_ai-research_engine-py-ResearchEngine-_detect_foundational_gaps]]`() → list[str]` — When no interaction history exists, identify foundational knowledge gaps
- [[eos_ai-research_engine-py-ResearchEngine-research_topic]]`(topic, venture_id) → dict` — Horizontal research on a topic using live web sources via Scrapling,
- [[eos_ai-research_engine-py-ResearchEngine-store_knowledge]]`(topic, knowledge_object, venture_id) → bool` — Write a research result to the Neon skills table as a permanent
- [[eos_ai-research_engine-py-ResearchEngine-run_gap_fill_cycle]]`() → dict` — Full weekly gap-fill cycle: Detect → Research → Store.
- [[eos_ai-research_engine-py-ResearchEngine-scan_ai_landscape]]`() → dict` — Horizontal scan of the current AI landscape.
- [[eos_ai-research_engine-py-ResearchEngine-_parse_model_costs]]`(scan_text) → dict` — Extract model pricing from AI landscape scan text.
- [[eos_ai-research_engine-py-ResearchEngine-run_domain_update_cycle]]`() → dict` — Weekly domain update cycle. Horizontal-then-vertical methodology:
