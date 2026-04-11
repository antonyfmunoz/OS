---
type: codebase-function
file: eos_ai/agent_runtime.py
line: 168
generated: 2026-04-11
---

# AgentRuntime.run

**File:** [[eos_ai-agent_runtime-py]] | **Line:** 168
**Signature:** `run(task_type, prompt, venture_id, skill_name, max_tokens, agent, system_extra, ctx, modality, data_tier, require_realtime, forced_model, task_criticality) → AgentResult`

**Class:** [[eos_ai-agent_runtime-py-AgentRuntime]]

Execute a task with the appropriate model.

Args:
    task_type:    Determines model selection (Haiku vs Sonnet).
    prompt:       The user-facing task description / input.
...

## Calls

- [[eos_ai-agent_runtime-py-RateLimiter-check]]
- [[eos_ai-agent_runtime-py-calculate_cost]]
- [[eos_ai-authority_engine-py-AuthorityEngine-check_can_execute]]
- [[eos_ai-context-py-load_context_from_env]]
- [[eos_ai-model_preferences-py-ModelPreferences-resolve_model]]
- [[eos_ai-skill_registry-py-SkillRegistry-get_relevant_skills]]
- [[eos_ai-skill_registry-py-SkillRegistry-get_skill]]
- [[eos_ai-venture_knowledge-py-VentureKnowledgeBase-get]]
- [[eos_ai-venture_knowledge-py-VentureKnowledgeBase-to_agent_context]]

## Called By

- [[eos_ai-agent_runtime-py-AgentRuntime-run_team_task]]
- [[eos_ai-agent_runtime-py-AgentRuntime-run_with_auto_skill]]
- [[eos_ai-cognitive_loop-py-CognitiveLoop-_enhance_prompt]]
- [[eos_ai-cognitive_loop-py-CognitiveLoop-_verify_output]]
- [[eos_ai-cognitive_loop-py-CognitiveLoop-process_in_order]]
- [[eos_ai-cognitive_loop-py-CognitiveLoop-run]]
- [[eos_ai-evolution_engine-py-EvolutionEngine-propose_new_agent]]
- [[eos_ai-evolution_engine-py-EvolutionEngine-propose_workflow_improvement]]
- [[eos_ai-human_intelligence-py-HumanIntelligenceEngine-adapt_communication]]
- [[eos_ai-human_intelligence-py-HumanIntelligenceEngine-build_profile]]
- [[eos_ai-human_intelligence-py-HumanIntelligenceEngine-get_adapted_message]]
- [[eos_ai-human_intelligence-py-HumanIntelligenceEngine-profile_team_member]]
- [[eos_ai-orchestrator-py-EOSOrchestrator-morning_brief]]
- [[eos_ai-orchestrator-py-EOSOrchestrator-run_morning_cycle]]
- [[eos_ai-orchestrator-py-EOSOrchestrator-write_postmortem]]
- [[eos_ai-portfolio_advisor-py-PortfolioAdvisor-cross_company_intelligence]]
- [[eos_ai-portfolio_advisor-py-PortfolioAdvisor-morning_advisory]]
- [[eos_ai-portfolio_advisor-py-PortfolioAdvisor-run_weekly_review]]
- [[eos_ai-reality_engine-py-RealityIntelligenceEngine-generate_truth_report]]
- [[eos_ai-reality_engine-py-RealityIntelligenceEngine-run_competitor_analysis]]
