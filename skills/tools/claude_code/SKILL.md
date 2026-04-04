---
name: claude_code
description: "Use when any agent needs to execute code changes, run shell commands, manage files, dispatch subagents, or leverage Claude Code's agentic development capabilities."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://docs.anthropic.com/en/docs/claude-code"
last_researched: "2026-04-04"
instantiated_from: templates/tools/_template/
api_version: "Claude Code CLI (latest)"
sdk_version: "claude-agent-sdk (npm @anthropic-ai/claude-code)"
speed_category: "fast"
---

# Tool: Claude Code

## What This Tool Does

Claude Code is an agentic CLI by Anthropic that reads, writes, and edits files, runs bash commands, searches codebases, and executes multi-step development tasks autonomously. It is the Developer Agent's execution environment — the interface through which EOS is built and maintained.

Core capabilities:
- **File operations** — Read, Write, Edit, Glob, Grep tools
- **Bash execution** — shell commands with sandboxing
- **Subagent dispatch** — parallel agents for independent tasks
- **MCP integration** — connects to external tool servers
- **Session persistence** — conversation context survives across turns
- **Plan mode** — structured planning before execution
- **Skills** — reusable prompt templates in .claude/skills/
- **Hooks** — automated actions on tool events
- **Memory** — persistent notes across sessions

Additionally, EOS integrates Claude Code as an LLM provider via the **Claude Code Agent SDK** (`cc_sdk.py`), allowing EOS services running in Docker to query Claude through the CLI's subprocess transport.

## EOS Integration

### As Developer Agent execution environment
Claude Code IS the Developer Agent. Every build, deploy, debug, and refactor happens through Claude Code. The project structure at `/opt/OS/` provides context:
- `/opt/OS/CLAUDE.md` — primary soul document and conventions
- `/opt/OS/.claude/CLAUDE.md` — session protocols and risk classes
- `/opt/OS/.claude/skills/` — deployment and agent workflows
- `/opt/OS/.claude/rules/` — Python, agent, and skill rules

### As LLM provider via CC SDK (`eos_ai/cc_sdk.py`)
```python
from eos_ai.cc_sdk import query_cc_sync, CCResult

result = query_cc_sync(
    prompt="Analyze this business situation",
    system="You are a business analyst.",
    task_type="analyze",        # maps to effort level
    agent_id="sales_agent",     # persists session
    max_budget_usd=0.10,        # cost cap
    timeout=30.0,               # seconds
)
if result:
    print(result.output)        # response text
    print(result.session_id)    # for session continuity
    print(result.latency_ms)    # timing
```

**Position in fallback chain:** CC SDK is priority 0 (highest) in model_router.py.
Quality score: highest available (uses whatever model Claude Code is configured for).

### Agents that use it
- Developer Agent (directly — this IS Claude Code)
- All EOS agents (indirectly — via cc_sdk provider in model_router)

## Authentication

Claude Code authenticates via OAuth to claude.ai or via an Anthropic API key.

```bash
# Login (interactive — run once on VPS)
claude login

# Or set API key
export ANTHROPIC_API_KEY=sk-ant-api03-...
```

EOS VPS: Claude Code is authenticated via OAuth. The session persists in `~/.claude/`.

For CC SDK in Docker: containers mount `~/.claude` read-only to access the auth state:
```yaml
volumes:
  - /root/.claude:/root/.claude:ro
  - /root/.claude.json:/root/.claude.json:ro
```

## Quick Reference

### CLI commands
```bash
claude                           # interactive mode
claude "do something"            # one-shot with prompt
claude -p "prompt"               # print mode (no conversation)
claude --resume                  # resume last session
claude --model opus              # model override
claude --allowedTools "Read,Bash" # restrict tools

# Settings
claude config set --global model opus
claude config set --global theme dark

# MCP
claude mcp add server-name -- command args
claude mcp list
```

### Skills (EOS workflows)
Located in `/opt/OS/.claude/skills/`:
- `deploy-service.md` — deploy decision tree
- `new-agent.md` — agent creation checklist
- `new-skill.md` — skill creation checklist
- `new-primitive.md` — business primitive checklist
- `debug-agent.md` — agent debugging steps

### CC SDK integration
```python
# In model_router.py — CC SDK is provider priority 0
from eos_ai.cc_sdk import query_cc_sync

# Task type → effort mapping
EFFORT_MAP = {
    "analyze": "high",
    "fast_response": "low",
    "generate": "medium",
    "code": "high",
}

# Nested session detection prevents infinite loops
if os.environ.get("CLAUDE_CODE_SESSION"):
    return None  # skip CC SDK, use next provider
```

## Gotchas

### CC SDK requires CLI auth (ACTIVE)
Docker containers need access to Claude Code's auth state. Mount `~/.claude` and `~/.claude.json` read-only. Without auth, CC SDK returns None and falls through to Anthropic API.

### Nested session detection (BY DESIGN)
If EOS is already running inside a Claude Code session (CLAUDE_CODE_SESSION env var set), cc_sdk.py skips the CC SDK provider to avoid infinite recursion. This is correct — it means the interactive Developer Agent session doesn't try to spawn a CC SDK subprocess.

### CLI exit code 1 with valid output (KNOWN)
CC SDK CLI sometimes exits with code 1 after delivering a valid response (MCP server shutdown errors). cc_sdk.py handles this: if output_parts is non-empty, treats as success with a warning.

### Budget cap defaults to $0.10 per call
CC SDK enforces `max_budget_usd` to prevent runaway costs. Fast tasks get $0.05 cap. This may be too low for complex analysis — increase for strategic tasks.

### Session persistence per agent
cc_sdk.py maintains `_agent_sessions` dict mapping agent_id → session_id. This allows agents to resume prior conversations. Session state is in-memory only — lost on process restart.

See references/best_practices.md for Claude Code internals, skill patterns, and advanced usage.
