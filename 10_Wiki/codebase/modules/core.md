---
type: codebase-module
generated: 2026-04-12
---

# core/

**Files:** 73 | **Lines:** 21,799 | **Classes:** 111 | **Functions:** 626

## Entry Points

- [[core-control_plane-py]]
- [[core-optimizer-py]]
- [[core-security-cli-py]]
- [[core-tool_mastery_author_agent-__main__-py]]
- [[core-tool_mastery_author_agent-cli-py]]
- [[core-tool_mastery_research_agent-__main__-py]]
- [[core-tool_mastery_research_agent-cli-py]]

## All Files

- [[core-action_system-actions-py]] (84 lines) — Action object — the canonical unit of control in EOS.
- [[core-action_system-control_plane-py]] (273 lines) — Control Plane — the public entry point for the EOS Action Sy
- [[core-action_system-deferred-py]] (97 lines) — Durable persistence for deferred actions.
- [[core-action_system-deferred_status-py]] (242 lines) — Lightweight status tracking for deferred actions.
- [[core-action_system-executor-py]] (114 lines) — Action executors — dispatch by action.type.
- [[core-action_system-idempotency-py]] (296 lines) — Filesystem sentinel store for Control Plane idempotency.
- [[core-action_system-logging-py]] (73 lines) — Append-only JSONL loggers for execution and decision records
- [[core-action_system-notifier-py]] (120 lines) — Notifier foundation for deferred actions.
- [[core-action_system-policy-py]] (165 lines) — Policy bridge between the Control Plane and `eos_ai.authorit
- [[core-action_system-tme-py]] (78 lines) — Tool Mastery Engine / Manager integration for the Control Pl
- [[core-action_system-validator-py]] (188 lines) — Validation + approval rules for Actions.
- [[core-advisor-py]] (864 lines) — advisor.py — Conditional intelligence layer for the EOS AI O
- [[core-agent_harness-py]] (741 lines) — agent_harness.py — Unified execution surface for every agent
- [[core-capability-py]] (511 lines) — capability.py — Permission + risk matrix for the unified EOS
- [[core-control_plane-py]] (322 lines) *[entry]* — control_plane.py — Unified control plane composing the orche
- [[core-coord_assignment-py]] (405 lines) — Semantic Space v1.1 — Coordinate Assignment
- [[core-environment-py]] (535 lines) — environment.py — Execution environment model for the EOS AI 
- [[core-execution_contract-py]] (385 lines) — ExecutionContract — unified execution entry point for all EO
- [[core-observability-py]] (408 lines) — observability.py — Read-only view over the EOS AI OS.
- [[core-optimizer-py]] (652 lines) *[entry]* — optimizer.py — Feedback loop for the EOS AI OS.
- [[core-orchestrator-decisions-py]] (159 lines) — Decision helpers for signal handler workflows.
- [[core-orchestrator-handlers-py]] (322 lines) — Signal handler workflows.
- [[core-orchestrator-loop-py]] (451 lines) — Autonomous loop — deterministic orchestration cycle.
- [[core-orchestrator-orchestrator-py]] (200 lines) — Orchestrator — execution coordinator for named workflows.
- [[core-orchestrator-pipeline-py]] (277 lines) — Pipeline — sequential composition of Control Plane actions.
- [[core-orchestrator-signals-py]] (209 lines) — Signals — filesystem-backed event layer for the orchestrator
- [[core-orchestrator-steps-py]] (211 lines) — Reusable orchestrator step helpers.
- [[core-orchestrator-workflows-py]] (125 lines) — Workflow registry — wires existing Control Plane workflows i
- [[core-persistent_agents-py]] (566 lines) — persistent_agents.py — Long-running stateful agents in the E
- [[core-security-approval-py]] (415 lines) — approval.py — Approval queue for high-risk actions.
- [[core-security-audit-py]] (272 lines) — audit.py — Append-only audit log with hash-chain integrity.
- [[core-security-cli-py]] (288 lines) *[entry]* — cli.py — Operator CLI for the EOS security layer.
- [[core-security-context-py]] (642 lines) — context.py — SecurityContext facade.
- [[core-security-environments-py]] (227 lines) — environments.py — Environment policy layer for the security 
- [[core-security-execution-py]] (331 lines) — execution.py — Restricted execution contexts for agent workl
- [[core-security-identity-py]] (401 lines) — identity.py — User model and token-based authentication.
- [[core-security-rbac-py]] (304 lines) — rbac.py — Role-based access control on top of core.capabilit
- [[core-semantic_space-py]] (499 lines) — Semantic Space v1.2 — Query Projection, Region Search, Graph
- [[core-tool_mastery_author_agent-__main__-py]] (5 lines) *[entry]* — 
- [[core-tool_mastery_author_agent-agent-py]] (189 lines) — Author Agent orchestrator.
- [[core-tool_mastery_author_agent-cli-py]] (133 lines) *[entry]* — CLI entry for the Tool Mastery Author Agent.
- [[core-tool_mastery_author_agent-draft-py]] (452 lines) — Draft authored section content from SectionEvidence.
- [[core-tool_mastery_author_agent-loader-py]] (219 lines) — Research artifact loader.
- [[core-tool_mastery_author_agent-mapping-py]] (610 lines) — Section → raw-capture evidence mapping.
- [[core-tool_mastery_author_agent-models-py]] (141 lines) — Data types for the Tool Mastery Author Agent.
- [[core-tool_mastery_author_agent-paths-py]] (26 lines) — Path resolution for the Tool Mastery Author Agent.
- [[core-tool_mastery_author_agent-reconcile-py]] (172 lines) — Reconcile drafts with existing on-disk skill files.
- [[core-tool_mastery_author_agent-verify-py]] (77 lines) — Run verify_tool_skill.py against an authored tool.
- [[core-tool_mastery_manager-backlog-py]] (189 lines) — Backlog / bootstrap flow.
- [[core-tool_mastery_manager-coverage-py]] (120 lines) — Unified coverage evaluator for the Tool Mastery Manager.
- [[core-tool_mastery_manager-discovery-py]] (333 lines) — Tool discovery for the Tool Mastery Manager.
- [[core-tool_mastery_manager-ensure-py]] (173 lines) — ensure_mastery — the primary entry point of the Tool Mastery
- [[core-tool_mastery_manager-maintenance-py]] (61 lines) — Maintenance flows for the Tool Mastery Manager.
- [[core-tool_mastery_manager-models-py]] (122 lines) — Data types for the Tool Mastery Manager.
- [[core-tool_mastery_manager-paths-py]] (26 lines) — Path resolution for the Tool Mastery Manager.
- [[core-tool_mastery_research_agent-__main__-py]] (5 lines) *[entry]* — 
- [[core-tool_mastery_research_agent-agent-py]] (199 lines) — Research Agent orchestrator.
- [[core-tool_mastery_research_agent-artifact-py]] (609 lines) — Artifact writer for the Tool Mastery Research Agent.
- [[core-tool_mastery_research_agent-candidate_approval-py]] (272 lines) — Candidate approval gate for search-based source discovery.
- [[core-tool_mastery_research_agent-cli-py]] (250 lines) *[entry]* — CLI entry for the Tool Mastery Research Agent.
- [[core-tool_mastery_research_agent-docs_site_discovery-py]] (610 lines) — Docs site discovery for the Tool Mastery Research Agent.
- [[core-tool_mastery_research_agent-extraction-py]] (1266 lines) — Structured knowledge extraction for the Tool Mastery Researc
- [[core-tool_mastery_research_agent-fetcher-py]] (164 lines) — Fetcher for the Tool Mastery Research Agent.
- [[core-tool_mastery_research_agent-github_extractor-py]] (349 lines) — GitHub repo extractor for the Tool Mastery Research Agent.
- [[core-tool_mastery_research_agent-handoff-py]] (124 lines) — Safe metadata handoff for the Tool Mastery Research Agent.
- [[core-tool_mastery_research_agent-headless_fetcher-py]] (367 lines) — Headless rendering fetch path for the Tool Mastery Research 
- [[core-tool_mastery_research_agent-models-py]] (210 lines) — Data types for the Tool Mastery Research Agent.
- [[core-tool_mastery_research_agent-paths-py]] (23 lines) — Path resolution for the Tool Mastery Research Agent.
- [[core-tool_mastery_research_agent-search_discovery-py]] (354 lines) — Deterministic search candidate generator for the Research Ag
- [[core-tool_mastery_research_agent-source_discovery-py]] (363 lines) — Source discovery for the Tool Mastery Research Agent.
- [[core-tool_mastery_research_agent-source_quality-py]] (371 lines) — Source quality scoring for the Tool Mastery Research Agent.
- [[core-tool_mastery_research_agent-structured_crawl-py]] (437 lines) — Structured crawl expansion for the Tool Mastery Research Age
- [[core-wiki_navigation-py]] (326 lines) — Wiki Navigation Layer — bridges graph nodes and Obsidian wik
