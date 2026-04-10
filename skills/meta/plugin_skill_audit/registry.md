# Plugin Skill Audit Registry

Generated: 2026-04-06
Source: Claude Code session-loaded plugin skill manifest (filesystem
glob blocked by E2BIG against /root/.claude/plugins; this registry
reflects the skills CC actually loaded into the active session,
which is the operative surface for trigger conflicts).

Skill names use the `plugin:skill` form CC exposes them as.
Tool allow-lists are not visible in the session manifest — see
each plugin's SKILL.md on disk if a specific allow-list is needed.

| Plugin | Skill Name | Trigger Condition | Tools | Notes |
|---|---|---|---|---|
| (builtin) | update-config | Configure CC harness via settings.json; automated "from now on" behaviors | n/a | Hooks live in settings.json |
| (builtin) | keybindings-help | User wants to customize keyboard shortcuts / ~/.claude/keybindings.json | n/a | |
| (builtin) | simplify | Review changed code for reuse, quality, efficiency | n/a | |
| (builtin) | loop | Run a prompt/slash command on a recurring interval | n/a | Default 10m |
| (builtin) | schedule | Create/list/run scheduled remote agents on cron | n/a | |
| (builtin) | claude-api | Build apps with Claude API / Anthropic SDK | n/a | Triggers on anthropic SDK imports |
| (builtin) | find-skills | Discover and install agent skills | n/a | |
| (builtin) | humanizer | Remove signs of AI-generated writing | n/a | |
| apify | apify-audience-analysis | Understand audience demographics, preferences | n/a | |
| apify | apify-competitor-intelligence | Analyze competitor strategies, content, pricing | n/a | |
| apify | apify-content-analytics | Track engagement metrics, measure campaign ROI | n/a | |
| apify | apify-influencer-discovery | Find/evaluate influencers for brand partnerships | n/a | |
| apify | apify-lead-generation | B2B/B2C leads via Google Maps scraping | n/a | Overlaps EOS apify tool skill |
| apify | apify-market-research | Analyze market conditions, geographic opportunities | n/a | |
| apify | apify-trend-analysis | Discover/track emerging trends across Google | n/a | |
| apify | apify-ultimate-scraper | Universal AI-powered web scraper | n/a | |
| superpowers | brainstorm (deprecated) | Use brainstorming instead | n/a | Deprecated alias |
| superpowers | write-plan (deprecated) | Use writing-plans instead | n/a | Deprecated alias |
| superpowers | execute-plan (deprecated) | Use executing-plans instead | n/a | Deprecated alias |
| superpowers | brainstorming | MUST use before any creative work | n/a | |
| superpowers | dispatching-parallel-agents | 2+ independent tasks that can run in parallel | n/a | |
| superpowers | executing-plans | Have a written implementation plan to execute | n/a | |
| superpowers | finishing-a-development-branch | Implementation complete, all tests pass | n/a | |
| superpowers | receiving-code-review | Receiving code review feedback | n/a | |
| superpowers | requesting-code-review | Completing tasks, implementing major changes | n/a | |
| superpowers | subagent-driven-development | Executing implementation plans with isolation | n/a | |
| superpowers | systematic-debugging | Encountering any bug, test failure | n/a | |
| superpowers | test-driven-development | Implementing any feature or bugfix | n/a | |
| superpowers | using-git-worktrees | Starting feature work needing isolation | n/a | |
| superpowers | using-superpowers | Starting any conversation | n/a | |
| superpowers | verification-before-completion | About to claim work is complete | n/a | |
| superpowers | writing-plans | Have a spec or requirements for a feature | n/a | |
| superpowers | writing-skills | Creating new skills, editing existing | n/a | Overlaps EOS skill creation rules |
| code-review | code-review | Code review a pull request | n/a | |
| claude-md-management | revise-claude-md | Update CLAUDE.md with session learnings | n/a | Could overlap EOS CLAUDE.md rules |
| claude-md-management | claude-md-improver | Audit and improve CLAUDE.md files | n/a | Could overlap EOS CLAUDE.md rules |
| agent-sdk-dev | new-sdk-app | Create/setup new Claude Agent SDK app | n/a | Overlaps EOS claude_agent_sdk tool skill |
| plugin-dev | create-plugin | Guided end-to-end plugin creation | n/a | |
| plugin-dev | agent-development | Develop CC agents | n/a | |
| plugin-dev | command-development | Develop slash commands | n/a | |
| plugin-dev | mcp-integration | Integrate MCP servers | n/a | |
| plugin-dev | plugin-settings | Plugin settings configuration | n/a | |
| plugin-dev | plugin-structure | Plugin structure scaffolding | n/a | |
| plugin-dev | skill-development | Develop CC skills | n/a | Overlaps EOS skill rules |
| plugin-dev | hook-development | Develop CC hooks | n/a | |
| posthog | dashboards | Manage PostHog dashboards | n/a | |
| posthog | docs | Search PostHog documentation | n/a | |
| posthog | errors | View PostHog error tracking data | n/a | |
| posthog | actions | Manage PostHog actions | n/a | |
| posthog | experiments | Manage PostHog A/B experiments | n/a | |
| posthog | insights | Query PostHog analytics and insights | n/a | |
| posthog | flags | List/manage PostHog feature flags | n/a | |
| posthog | llm-analytics | Track LLM and AI costs in PostHog | n/a | |
| posthog | logs | Query PostHog logs | n/a | |
| posthog | query | Run HogQL queries / NL analytics | n/a | |
| posthog | surveys | Manage PostHog surveys | n/a | |
| posthog | workspace | Manage PostHog orgs/projects | n/a | |
| posthog | search | Search across all PostHog entities | n/a | |
| posthog | analyzing-experiment-session-replays | Analyze session replays across experiments | n/a | |
| posthog | cleaning-up-stale-feature-flags | Identify/clean up stale flags | n/a | |
| posthog | exploring-llm-clusters | Investigate LLM analytics clusters | n/a | |
| posthog | instrument-error-tracking | Add PostHog error tracking | n/a | |
| posthog | instrument-feature-flags | Add PostHog feature flags | n/a | |
| posthog | instrument-integration | Add PostHog SDK integration | n/a | |
| posthog | instrument-llm-analytics | Add PostHog LLM analytics tracing | n/a | |
| posthog | instrument-logs | Add PostHog log capture | n/a | |
| posthog | exploring-llm-traces | Debug/inspect LLM/AI agent traces | n/a | |
| posthog | query-examples | HogQL query examples and reference | n/a | |
| posthog | instrument-product-analytics | Add PostHog product analytics events | n/a | |
| posthog | signals | Query document_embeddings table | n/a | |
| posthog | auditing-experiments-flags | Audit PostHog experiments and flags | n/a | |
| codex | rescue | Delegate investigation / explicit fix request to Codex | n/a | |
| codex | setup | Check whether local Codex CLI is ready | n/a | |
| codex | codex-cli-runtime | Internal contract for calling codex CLI | n/a | |
| codex | codex-result-handling | Internal: presenting Codex helper results | n/a | |
| codex | gpt-5-4-prompting | Internal: composing Codex/GPT prompts | n/a | |
| ralph-loop | cancel-ralph | Cancel active Ralph Loop | n/a | |
| ralph-loop | help | Explain Ralph Loop plugin | n/a | |
| ralph-loop | ralph-loop | Start Ralph Loop in current session | n/a | |
| pr-review-toolkit | review-pr | Comprehensive PR review using specialized agents | n/a | |
| firecrawl | skill-gen | Generate Agent Skill from documentation | n/a | |
| firecrawl | firecrawl-cli | Web operations via Firecrawl | n/a | |
| frontend-design | frontend-design | Create distinctive production-grade frontend | n/a | |
| skill-creator | skill-creator | Create/modify/improve skills | n/a | Overlaps EOS skill rules |
| claude-code-setup | claude-automation-recommender | Analyze codebase, recommend CC automation | n/a | |
| playground | playground | Create interactive HTML playgrounds | n/a | |
| chrome-devtools-mcp | chrome-devtools | Chrome DevTools via MCP for debugging | n/a | |
| chrome-devtools-mcp | a11y-debugging | Accessibility debugging via Chrome DevTools MCP | n/a | |
| chrome-devtools-mcp | troubleshooting | Chrome DevTools MCP troubleshooting | n/a | |
| chrome-devtools-mcp | debug-optimize-lcp | Debug/optimize Largest Contentful Paint | n/a | |

## Conflicts & Overlaps

EOS tool skills (under /opt/OS/skills/tools/) that overlap with plugin skill triggers:

- apify (EOS) vs apify:* (plugin) — 8 plugin skills cover scraping, lead-gen, trend, audience, competitor, influencer, content analytics, market research. EOS apify SKILL is the canonical entry; plugin skills may auto-trigger first on Apify keywords.
- claude_agent_sdk (EOS) vs agent-sdk-dev:new-sdk-app (plugin) — both fire on "new Agent SDK app"; EOS skill is the project-aware one.
- (no EOS skill) vs claude-api (builtin) — builtin triggers on `anthropic` import; EOS routes through model_router.call_with_fallback, do not let plugin skill push toward direct SDK use.
- (no EOS skill) vs posthog:* — no EOS posthog tool skill exists; plugin owns this surface.
- (no EOS skill) vs chrome-devtools-mcp:* — no EOS chrome devtools skill; plugin owns this.
- (no EOS skill) vs firecrawl:* — no EOS firecrawl skill; plugin owns this.
- skills meta-rules (/opt/OS/.claude/rules/skills.md) vs superpowers:writing-skills, skill-creator:skill-creator, plugin-dev:skill-development — three plugin skills compete to own skill authoring. EOS rules MUST override (Gotchas: SKILL.md must include trigger-style description + Gotchas section + verification step; plugin skills do not enforce these).
- CLAUDE.md authority (project + global) vs claude-md-management:revise-claude-md, claude-md-improver — plugin skills may suggest edits that conflict with EOS protocol layering (L0-L3, PROTOCOLS.md). Treat as advisory only.
- git workflow (commit-push-pr, EOS direct-to-main rule) vs superpowers:using-git-worktrees, finishing-a-development-branch — superpowers favors branch-based flow; EOS solo-founder phase commits to main.
