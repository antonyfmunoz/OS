---
type: codebase-class
file: eos_ai/memory.py
line: 79
generated: 2026-04-12
---

# AgentMemory

**File:** [[eos_ai-memory-py]] | **Line:** 79

Persistent memory backed by Neon PostgreSQL.

All writes are RLS-scoped to EOS_ORG_ID via the db.get_conn() context
manager. interaction_id is now a UUID string instead of an integer.

## Methods

- [[eos_ai-memory-py-AgentMemory-log]]`(agent_result, venture_id, input_summary, agent, task_type, lead_username) → str` — Called automatically by AgentRuntime.run(). Returns interaction_id (UUID).
- [[eos_ai-memory-py-AgentMemory-log_lead_scored]]`(username, venture_id, comment_text, score, archetype, model_used, input_tokens, output_tokens) → str` — Called by icp_scorer when a lead is qualified and a lead file is created.
- [[eos_ai-memory-py-AgentMemory-_fire_milestone_alert]]`(outcome_count) → None` — Fire a Telegram alert when outcome count hits a milestone (background).
- [[eos_ai-memory-py-AgentMemory-log_outcome]]`(interaction_id, outcome_type, score, notes) → str` — Log an outcome against a prior interaction.
- [[eos_ai-memory-py-AgentMemory-log_standalone_outcome]]`(outcome_type, score, notes, source) → str` — Log an outcome with no linked interaction_id.
- [[eos_ai-memory-py-AgentMemory-log_orphaned_reply]]`(username, outcome_type, score, notes) → str` — Log an outcome with no matching interaction_id.
- [[eos_ai-memory-py-AgentMemory-log_event]]`(org_id, event_type, payload) → str` — Write a structured event to the Neon events table.
- [[eos_ai-memory-py-AgentMemory-get_interaction_for_lead]]`(username, venture_id) → dict | None` — Look up the most recent interaction for a lead by username.
- [[eos_ai-memory-py-AgentMemory-get_recent]]`(venture_id, limit) → list[dict]` — Return recent interactions, optionally filtered by venture.
- [[eos_ai-memory-py-AgentMemory-get_outcomes_for]]`(interaction_id) → list[dict]` — Return all outcomes logged against a specific interaction.
- [[eos_ai-memory-py-AgentMemory-get_orphaned_replies]]`(limit) → list[dict]` — Return unreconciled orphaned replies for manual review.
- [[eos_ai-memory-py-AgentMemory-embed_and_store]]`(interaction_id, text) → bool` — Embed text and persist the vector for interaction_id.
- [[eos_ai-memory-py-AgentMemory-semantic_search]]`(query, limit, min_similarity, venture_id) → list[dict]` — Search past interactions by semantic similarity.
- [[eos_ai-memory-py-AgentMemory-reply_rate_by_skill]]`() → list[dict]` — RLHF aggregate: reply rate per skill, sorted by reply_rate desc.
