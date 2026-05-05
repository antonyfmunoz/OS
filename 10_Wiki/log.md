<<<<<<< Updated upstream
---
type: wiki_log
---

# Wiki Change Log

Append-only. Every wiki mutation gets an entry.

## [2026-04-05T21:45:00-07:00] create | index.md
Initial wiki index created with Concepts, Entities, Decisions, Synthesis, Sources categories.

## [2026-04-05T21:45:00-07:00] create | WIKI_RULES.md
Wiki schema and operating rules established.

## [2026-04-05T21:45:00-07:00] create | entities/initiate-arena.md
Seeded from 04_Offers/Initiate Arena.md and existing knowledge.

## [2026-04-05T21:45:00-07:00] create | concepts/icp-signals.md
Synthesized from 07_Knowledge/ICP/ signal analysis files.

## [2026-04-06T02:57:39-07:00] create | memory-pipeline
Promoted from summary. The conversation-to-summary-to-wiki knowledge extraction pipeline in EOS

## [2026-04-11T03:14:03-07:00] create | eos-mode-behavior-control
Promoted from summary. Details the EOS Mode Behavior + Session Control v1 production upgrade, including objectives, non-negotiables, implementation steps, and architectural insights.

## [2026-04-11T03:14:03-07:00] create | eos-product-mode
Promoted from summary. Explains the target behavior and implementation for Product Mode in EOS, focusing on clean SaaS output and suppression of internal language.

## [2026-04-11T03:14:04-07:00] create | eos-builder-mode
Promoted from summary. Describes the target behavior for Builder Mode in EOS, aiming for an AI operator/dev cofounder feel with system/debug references visible.

## [2026-04-11T03:14:05-07:00] create | eos-auto-clear-mechanism
Promoted from summary. Documents the flow-triggered, message-counting mechanism for auto-clearing sessions in EOS, highlighting its efficiency benefits.

## [2026-04-11T03:14:05-07:00] create | eos-architectural-preservation
Promoted from summary. Explains the decision to implement presentation and lifecycle layers on top of the existing EOS pipeline without modifying the hot path, ensuring architecture preservation.

## [2026-05-01T06:13:33-07:00] create | claude-code-session
Promoted from summary. Describes the environment for interactive coding and problem-solving.

## [2026-05-01T06:13:34-07:00] create | constraint-check-command
Promoted from summary. Explains the purpose and usage of the /constraint-check command for task prioritization.

## [2026-05-01T06:13:35-07:00] create | json-execution-plan
Promoted from summary. Explains the structure and purpose of a JSON object describing a multi-step plan for the assistant to execute.

## [2026-05-01T06:13:36-07:00] create | assistant-operations
Promoted from summary. A list and description of the various operations the assistant is capable of performing, such as `classify_intent` or `summarize`.

## [2026-05-01T06:13:37-07:00] create | execution-class-types
Promoted from summary. Defines the categories of execution classes like `llm_call`, `side_effect`, and `pure` used to characterize operations in an execution plan.

## [2026-05-01T06:13:40-07:00] create | llm-operations
Promoted from summary. Details the available primitive operations (e.g., classify_intent, short_response, shell_command) that can be included in an execution plan.

## [2026-05-01T06:13:43-07:00] create | execution-class
Promoted from summary. Describes the categorization of operations into 'llm_call', 'side_effect', or 'pure' based on their nature and impact.

## [2026-05-01T06:13:46-07:00] create | short-response-operation
Promoted from summary. Details the `short_response` operation, used for brief acknowledgments or simple replies.

## [2026-05-01T06:13:47-07:00] create | test-step-statuses
Promoted from summary. Explains the concept of "test step statuses" as checking or reporting the pass/fail state of individual steps in a test run.

## [2026-05-01T06:13:49-07:00] create | available-operations
Promoted from summary. A catalog of all operations available to the assistant for generating

## [2026-05-01T06:13:52-07:00] create | execution-class-categories
Promoted from summary. Explains the different categories for operations such such as llm_call, side_effect, and pure.

## [2026-05-01T06:13:53-07:00] create | available-ai-operations
Promoted from summary. Documents the standard set of operations an AI agent can utilize for task execution.

## [2026-05-01T06:13:56-07:00] create | ai-execution-system
Promoted from summary. The system responsible for executing AI-driven plans based on objectives and capabilities.

## [2026-05-01T06:14:01-07:00] create | execution-plan
Promoted from summary. A structured set of steps designed to achieve a specific objective within an AI execution system.

## [2026-05-01T06:14:03-07:00] create | system-health-inspection
Promoted from summary. The process of evaluating and reporting the operational status and resource utilization of a system.

## [2026-05-01T06:14:05-07:00] create | session-state-persistence
Promoted from summary. Explains how task context and session state are managed, particularly the lack of persistence across new sessions.

## [2026-05-01T06:14:07-07:00] create | automated-loop-diagnosis
Promoted from summary. Documents the process of identifying and troubleshooting continuous "continue" messages caused by automated system hooks.

## [2026-05-01T06:14:08-07:00] create | classify-intent
Promoted from summary. Describes the `classify_intent` function or module and its role within the codebase.

## [2026-05-01T06:14:09-07:00] create | plan-review
Promoted from summary. Details the process of evaluating an AI execution plan for correctness, efficiency, and adherence to objectives.

## [2026-05-01T06:14:09-07:00] create | system-health-check-plan
Promoted from summary. Describes a standard AI execution plan template for inspecting the health and status of a system.

## [2026-05-01T06:14:11-07:00] create | shell-command-operation
Promoted from summary. Defines the 'shell_command' operation, a fundamental capability allowing AI agents to execute shell commands.

## [2026-05-01T06:14:12-07:00] create | system-health-check
Promoted from summary. Details standard procedures and common commands for assessing system status.

## [2026-05-01T06:14:13-07:00] create | plan-reviewer
Promoted from summary. A role or persona within the AI execution system responsible for evaluating plans for issues, suggestions, and adherence to constraints.

## [2026-05-01T06:14:14-07:00] create | objective-interpretation-logic
Promoted from summary. Describes how the assistant interprets and responds to different types of objectives, especially vague or invalid ones.

## [2026-05-01T06:14:15-07:00] create | summarization-of-vague-input
Promoted from summary. Details the system's behavior when prompted to summarize insufficient or non-meaningful input.

## [2026-05-01T06:14:17-07:00] create | json-execution-plan-format
Promoted from summary. Explains the expected structure and components of a JSON execution plan, including available operations and input parameters.

## [2026-05-01T06:14:18-07:00] create | testing-types
Promoted from summary. Defines and differentiates between unit, integration, and end-to-end testing, as explained by the assistant.

## [2026-05-01T06:14:19-07:00] create | execution-plan-constraints
Promoted from summary. Outlines the general rules and limitations that apply to generating and formatting execution plans, such as step limits and required fields.

## [2026-05-01T06:14:20-07:00] create | llm-call-execution-class
Promoted from summary. Defines the 'llm_call' execution class, indicating that a step in an execution plan involves an interaction with a large language model.

## [2026-05-01T06:14:21-07:00] create | dry-run-mode
Promoted from summary. A mode of operation where a plan is simulated or acknowledged without taking any side-effecting actions.

## [2026-05-01T06:14:22-07:00] create | llm-call
Promoted from summary. An operation within an execution plan that involves making a call to a Large Language Model.

## [2026-05-01T06:14:23-07:00] create | execution-plan-review
Promoted from summary. A guide on the process and criteria for reviewing AI execution plans to identify issues and suggest improvements.

## [2026-05-01T06:14:24-07:00] create | text-summarization-plans
Promoted from summary. Best practices and common templates for AI execution plans designed to summarize text using LLMs.

## [2026-05-01T06:14:25-07:00] create | input-length-check-for-summarization
Promoted from summary. A discussion of the importance and implementation of input length checks for summarization tasks to improve quality and efficiency.

## [2026-05-01T06:14:26-07:00] create | execution-plan-generation
Promoted from summary. Covers the process and requirements for generating structured execution plans based on objectives and specified constraints.

## [2026-05-01T06:14:27-07:00] create | dry-run-constraint
Promoted from summary. Explains the 'dry_run' constraint, its implications for execution, and the expected system behavior of generating plans without side effects.

## [2026-05-01T06:14:27-07:00] create | unclear-objective-handling
Promoted from summary. Details the system's strategy for identifying and responding to vague or non-actionable user objectives.

## [2026-05-01T06:14:28-07:00] create | brief-intent
Promoted from summary. An existing intent in the gateway classifier, triggered by keywords like 'summary', designed for system status updates rather than content summarization.

## [2026-05-01T06:14:29-07:00] create | intent-gap
Promoted from summary. A common issue where user input is misrouted due to an ambiguity or absence in the intent classification system.

## [2026-05-01T06:14:31-07:00] create | gateway-intent-classifier
Promoted from summary. The component responsible for classifying user intents, characterized by a single Haiku-class LLM call returning a single uppercase word.

## [2026-05-01T06:14:32-07:00] create | assistant-operations-list
Promoted from summary. A comprehensive list and description of all available operations the assistant can use in execution plans, such as classify_intent, summarize, and file_read.

## [2026-05-01T06:14:33-07:00] create | input-validation-for-llm-interactions
Promoted from summary. Explains the importance of providing clear, contextual, and complete input for effective interaction with LLM-based assistants, highlighting common rejection scenarios.

## [2026-05-01T06:14:33-07:00] create | umh-runtime-engine-system-health-error
Promoted from summary. Covers the recurring error related to the 'umh.runtime_engine.system_health' module, including its symptoms and potential causes.

## [2026-05-01T06:14:34-07:00] create | session-state-module
Promoted from summary. Details the purpose and expected functionality of the 'session_state' module, particularly regarding persistent session data.

## [2026-05-01T06:14:35-07:00] create | pending-tasks
Promoted from summary. Describes the system's mechanism for tracking and managing pending tasks that require attention or resolution.

## [2026-05-01T06:14:37-07:00] create | ai-execution-system-failure-analysis
Promoted from summary. Covers the process and methods for analyzing failures within an AI execution system.

## [2026-05-01T06:14:37-07:00] create | error-classification-categories
Promoted from summary. Defines and describes standard categories for classifying errors in an AI execution system, such as input_error, timeout, and internal_error.

## [2026-05-01T06:14:38-07:00] create | root-cause-analysis-template
Promoted from summary. Details the structured output required for root cause analysis, including root_cause, failure_category, and suggested_fix fields.

## [2026-05-01T06:14:39-07:00] create | ai-execution-plan
Promoted from summary. A structured plan defining steps and operations for an AI execution system.

## [2026-05-01T06:14:40-07:00] create | plan-reviewer-role
Promoted from summary. The role responsible for evaluating AI execution plans for issues and suggestions.

## [2026-05-01T06:14:40-07:00] create | llm-call-operation
Promoted from summary. A type of operation within an execution plan that involves making a call to a Large Language Model.

## [2026-05-01T06:14:41-07:00] create | failure-analysis-methodology
Promoted from summary. Details the systematic approach to identifying the root causes of system failures and proposing effective solutions.

## [2026-05-01T06:14:42-07:00] create | failure-analysis-json-standard
Promoted from summary. Specifies the required JSON format and fields for structured failure analysis reports, including root cause, category, and fix.

## [2026-05-01T06:14:43-07:00] create | vps-performance-diagnosis
Promoted from summary. Covers common methods and metrics for diagnosing performance issues on a Virtual Private Server (VPS), including load average, CPU, and RAM usage analysis.

## [2026-05-01T06:14:44-07:00] create | system-backpressure-and-failure-recovery
Promoted from summary. Details strategies and components for building resilient systems that prevent cascading failures and manage resource exhaustion, including global provider state, execution budgets, and subagent spawn guards.

## [2026-05-01T06:14:44-07:00] create | provider-state-management
Promoted from summary. Explains the concept of tracking the health and status of external providers within a system to make informed decisions about routing and execution.

## [2026-05-01T06:14:45-07:00] create | execution-budget
Promoted from summary. Defines mechanisms for limiting system resource consumption by setting maximum thresholds for cycles, concurrent agents, and retries to prevent runaway processes.

## [2026-05-01T06:14:47-07:00] create | software-testing-types
Promoted from summary. Defines different types of software testing like unit, integration, and E2E tests, and their roles in verifying code behavior.

## [2026-05-01T06:14:47-07:00] create | execution-plan-objective-handling
Promoted from summary. Documents the expected JSON format for objective-based execution plans and the system's responses to undefined, invalid, or nonexistent template objectives.

## [2026-05-01T06:14:48-07:00] create | failure-analysis
Promoted from summary. The process of identifying and determining the root causes of failures in systems or processes.

## [2026-05-01T06:14:49-07:00] create | timeout-failure
Promoted from summary. A type of execution failure where a task exceeds its allocated time limit without completing.

## [2026-05-01T06:14:50-07:00] create | umh-session-state
Promoted from summary. Represents the state management mechanism within the UMH system that allows sessions to resume.

## [2026-05-01T06:14:51-07:00] create | umh-runtime-engine-system-health
Promoted from summary. Refers to the component or indicator within the UMH runtime engine responsible for reporting system health.

## [2026-05-01T06:14:52-07:00] create | system-hooks
Promoted from summary. Mechanisms used by the assistant to query and gather information about the current system status and environment.

## [2026-05-01T06:14:53-07:00] create | plan-review-process
Promoted from summary. Outlines the methodology and common considerations for evaluating AI execution plans for issues and potential improvements.

## [2026-05-01T06:14:53-07:00] create | short-text-summarization-edge-case
Promoted from summary. Explains the challenge where summarization models may produce output longer than the original input for very short texts.

## [2026-05-01T06:14:54-07:00] create | system-health-inspection-objective
Promoted from summary. An objective type focused on checking the operational status and resource usage of a system using standard commands.

## [2026-05-01T06:14:55-07:00] create | classify-intent-operation
Promoted from summary. An operation typically used in AI execution plans to determine the user's or system's intended action from a given prompt.

## [2026-05-01T06:14:56-07:00] create | objective-summarize-text
Promoted from summary. An example objective highlighting common pitfalls in AI plan generation, such as mistaking intent classification for actual summarization and lacking proper context resolution.

## [2026-05-01T06:14:57-07:00] create | system-status-inspection
Promoted from summary. The process of evaluating the current operational state, resource utilization, and health of a computing system.

## [2026-05-01T06:14:57-07:00] create | docker-container-management
Promoted from summary. Refers to the set of actions and commands used for monitoring, controlling, and interacting with Docker containers.

## [2026-05-01T06:14:58-07:00] create | text-summarization-plan-review
Promoted from summary. Best practices and common issues identified when reviewing execution plans for text summarization tasks.

## [2026-05-01T06:15:01-07:00] create | plan-step-parallelization
Promoted from summary. Explains the concept and benefits of executing independent steps in an AI plan concurrently for efficiency.

## [2026-05-01T06:15:18-07:00] create | llm-input-validation
Promoted from summary. Discusses the importance of validating inputs, like minimum length checks, before invoking Large Language Models to avoid trivial calls.

## [2026-05-01T06:15:31-07:00] create | fresh-session-context
Promoted from summary. Explains that each session starts without prior context, requiring the user to provide a complete task description.

## [2026-05-01T06:15:46-07:00] create | os-bot-status
Promoted from summary. Describes the 'os-bot' entity, its typical function, and how to check its current operational status.

## [2026-05-01T06:15:53-07:00] create | task-assignment-protocol
Promoted from summary. Outlines the recommended way to assign tasks in a fresh session, emphasizing the need for full context rather than partial steps.

## [2026-05-01T06:16:04-07:00] create | session-persistence
Promoted from summary. Explains how session data is saved and restored across different Claude Code interactions.

## [2026-05-01T06:16:15-07:00] create | claude-code-session-management
Promoted from summary. Describes the mechanisms and behaviors related to starting, resuming, and ending sessions within Claude Code.

## [2026-05-01T06:16:25-07:00] create | eos-sessionstate-system
Promoted from summary. Details the underlying system responsible for managing persistent session state in the EOS environment for Claude Code.

## [2026-05-01T06:16:33-07:00] create | plan-quality-metrics
Promoted from summary. Details the various dimensions and scores used to assess the quality of an execution plan, such as specificity, executability, and safety.

## [2026-05-01T06:16:41-07:00] create | llm-summarization-considerations
Promoted from summary. Discusses best practices and common issues when using LLMs for text summarization, including handling short inputs and defining output format.

## [2026-05-01T06:16:48-07:00] create | constraint-check
Promoted from summary. A command or process used to check and prioritize pending tasks based on established constraints.

## [2026-05-01T06:16:53-07:00] create | eos-morning-preparation
Promoted from summary. A routine procedure to check and ensure the health and readiness of the EOS system components.

## [2026-05-01T06:16:59-07:00] create | eos-system-components
Promoted from summary. Overview of the critical components comprising the EOS system, including Docker containers, API keys, Neon DB, and GWS.

## [2026-05-01T06:17:06-07:00] create | gws-connector
Promoted from summary. A component within the EOS system responsible for connecting to and interacting with the GWS service.

## [2026-05-01T06:17:13-07:00] create | neon-database
Promoted from summary. The database service used by EOS, checked for connectivity during morning preparation.

## [2026-05-01T06:17:17-07:00] create | anthropic-api-key
Promoted from summary. The API key required for authentication with Anthropic services, essential for EOS AI functionalities.

## [2026-05-01T06:17:19-07:00] create | available-operations-for-plans
Promoted from summary. Lists and explains the standard set of operations available for generating execution plans in Claude Code sessions.

## [2026-05-01T06:17:21-07:00] create | objective-planning-process
Promoted from summary. Details how Claude constructs multi-step execution plans from a given objective, constraints, and available operations.

## [2026-05-01T06:17:24-07:00] create | staging-deployment-workflow
Promoted from summary. Outlines a typical multi-step workflow for deploying to a staging environment, covering configuration, validation, execution, and verification.

## [2026-05-01T06:17:25-07:00] create | execution-spine
Promoted from summary. A core architectural component currently under development, possibly related to centralizing execution flow.

## [2026-05-01T06:17:28-07:00] create | meta-harness
Promoted from summary. A project component likely related to testing, orchestration, or meta-level control.

## [2026-05-01T06:17:32-07:00] create | eos-mvp
Promoted from summary. A significant project milestone or deliverable, possibly the "End of Session Minimum Viable Product".

## [2026-05-01T06:17:36-07:00] create | broken-chains-diagnosis
Promoted from summary. Details the recurring system health issue where specific chains (foundation, gateway, memory) are reported as broken.

## [2026-05-01T06:17:37-07:00] create | session-context-handling
Promoted from summary. Covers the mechanisms and challenges associated with maintaining and retrieving conversational and development context across sessions.

## [2026-05-01T06:17:39-07:00] create | munoz-holdings-portfolio
Promoted from summary. The overarching entity for which the AI provides board-level advisory.

## [2026-05-01T06:17:40-07:00] create | north-star
Promoted from summary. The primary financial objective of $100K/month net profit across the portfolio.

## [2026-05-01T06:17:40-07:00] create | strategy-engine
Promoted from summary. A system mentioned for providing strategy analysis, currently experiencing authentication issues.

## [2026-05-01T06:17:41-07:00] create | board-level-advisory
Promoted from summary. The defined role and output type of the AI, focusing on strategic advice across the portfolio.

## [2026-05-01T06:17:42-07:00] create | trivial-input-length-issue
Promoted from summary. A problem in LLM summarization where very short input texts may result in summaries that are longer than the original or simply echo the input.

## [2026-05-01T06:17:44-07:00] create | execution-planning-rejection-strategy
Promoted from summary. Explains how the assistant rejects invalid or undefined objectives when asked to generate an execution plan, typically by using a short_response operation.

## [2026-05-01T06:17:46-07:00] create | execution-plan-json-format
Promoted from summary. Describes the expected JSON structure for an execution plan, including fields like steps, name, operation, inputs, execution_class, and rationale.

## [2026-05-01T06:17:50-07:00] create | assistant-available-operations
Promoted from summary. Lists the set of primitive operations (e.g., classify_intent, summarize, shell_command) that the assistant can utilize in its execution plans.

## [2026-05-01T06:17:54-07:00] create | os-bot
Promoted from summary. Explains the purpose and status of the os-bot service.

## [2026-05-01T06:17:55-07:00] create | system-status-monitoring
Promoted from summary. Describes how system status, including service health and task queues, is reported via hooks.

## [2026-05-01T06:17:57-07:00] create | bis-service
Promoted from summary. Describes the BIS service, responsible for providing the Venture stage.

## [2026-05-01T06:17:59-07:00] create | llm-summarize-operation
Promoted from summary. Details the `summarize` operation as implemented for LLMs within AI execution plans, including common inputs and considerations.

## [2026-05-01T06:18:02-07:00] create | short-text-llm-input-handling
Promoted from summary. Covers strategies and best practices for managing very short text inputs when using LLMs to avoid suboptimal or unnecessary processing.

## [2026-05-01T06:18:06-07:00] create | ai-execution-plan-review
Promoted from summary. Guidelines and best practices for reviewing automated AI execution plans, focusing on identifying issues and suggesting improvements.

## [2026-05-01T06:18:10-07:00] create | execution-plan-best-practices
Promoted from summary. A compilation of recommended fields, constraints, and scoring considerations for robust AI execution plans, such as `expected_output`, `success_criteria`, `timeout`, `max_tokens`, and confidence calibration.

## [2026-05-01T06:18:16-07:00] create | invalid-objective-handling
Promoted from summary. Describes the assistant's behavior and strategies when presented with objectives that are vague, non-actionable, or intentionally invalid.

## [2026-05-01T06:18:21-07:00] create | llm-summarization
Promoted from summary. The use of Large Language Models (LLMs) to condense text into a shorter, concise version.

## [2026-05-01T06:18:26-07:00] create | input-validation-in-ai-plans
Promoted from summary. The practice of checking input parameters in AI execution plans to ensure quality, prevent errors, and optimize resource usage.

## [2026-05-01T06:18:32-07:00] create | output-validation-in-ai-plans
Promoted from summary. The practice of checking the output of steps in AI execution plans to ensure desired properties, such as conciseness for summaries.

## [2026-05-01T06:18:37-07:00] create | nonexistent-objective-handling
Promoted from summary. Describes the AI's response strategy when an objective is explicitly "nonexistent" or empty, leading to a short acknowledgment and prompt for a new task.

## [2026-05-01T06:18:42-07:00] create | unclear-prompt-clarification
Promoted from summary. Explains the assistant's behavior of prompting the user for more context or a clearer task when given vague or very short inputs that lack actionable instructions.

## [2026-05-01T06:18:46-07:00] create | execution-classes
Promoted from summary. Categories for classifying operations based on their nature, such as llm_call, side_effect, or pure.

## [2026-05-01T06:18:53-07:00] create | available-operations-list
Promoted from summary. A catalog of permissible actions or functions that can be incorporated into an execution plan.

## [2026-05-01T06:18:57-07:00] create | execution-class-observation
Promoted from summary. A proposed classification for execution plan steps that perform read-only operations without modifying system state, distinguishing them from 'side_effect' operations.

## [2026-05-01T06:19:01-07:00] create | inspect-system-status
Promoted from summary. A common objective or template for checking the health and operational state of a system.

## [2026-05-01T06:19:06-07:00] create | llm-planning-pipeline
Promoted from summary. The system or process by which a language model generates a plan based on an objective and available operations.

## [2026-05-01T06:19:10-07:00] create | api-error-401
Promoted from summary. A common HTTP status code indicating invalid authentication credentials, blocking access to API resources.

## [2026-05-01T06:19:14-07:00] create | portfolio-north-star
Promoted from summary. A high-level, overarching metric or goal used to guide strategic decisions across an entire portfolio of companies.

## [2026-05-01T06:19:19-07:00] create | task-pause-resume-on-approval
Promoted from summary. Describes the system's capability to pause multi-step tasks requiring approval and automatically resume them without breaking deterministic sequential execution.

## [2026-05-01T06:19:24-07:00] create | in-memory-task-pause-state
Promoted from summary. Details the architectural decision to store task pause state entirely in-memory on the Task dataclass, including the rationale and trade-offs.

## [2026-05-01T06:19:30-07:00] create | event-driven-resume-mechanism
Promoted from summary. Explains the event-driven mechanism for resuming tasks on approval, including the ordering of event processing rules and deadlock prevention.

## [2026-05-01T06:19:35-07:00] create | umh-orchestrator-task
Promoted from summary. Covers the `umh/orchestrator/task.py` module, which defines task state, status, and pause-related fields, including `TaskStatus.PAUSED` and `StepStatus.WAITING_APPROVAL`.

## [2026-05-01T06:19:38-07:00] create | execution-fabric
Promoted from summary. Details the design and components of the event-native execution layer that replaced direct function calls.

## [2026-05-01T06:19:42-07:00] create | llm-planning-layer
Promoted from summary. Explains the system enabling AI to plan multi-step actions as replay-safe, non-deterministic events.

## [2026-05-01T06:19:45-07:00] create | event-native-execution
Promoted from summary. Defines the paradigm of processing actions as data-driven events through a dispatch system.

## [2026-05-01T06:19:47-07:00] create | single-execution-spine
Promoted from summary. Covers the architectural consolidation of the project into a unified execution path with a meta harness.

## [2026-05-01T06:19:51-07:00] create | claude-code-session-context
Promoted from summary. Explains how session state and context persistence work within Claude Code, detailing the distinction between fresh and ongoing sessions.

## [2026-05-01T06:19:55-07:00] create | broken-chain-links
Promoted from summary. Describes the system health indicators, specifically "foundation," "gateway," and "memory," and their potential implications.

## [2026-05-01T06:19:58-07:00] create | summarization-best-practices
Promoted from summary. Gathers best practices and common patterns for designing AI execution plans focused on text summarization, including input validation strategies.

## [2026-05-01T06:20:10-07:00] create | software-testing-levels
Promoted from summary. Covers the definitions and purpose of unit, integration, and end-to-end testing in software development.

## [2026-05-01T06:20:23-07:00] create | llm-execution-plan-format
Promoted from summary. Details the structure of a JSON execution plan including steps, operations, inputs, execution class, and rationale.

## [2026-05-01T06:20:30-07:00] create | llm-agent-operations
Promoted from summary. Lists and describes the core operations an LLM agent can perform, such as `classify_intent`, `summarize`, and `shell_command`.

## [2026-05-01T06:20:47-07:00] create | prompt-payload-separation
Promoted from summary. Discusses the design principle of separating static prompt templates from dynamic payload data in LLM interactions.

## [2026-05-01T06:20:58-07:00] create | common-plan-issues
Promoted from summary. Catalogs frequently encountered problems in AI execution plans, such as template errors, step duplication, and lack of validation.

## [2026-05-01T06:21:03-07:00] create | plan-validation-strategies
Promoted from summary. Explains techniques for ensuring the correctness and quality of AI execution plans, including verification and aggregation steps.

## [2026-05-01T06:21:09-07:00] create | summarize-operation
Promoted from summary. A common AI operation used in execution plans to condense textual information into a shorter, coherent summary, typically powered by an LLM.

## [2026-05-01T06:21:13-07:00] create | objective-rejection-strategy
Promoted from summary. Explains the assistant's consistent strategy for rejecting invalid or vague objectives by returning clear error messages and requiring valid descriptions.

## [2026-05-01T06:21:17-07:00] create | json-execution-plan-spec
Promoted from summary. Defines the required JSON format and structure for generating an execution plan, including accepted keys like 'steps', 'name', 'operation', 'inputs', 'execution_class', and 'rationale'.

## [2026-05-01T06:21:21-07:00] create | handling-invalid-requests
Promoted from summary. Strategies and best practices for an AI assistant to respond to vague, nonsensical, or unachievable user requests.

## [2026-05-01T06:21:27-07:00] create | system-health-check-patterns
Promoted from summary. Outlines common steps and suggested structures for effective system health inspection plans, including summary steps.

## [2026-05-01T06:21:32-07:00] create | input-validation-in-ai-agents
Promoted from summary. Discusses the importance and implementation of validating input length and content for AI agent operations like summarization.

## [2026-05-01T06:21:39-07:00] create | ceo-agent-simulation
Promoted from summary. A strategy where an AI simulates a CEO role to define objectives and direct specialist agents based on predefined business metrics.

## [2026-05-01T06:21:43-07:00] create | binding-constraint
Promoted from summary. The primary limiting factor or bottleneck preventing a business from achieving its north star metric.

## [2026-05-01T06:21:48-07:00] create | north-star-metric
Promoted from summary. A single, overarching metric that defines the primary growth objective for a business or product.

## [2026-05-01T06:21:53-07:00] create | api-authentication-error-401
Promoted from summary. An HTTP status code indicating that the client's request lacks valid authentication credentials for the target resource.

## [2026-05-01T06:21:57-07:00] create | handling-vague-objectives
Promoted from summary. Strategies and common patterns for dealing with user objectives that lack sufficient detail for direct execution.

## [2026-05-01T06:22:02-07:00] create | constraint-diagnosis-framework
Promoted from summary. A framework for identifying the current binding constraint, the single objective, stage advancement criteria, and deprioritized work.

## [2026-05-01T06:22:06-07:00] create | initiate-arena-outreach
Promoted from summary. The primary business objective focused on acquiring qualified prospects for Initiate Arena to achieve first paying customers.

## [2026-05-01T06:22:09-07:00] create | eos-infrastructure-components
Promoted from summary. Key underlying system components of the EOS platform, including the execution spine, meta harness, and planning layers.

## [2026-05-01T06:22:12-07:00] create | claudemd
Promoted from summary. A markdown document serving as a primary source of truth for system constraints and state.

## [2026-05-01T06:22:16-07:00] create | minimum-input-length-guard
Promoted from summary. Details a design pattern to prevent LLM operations from processing trivially short inputs, improving quality and efficiency.

## [2026-05-01T06:22:19-07:00] create | minimum-input-length-check
Promoted from summary. Discusses the rationale and implementation of checks to prevent LLM calls for trivially short inputs.

## [2026-05-01T06:22:23-07:00] create | input-length-guard
Promoted from summary. A proposed mechanism to prevent execution plans from attempting to process trivially short inputs for tasks like summarization.

## [2026-05-01T06:22:27-07:00] create | execution-plan-concept
Promoted from summary. Covers the definition and structure of an execution plan, likely in JSON format, used for defining sequences of operations.
=======
---
type: wiki_log
---

# Wiki Change Log

Append-only. Every wiki mutation gets an entry.

## [2026-04-05T21:45:00-07:00] create | index.md
Initial wiki index created with Concepts, Entities, Decisions, Synthesis, Sources categories.

## [2026-04-05T21:45:00-07:00] create | WIKI_RULES.md
Wiki schema and operating rules established.

## [2026-04-05T21:45:00-07:00] create | entities/initiate-arena.md
Seeded from 04_Offers/Initiate Arena.md and existing knowledge.

## [2026-04-05T21:45:00-07:00] create | concepts/icp-signals.md
Synthesized from 07_Knowledge/ICP/ signal analysis files.

## [2026-04-06T02:57:39-07:00] create | memory-pipeline
Promoted from summary. The conversation-to-summary-to-wiki knowledge extraction pipeline in EOS

## [2026-04-11T03:14:03-07:00] create | eos-mode-behavior-control
Promoted from summary. Details the EOS Mode Behavior + Session Control v1 production upgrade, including objectives, non-negotiables, implementation steps, and architectural insights.

## [2026-04-11T03:14:03-07:00] create | eos-product-mode
Promoted from summary. Explains the target behavior and implementation for Product Mode in EOS, focusing on clean SaaS output and suppression of internal language.

## [2026-04-11T03:14:04-07:00] create | eos-builder-mode
Promoted from summary. Describes the target behavior for Builder Mode in EOS, aiming for an AI operator/dev cofounder feel with system/debug references visible.

## [2026-04-11T03:14:05-07:00] create | eos-auto-clear-mechanism
Promoted from summary. Documents the flow-triggered, message-counting mechanism for auto-clearing sessions in EOS, highlighting its efficiency benefits.

## [2026-04-11T03:14:05-07:00] create | eos-architectural-preservation
Promoted from summary. Explains the decision to implement presentation and lifecycle layers on top of the existing EOS pipeline without modifying the hot path, ensuring architecture preservation.
>>>>>>> Stashed changes
