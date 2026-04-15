---
type: codebase-function
file: eos_ai/cognitive_loop.py
line: 268
generated: 2026-04-12
---

# CognitiveLoop.run

**File:** [[eos_ai-cognitive_loop-py]] | **Line:** 268
**Signature:** `run(input, session_id, cm, agent, task_type, venture_id, skill_name, workflow_id, channel, max_iterations) → CognitiveResult`

**Class:** [[eos_ai-cognitive_loop-py-CognitiveLoop]]

*No docstring.*

## Calls

- [[eos_ai-agent_runtime-py-AgentRuntime-run]]
- [[eos_ai-authority_engine-py-AuthorityEngine-check_can_execute]]
- [[eos_ai-authority_engine-py-AuthorityEngine-queue_for_approval]]
- [[eos_ai-cognitive_loop-py-CognitiveLoop-_enhance_prompt]]
- [[eos_ai-cognitive_loop-py-CognitiveLoop-_infer_action_type]]
- [[eos_ai-cognitive_loop-py-CognitiveLoop-_maybe_compact]]
- [[eos_ai-cognitive_loop-py-CognitiveLoop-_reflect]]
- [[eos_ai-cognitive_loop-py-CognitiveLoop-_verify_output]]
- [[eos_ai-cognitive_loop-py-_format_intent_context]]
- [[eos_ai-cognitive_loop-py-detect_intent_and_inject]]
- [[eos_ai-cognitive_loop-py-format_response_footer]]
- [[eos_ai-memory-py-AgentMemory-log_event]]
- [[eos_ai-memory-py-AgentMemory-log_outcome]]
- [[eos_ai-memory-py-AgentMemory-semantic_search]]
- [[eos_ai-memory-py-ConversationMemory-format_channel_history_for_prompt]]
- [[eos_ai-memory-py-ConversationMemory-format_session_for_prompt]]
- [[eos_ai-venture_knowledge-py-VentureKnowledgeBase-get]]
- [[eos_ai-venture_knowledge-py-VentureKnowledgeBase-to_agent_context]]

## Called By

- [[eos_ai-cognitive_loop-py-CognitiveLoop-_enhance_prompt]]
- [[eos_ai-cognitive_loop-py-CognitiveLoop-_verify_output]]
- [[eos_ai-cognitive_loop-py-CognitiveLoop-process_in_order]]
- [[eos_ai-evolution_engine-py-EvolutionEngine-propose_new_agent]]
- [[eos_ai-evolution_engine-py-EvolutionEngine-propose_workflow_improvement]]
- [[eos_ai-onboarding_backfill-py-OnboardingBackfill-_build_knowledge_base]]
- [[eos_ai-reality_engine-py-RealityIntelligenceEngine-generate_truth_report]]
- [[eos_ai-reality_engine-py-RealityIntelligenceEngine-run_competitor_analysis]]
- [[eos_ai-reality_engine-py-RealityIntelligenceEngine-scan_market_signals]]
- [[eos_ai-research_engine-py-ResearchEngine-_detect_foundational_gaps]]
- [[eos_ai-research_engine-py-ResearchEngine-_parse_model_costs]]
- [[eos_ai-research_engine-py-ResearchEngine-detect_knowledge_gaps]]
- [[eos_ai-research_engine-py-ResearchEngine-research_topic]]
- [[eos_ai-research_engine-py-ResearchEngine-run_domain_update_cycle]]
- [[eos_ai-research_engine-py-ResearchEngine-scan_ai_landscape]]
- [[eos_ai-strategy_engine-py-DecisionEngine-evaluate]]
- [[eos_ai-strategy_engine-py-StrategyEngine-analyze_company_position]]
- [[eos_ai-strategy_engine-py-StrategyEngine-analyze_portfolio_strategy]]
- [[eos_ai-strategy_engine-py-StrategyEngine-run_decision_analysis]]
- [[eos_ai-user_model-py-UserModel-build_communication_profile]]
