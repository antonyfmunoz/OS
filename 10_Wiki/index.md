---
type: wiki_index
updated: 2026-04-05
---

# Wiki Index

Entry point for the LLM-maintained knowledge graph.
Retrieval strategy: index -> page -> deep dive into RAW if needed.

## Concepts

Ideas, frameworks, and patterns that recur across the business.

- [[icp-signals]] — ICP signal detection patterns and psychology
- [[memory-pipeline]] — The conversation-to-summary-to-wiki knowledge extraction pipeline in EOS
- [[eos-product-mode]] — Explains the target behavior and implementation for Product Mode in EOS, focusing on clean SaaS output and suppression of internal language.
- [[eos-builder-mode]] — Describes the target behavior for Builder Mode in EOS, aiming for an AI operator/dev cofounder feel with system/debug references visible.
- [[eos-auto-clear-mechanism]] — Documents the flow-triggered, message-counting mechanism for auto-clearing sessions in EOS, highlighting its efficiency benefits.
- [[claude-code-session]] — Describes the environment for interactive coding and problem-solving.
- [[json-execution-plan]] — Explains the structure and purpose of a JSON object describing a multi-step plan for the assistant to execute.
- [[execution-class-types]] — Defines the categories of execution classes like `llm_call`, `side_effect`, and `pure` used to characterize operations in an execution plan.
- [[llm-operations]] — Details the available primitive operations (e.g., classify_intent, short_response, shell_command) that can be included in an execution plan.
- [[execution-class]] — Describes the categorization of operations into 'llm_call', 'side_effect', or 'pure' based on their nature and impact.
- [[test-step-statuses]] — Explains the concept of "test step statuses" as checking or reporting the pass/fail state of individual steps in a test run.
- [[execution-class-categories]] — Explains the different categories for operations such such as llm_call, side_effect, and pure.
- [[available-ai-operations]] — Documents the standard set of operations an AI agent can utilize for task execution.
- [[ai-execution-system]] — The system responsible for executing AI-driven plans based on objectives and capabilities.
- [[execution-plan]] — A structured set of steps designed to achieve a specific objective within an AI execution system.
- [[system-health-inspection]] — The process of evaluating and reporting the operational status and resource utilization of a system.
- [[session-state-persistence]] — Explains how task context and session state are managed, particularly the lack of persistence across new sessions.
- [[classify-intent]] — Describes the `classify_intent` function or module and its role within the codebase.
- [[plan-review]] — Details the process of evaluating an AI execution plan for correctness, efficiency, and adherence to objectives.
- [[shell-command-operation]] — Defines the 'shell_command' operation, a fundamental capability allowing AI agents to execute shell commands.
- [[system-health-check]] — Details standard procedures and common commands for assessing system status.
- [[plan-reviewer]] — A role or persona within the AI execution system responsible for evaluating plans for issues, suggestions, and adherence to constraints.
- [[objective-interpretation-logic]] — Describes how the assistant interprets and responds to different types of objectives, especially vague or invalid ones.
- [[testing-types]] — Defines and differentiates between unit, integration, and end-to-end testing, as explained by the assistant.
- [[llm-call-execution-class]] — Defines the 'llm_call' execution class, indicating that a step in an execution plan involves an interaction with a large language model.
- [[dry-run-mode]] — A mode of operation where a plan is simulated or acknowledged without taking any side-effecting actions.
- [[llm-call]] — An operation within an execution plan that involves making a call to a Large Language Model.
- [[execution-plan-review]] — A guide on the process and criteria for reviewing AI execution plans to identify issues and suggest improvements.
- [[input-length-check-for-summarization]] — A discussion of the importance and implementation of input length checks for summarization tasks to improve quality and efficiency.
- [[execution-plan-generation]] — Covers the process and requirements for generating structured execution plans based on objectives and specified constraints.
- [[dry-run-constraint]] — Explains the 'dry_run' constraint, its implications for execution, and the expected system behavior of generating plans without side effects.
- [[brief-intent]] — An existing intent in the gateway classifier, triggered by keywords like 'summary', designed for system status updates rather than content summarization.
- [[intent-gap]] — A common issue where user input is misrouted due to an ambiguity or absence in the intent classification system.
- [[input-validation-for-llm-interactions]] — Explains the importance of providing clear, contextual, and complete input for effective interaction with LLM-based assistants, highlighting common rejection scenarios.
- [[umh-runtime-engine-system-health-error]] — Covers the recurring error related to the 'umh.runtime_engine.system_health' module, including its symptoms and potential causes.
- [[pending-tasks]] — Describes the system's mechanism for tracking and managing pending tasks that require attention or resolution.
- [[ai-execution-system-failure-analysis]] — Covers the process and methods for analyzing failures within an AI execution system.
- [[error-classification-categories]] — Defines and describes standard categories for classifying errors in an AI execution system, such as input_error, timeout, and internal_error.
- [[root-cause-analysis-template]] — Details the structured output required for root cause analysis, including root_cause, failure_category, and suggested_fix fields.
- [[ai-execution-plan]] — A structured plan defining steps and operations for an AI execution system.
- [[plan-reviewer-role]] — The role responsible for evaluating AI execution plans for issues and suggestions.
- [[llm-call-operation]] — A type of operation within an execution plan that involves making a call to a Large Language Model.
- [[failure-analysis-methodology]] — Details the systematic approach to identifying the root causes of system failures and proposing effective solutions.
- [[vps-performance-diagnosis]] — Covers common methods and metrics for diagnosing performance issues on a Virtual Private Server (VPS), including load average, CPU, and RAM usage analysis.
- [[provider-state-management]] — Explains the concept of tracking the health and status of external providers within a system to make informed decisions about routing and execution.
- [[execution-budget]] — Defines mechanisms for limiting system resource consumption by setting maximum thresholds for cycles, concurrent agents, and retries to prevent runaway processes.
- [[software-testing-types]] — Defines different types of software testing like unit, integration, and E2E tests, and their roles in verifying code behavior.
- [[failure-analysis]] — The process of identifying and determining the root causes of failures in systems or processes.
- [[timeout-failure]] — A type of execution failure where a task exceeds its allocated time limit without completing.
- [[umh-session-state]] — Represents the state management mechanism within the UMH system that allows sessions to resume.
- [[umh-runtime-engine-system-health]] — Refers to the component or indicator within the UMH runtime engine responsible for reporting system health.
- [[system-hooks]] — Mechanisms used by the assistant to query and gather information about the current system status and environment.
- [[short-text-summarization-edge-case]] — Explains the challenge where summarization models may produce output longer than the original input for very short texts.
- [[system-health-inspection-objective]] — An objective type focused on checking the operational status and resource usage of a system using standard commands.
- [[system-status-inspection]] — The process of evaluating the current operational state, resource utilization, and health of a computing system.
- [[docker-container-management]] — Refers to the set of actions and commands used for monitoring, controlling, and interacting with Docker containers.
- [[plan-step-parallelization]] — Explains the concept and benefits of executing independent steps in an AI plan concurrently for efficiency.
- [[llm-input-validation]] — Discusses the importance of validating inputs, like minimum length checks, before invoking Large Language Models to avoid trivial calls.
- [[fresh-session-context]] — Explains that each session starts without prior context, requiring the user to provide a complete task description.
- [[session-persistence]] — Explains how session data is saved and restored across different Claude Code interactions.
- [[claude-code-session-management]] — Describes the mechanisms and behaviors related to starting, resuming, and ending sessions within Claude Code.
- [[plan-quality-metrics]] — Details the various dimensions and scores used to assess the quality of an execution plan, such as specificity, executability, and safety.
- [[llm-summarization-considerations]] — Discusses best practices and common issues when using LLMs for text summarization, including handling short inputs and defining output format.
- [[constraint-check]] — A command or process used to check and prioritize pending tasks based on established constraints.
- [[eos-morning-preparation]] — A routine procedure to check and ensure the health and readiness of the EOS system components.
- [[eos-system-components]] — Overview of the critical components comprising the EOS system, including Docker containers, API keys, Neon DB, and GWS.
- [[anthropic-api-key]] — The API key required for authentication with Anthropic services, essential for EOS AI functionalities.
- [[available-operations-for-plans]] — Lists and explains the standard set of operations available for generating execution plans in Claude Code sessions.
- [[execution-spine]] — A core architectural component currently under development, possibly related to centralizing execution flow.
- [[meta-harness]] — A project component likely related to testing, orchestration, or meta-level control.
- [[eos-mvp]] — A significant project milestone or deliverable, possibly the "End of Session Minimum Viable Product".
- [[session-context-handling]] — Covers the mechanisms and challenges associated with maintaining and retrieving conversational and development context across sessions.
- [[north-star]] — The primary financial objective of $100K/month net profit across the portfolio.
- [[board-level-advisory]] — The defined role and output type of the AI, focusing on strategic advice across the portfolio.
- [[execution-plan-json-format]] — Describes the expected JSON structure for an execution plan, including fields like steps, name, operation, inputs, execution_class, and rationale.
- [[assistant-available-operations]] — Lists the set of primitive operations (e.g., classify_intent, summarize, shell_command) that the assistant can utilize in its execution plans.
- [[system-status-monitoring]] — Describes how system status, including service health and task queues, is reported via hooks.
- [[short-text-llm-input-handling]] — Covers strategies and best practices for managing very short text inputs when using LLMs to avoid suboptimal or unnecessary processing.
- [[ai-execution-plan-review]] — Guidelines and best practices for reviewing automated AI execution plans, focusing on identifying issues and suggesting improvements.
- [[llm-summarization]] — The use of Large Language Models (LLMs) to condense text into a shorter, concise version.
- [[input-validation-in-ai-plans]] — The practice of checking input parameters in AI execution plans to ensure quality, prevent errors, and optimize resource usage.
- [[output-validation-in-ai-plans]] — The practice of checking the output of steps in AI execution plans to ensure desired properties, such as conciseness for summaries.
- [[execution-classes]] — Categories for classifying operations based on their nature, such as llm_call, side_effect, or pure.
- [[execution-class-observation]] — A proposed classification for execution plan steps that perform read-only operations without modifying system state, distinguishing them from 'side_effect' operations.
- [[inspect-system-status]] — A common objective or template for checking the health and operational state of a system.
- [[llm-planning-pipeline]] — The system or process by which a language model generates a plan based on an objective and available operations.
- [[api-error-401]] — A common HTTP status code indicating invalid authentication credentials, blocking access to API resources.
- [[portfolio-north-star]] — A high-level, overarching metric or goal used to guide strategic decisions across an entire portfolio of companies.
- [[task-pause-resume-on-approval]] — Describes the system's capability to pause multi-step tasks requiring approval and automatically resume them without breaking deterministic sequential execution.
- [[event-driven-resume-mechanism]] — Explains the event-driven mechanism for resuming tasks on approval, including the ordering of event processing rules and deadlock prevention.
- [[execution-fabric]] — Details the design and components of the event-native execution layer that replaced direct function calls.
- [[llm-planning-layer]] — Explains the system enabling AI to plan multi-step actions as replay-safe, non-deterministic events.
- [[event-native-execution]] — Defines the paradigm of processing actions as data-driven events through a dispatch system.
- [[single-execution-spine]] — Covers the architectural consolidation of the project into a unified execution path with a meta harness.
- [[broken-chain-links]] — Describes the system health indicators, specifically "foundation," "gateway," and "memory," and their potential implications.
- [[software-testing-levels]] — Covers the definitions and purpose of unit, integration, and end-to-end testing in software development.
- [[llm-execution-plan-format]] — Details the structure of a JSON execution plan including steps, operations, inputs, execution class, and rationale.
- [[llm-agent-operations]] — Lists and describes the core operations an LLM agent can perform, such as `classify_intent`, `summarize`, and `shell_command`.
- [[prompt-payload-separation]] — Discusses the design principle of separating static prompt templates from dynamic payload data in LLM interactions.
- [[common-plan-issues]] — Catalogs frequently encountered problems in AI execution plans, such as template errors, step duplication, and lack of validation.
- [[json-execution-plan-spec]] — Defines the required JSON format and structure for generating an execution plan, including accepted keys like 'steps', 'name', 'operation', 'inputs', 'execution_class', and 'rationale'.
- [[input-validation-in-ai-agents]] — Discusses the importance and implementation of validating input length and content for AI agent operations like summarization.
- [[ceo-agent-simulation]] — A strategy where an AI simulates a CEO role to define objectives and direct specialist agents based on predefined business metrics.
- [[binding-constraint]] — The primary limiting factor or bottleneck preventing a business from achieving its north star metric.
- [[north-star-metric]] — A single, overarching metric that defines the primary growth objective for a business or product.
- [[constraint-diagnosis-framework]] — A framework for identifying the current binding constraint, the single objective, stage advancement criteria, and deprioritized work.
- [[initiate-arena-outreach]] — The primary business objective focused on acquiring qualified prospects for Initiate Arena to achieve first paying customers.
- [[eos-infrastructure-components]] — Key underlying system components of the EOS platform, including the execution spine, meta harness, and planning layers.
- [[minimum-input-length-guard]] — Details a design pattern to prevent LLM operations from processing trivially short inputs, improving quality and efficiency.
- [[input-length-guard]] — A proposed mechanism to prevent execution plans from attempting to process trivially short inputs for tasks like summarization.
- [[execution-plan-concept]] — Covers the definition and structure of an execution plan, likely in JSON format, used for defining sequences of operations.

## Entities

Named things: people, products, companies, offers.

- [[initiate-arena]] — Lyfe Institute's flagship coaching offer
- [[constraint-check-command]] — Explains the purpose and usage of the /constraint-check command for task prioritization.
- [[assistant-operations]] — A list and description of the various operations the assistant is capable of performing, such as `classify_intent` or `summarize`.
- [[short-response-operation]] — Details the `short_response` operation, used for brief acknowledgments or simple replies.
- [[json-execution-plan-format]] — Explains the expected structure and components of a JSON execution plan, including available operations and input parameters.
- [[gateway-intent-classifier]] — The component responsible for classifying user intents, characterized by a single Haiku-class LLM call returning a single uppercase word.
- [[assistant-operations-list]] — A comprehensive list and description of all available operations the assistant can use in execution plans, such as classify_intent, summarize, and file_read.
- [[session-state-module]] — Details the purpose and expected functionality of the 'session_state' module, particularly regarding persistent session data.
- [[classify-intent-operation]] — An operation typically used in AI execution plans to determine the user's or system's intended action from a given prompt.
- [[os-bot-status]] — Describes the 'os-bot' entity, its typical function, and how to check its current operational status.
- [[eos-sessionstate-system]] — Details the underlying system responsible for managing persistent session state in the EOS environment for Claude Code.
- [[gws-connector]] — A component within the EOS system responsible for connecting to and interacting with the GWS service.
- [[neon-database]] — The database service used by EOS, checked for connectivity during morning preparation.
- [[munoz-holdings-portfolio]] — The overarching entity for which the AI provides board-level advisory.
- [[strategy-engine]] — A system mentioned for providing strategy analysis, currently experiencing authentication issues.
- [[os-bot]] — Explains the purpose and status of the os-bot service.
- [[bis-service]] — Describes the BIS service, responsible for providing the Venture stage.
- [[llm-summarize-operation]] — Details the `summarize` operation as implemented for LLMs within AI execution plans, including common inputs and considerations.
- [[available-operations-list]] — A catalog of permissible actions or functions that can be incorporated into an execution plan.
- [[umh-orchestrator-task]] — Covers the `umh/orchestrator/task.py` module, which defines task state, status, and pause-related fields, including `TaskStatus.PAUSED` and `StepStatus.WAITING_APPROVAL`.
- [[summarize-operation]] — A common AI operation used in execution plans to condense textual information into a shorter, coherent summary, typically powered by an LLM.
- [[api-authentication-error-401]] — An HTTP status code indicating that the client's request lacks valid authentication credentials for the target resource.
- [[claudemd]] — A markdown document serving as a primary source of truth for system constraints and state.

## Decisions

Architectural, strategic, or operational choices with rationale.

- [[eos-architectural-preservation]] — Explains the decision to implement presentation and lifecycle layers on top of the existing EOS pipeline without modifying the hot path, ensuring architecture preservation.
- [[in-memory-task-pause-state]] — Details the architectural decision to store task pause state entirely in-memory on the Task dataclass, including the rationale and trade-offs.

## Synthesis

Cross-cutting analysis that connects multiple sources or concepts.

- [[eos-mode-behavior-control]] — Details the EOS Mode Behavior + Session Control v1 production upgrade, including objectives, non-negotiables, implementation steps, and architectural insights.
- [[available-operations]] — A catalog of all operations available to the assistant for generating
- [[automated-loop-diagnosis]] — Documents the process of identifying and troubleshooting continuous "continue" messages caused by automated system hooks.
- [[system-health-check-plan]] — Describes a standard AI execution plan template for inspecting the health and status of a system.
- [[summarization-of-vague-input]] — Details the system's behavior when prompted to summarize insufficient or non-meaningful input.
- [[execution-plan-constraints]] — Outlines the general rules and limitations that apply to generating and formatting execution plans, such as step limits and required fields.
- [[text-summarization-plans]] — Best practices and common templates for AI execution plans designed to summarize text using LLMs.
- [[unclear-objective-handling]] — Details the system's strategy for identifying and responding to vague or non-actionable user objectives.
- [[failure-analysis-json-standard]] — Specifies the required JSON format and fields for structured failure analysis reports, including root cause, category, and fix.
- [[system-backpressure-and-failure-recovery]] — Details strategies and components for building resilient systems that prevent cascading failures and manage resource exhaustion, including global provider state, execution budgets, and subagent spawn guards.
- [[execution-plan-objective-handling]] — Documents the expected JSON format for objective-based execution plans and the system's responses to undefined, invalid, or nonexistent template objectives.
- [[plan-review-process]] — Outlines the methodology and common considerations for evaluating AI execution plans for issues and potential improvements.
- [[objective-summarize-text]] — An example objective highlighting common pitfalls in AI plan generation, such as mistaking intent classification for actual summarization and lacking proper context resolution.
- [[text-summarization-plan-review]] — Best practices and common issues identified when reviewing execution plans for text summarization tasks.
- [[task-assignment-protocol]] — Outlines the recommended way to assign tasks in a fresh session, emphasizing the need for full context rather than partial steps.
- [[objective-planning-process]] — Details how Claude constructs multi-step execution plans from a given objective, constraints, and available operations.
- [[staging-deployment-workflow]] — Outlines a typical multi-step workflow for deploying to a staging environment, covering configuration, validation, execution, and verification.
- [[broken-chains-diagnosis]] — Details the recurring system health issue where specific chains (foundation, gateway, memory) are reported as broken.
- [[trivial-input-length-issue]] — A problem in LLM summarization where very short input texts may result in summaries that are longer than the original or simply echo the input.
- [[execution-planning-rejection-strategy]] — Explains how the assistant rejects invalid or undefined objectives when asked to generate an execution plan, typically by using a short_response operation.
- [[execution-plan-best-practices]] — A compilation of recommended fields, constraints, and scoring considerations for robust AI execution plans, such as `expected_output`, `success_criteria`, `timeout`, `max_tokens`, and confidence calibration.
- [[invalid-objective-handling]] — Describes the assistant's behavior and strategies when presented with objectives that are vague, non-actionable, or intentionally invalid.
- [[nonexistent-objective-handling]] — Describes the AI's response strategy when an objective is explicitly "nonexistent" or empty, leading to a short acknowledgment and prompt for a new task.
- [[unclear-prompt-clarification]] — Explains the assistant's behavior of prompting the user for more context or a clearer task when given vague or very short inputs that lack actionable instructions.
- [[claude-code-session-context]] — Explains how session state and context persistence work within Claude Code, detailing the distinction between fresh and ongoing sessions.
- [[summarization-best-practices]] — Gathers best practices and common patterns for designing AI execution plans focused on text summarization, including input validation strategies.
- [[plan-validation-strategies]] — Explains techniques for ensuring the correctness and quality of AI execution plans, including verification and aggregation steps.
- [[objective-rejection-strategy]] — Explains the assistant's consistent strategy for rejecting invalid or vague objectives by returning clear error messages and requiring valid descriptions.
- [[handling-invalid-requests]] — Strategies and best practices for an AI assistant to respond to vague, nonsensical, or unachievable user requests.
- [[system-health-check-patterns]] — Outlines common steps and suggested structures for effective system health inspection plans, including summary steps.
- [[handling-vague-objectives]] — Strategies and common patterns for dealing with user objectives that lack sufficient detail for direct execution.
- [[minimum-input-length-check]] — Discusses the rationale and implementation of checks to prevent LLM calls for trivially short inputs.

## Sources

Summaries of ingested RAW material with provenance links.

(none yet)
