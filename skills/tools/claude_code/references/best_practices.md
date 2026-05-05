# Claude Code — Best Practices (Creator-Level Reference)

Source: Anthropic Documentation + Claude Code source + EOS production experience
Version: Claude Code CLI (latest, 2026-04)
Last Researched: 2026-04-04

---

## 1. Authentication

### OAuth login (primary — EOS VPS)
```bash
# Interactive login — run once per machine
claude login

# Verify auth status
claude auth status

# Logout
claude logout
```

OAuth state stored in:
- `~/.claude/` — session directory (tokens, config)
- `~/.claude.json` — root config file

### API key (alternative)
```bash
export ANTHROPIC_API_KEY=sk-ant-api03-...
```

API key takes precedence if both OAuth and key are present.
Key must start with `sk-ant-api03-` prefix.

### Docker auth mounting (CC SDK in containers)
```yaml
# docker-compose.yml — read-only mount of auth state
volumes:
  - /root/.claude:/root/.claude:ro
  - /root/.claude.json:/root/.claude.json:ro
```

Both files required. Missing either causes CC SDK to return None
and fall through to next provider in model_router.

### Auth verification
```bash
# Quick check — runs a minimal query
claude -p "echo test" --max-tokens 10

# Inside Python (CC SDK)
python3 -c "
import os
print('Auth dir exists:', os.path.isdir(os.path.expanduser('~/.claude')))
print('Config exists:', os.path.isfile(os.path.expanduser('~/.claude.json')))
"
```

---

## 2. Core Operations with Exact Signatures

### CLI modes
```bash
# Interactive mode — full conversation, tool use, file access
claude

# One-shot with prompt (starts conversation, exits after response)
claude "fix the bug in auth.py"

# Print mode — no conversation state, stdout only
claude -p "what does this function do?"

# Pipe mode — reads stdin
cat file.py | claude -p "review this code"

# Resume last session
claude --resume

# Resume specific session
claude --resume <session-id>
```

### Key CLI flags
```
--model <model>           Model override (opus, sonnet, haiku)
--max-tokens <n>          Max output tokens
--allowedTools "T1,T2"    Restrict available tools
--permission-mode <mode>  auto | plan | default | bypassPermissions
--max-turns <n>           Limit conversation turns (for scripting)
--output-format json      Machine-readable output
--verbose                 Show tool calls and reasoning
--no-cache                Disable prompt caching
--dangerously-skip-permissions  Skip all permission checks (scripting only)
```

### Configuration
```bash
# Set global config
claude config set --global model opus
claude config set --global theme dark
claude config set --global autoUpdaterStatus disabled

# Set project config
claude config set --project model sonnet

# List config
claude config list
```

Config precedence: CLI flags > project config > global config > defaults.

### MCP server management
```bash
# Add MCP server
claude mcp add <name> -- <command> [args...]

# Example: add a filesystem MCP server
claude mcp add filesystem -- npx @anthropic-ai/mcp-filesystem /path/to/dir

# List configured servers
claude mcp list

# Remove server
claude mcp remove <name>
```

MCP servers connect at session start. Timeout: 10s default.
Set `MCP_CONNECTION_NONBLOCKING=true` to prevent slow servers from blocking startup.

### Built-in tools (available to Claude inside sessions)
| Tool | Purpose |
|------|---------|
| Read | Read file contents (supports images, PDFs, notebooks) |
| Write | Create new files |
| Edit | Exact string replacement in existing files |
| Glob | Find files by pattern (`**/*.py`) |
| Grep | Search file contents (ripgrep-based) |
| Bash | Execute shell commands |
| Agent | Spawn subagent for parallel/isolated tasks |
| WebFetch | Fetch URL content |
| WebSearch | Search the web |
| NotebookEdit | Edit Jupyter notebook cells |
| TaskCreate/Update | Track work progress |

### Agent SDK (Node.js — `@anthropic-ai/claude-code`)
```typescript
import { query, ClaudeAgentOptions } from "@anthropic-ai/claude-code";

const options: ClaudeAgentOptions = {
  systemPrompt: "You are a code reviewer.",
  maxBudgetUsd: 0.10,
  permissionMode: "auto",
  maxTurns: 5,
  cliPath: "/usr/bin/claude",  // or "claude" if on PATH
  settingSources: [],           // skip reading .claude/settings.json
};

for await (const message of query({ prompt: "Review auth.py", options })) {
  if (message.type === "assistant") {
    for (const block of message.content) {
      if (block.type === "text") console.log(block.text);
    }
  }
  if (message.type === "result") {
    console.log("Session:", message.sessionId);
    console.log("Result:", message.result);
  }
}
```

### Agent SDK (Python wrapper — `eos_ai/cc_sdk.py`)
```python
from eos_ai.cc_sdk import query_cc_sync, CCResult

result: CCResult | None = query_cc_sync(
    prompt="Analyze this business situation",
    system="You are a business analyst.",        # optional system prompt
    task_type="analyze",                          # analyze|fast_response|generate|code
    session_id=None,                              # explicit session or auto-persist
    max_budget_usd=0.10,                          # hard cost cap per call
    agent_id="sales_agent",                       # persists session across calls
    timeout=30.0,                                 # seconds
)

if result:
    result.output        # str — response text
    result.session_id    # str — for session continuity
    result.latency_ms    # int — timing
    result.provider      # str — always "cc_sdk"
    result.model         # str — model that responded
```

---

## 3. Pagination Patterns

Claude Code does not use traditional pagination. Context management is handled via:

### Conversation compression
When context window approaches limits, older messages are automatically compressed
into summaries. The system inserts a "summary of prior conversation" block.
This is transparent — no user action required.

### File reading pagination
```python
# Read specific line range (for large files)
Read(file_path="/path/to/file.py", offset=100, limit=50)  # lines 100-150

# PDF page range
Read(file_path="/path/to/doc.pdf", pages="1-5")  # max 20 pages per request
```

### Search result limits
```python
# Grep head_limit (default 250 lines)
Grep(pattern="TODO", head_limit=50)

# Grep with offset for pagination
Grep(pattern="TODO", offset=50, head_limit=50)  # results 51-100
```

### Subagent context isolation
Large result sets should be delegated to subagents to avoid polluting
the main conversation context. The subagent processes the data and
returns only the relevant summary.

---

## 4. Rate Limits

### Claude Code CLI
- No explicit rate limit documentation — uses underlying Anthropic API limits
- OAuth (claude.ai) sessions: subject to Claude Pro/Max plan usage limits
- API key sessions: subject to Anthropic API tier rate limits

### CC SDK budget caps
```python
# Default: $0.10 per call
max_budget_usd=0.10

# Fast tasks auto-capped to $0.05
if task_type == "fast_response":
    max_budget_usd = min(max_budget_usd, 0.05)

# Strategic tasks may need higher budgets
max_budget_usd=0.50  # for complex analysis
```

### MCP server timeouts
```bash
# Default connection timeout: 10s
# Set via environment:
MCP_CONNECTION_NONBLOCKING=true  # don't block session start

# Per-tool timeout: controlled by MCP server implementation
# Claude Code default tool execution: 120s (Bash tool)
```

### Subagent limits
- No hard limit on concurrent subagents
- Each subagent consumes its own context window
- Practical limit: memory and API throughput
- Max Bash tool timeout: 600,000ms (10 minutes)

---

## 5. Error Codes and Recovery

### CLI exit codes
| Code | Meaning | Recovery |
|------|---------|----------|
| 0 | Success | — |
| 1 | General error (may include valid output) | Check stdout — CC SDK handles this |
| 2 | Invalid arguments | Fix CLI flags |
| Non-zero | Process killed / timeout | Retry with higher timeout |

### CC SDK error handling (from `cc_sdk.py`)
```python
# Rate limit detection
if "rate" in err_str or "429" in err_str:
    logger.warning("cc_sdk: rate limited")
    return None  # model_router tries next provider

# Auth error detection
if "auth" in err_str or "401" in err_str or "key" in err_str:
    logger.warning("cc_sdk: auth error")
    return None  # falls through to Anthropic direct

# Timeout handling
if "timeout" in err_str or "timed out" in err_str:
    logger.warning("cc_sdk: timeout")
    return None

# Partial output on timeout — still usable
except asyncio.TimeoutError:
    if output_parts:
        # Treat partial as success with warning
        pass
    else:
        return None
```

### Common session errors
| Error | Cause | Fix |
|-------|-------|-----|
| "File has not been read yet" | Write/Edit without prior Read | Read the file first in the same conversation |
| "old_string not found" | Edit string doesn't match file | Re-Read file, use exact string including whitespace |
| MCP connection timeout | Server not responding | Set `MCP_CONNECTION_NONBLOCKING=true` |
| "Permission denied" | Tool not in allowedTools | Add tool to `--allowedTools` flag |
| Context overflow | Conversation too long | Use subagents, or start new session with `--resume` |

---

## 6. SDK Idioms

### CLAUDE.md hierarchy (project context injection)
```
~/.claude/CLAUDE.md                    # Global user instructions (all projects)
/opt/OS/CLAUDE.md                      # Project instructions (checked in)
/opt/OS/CLAUDE.local.md                # Local overrides (gitignored)
/opt/OS/.claude/CLAUDE.md              # .claude-specific context
/opt/OS/.claude/rules/*.md             # Rule files (auto-loaded by Claude Code)
/opt/OS/.claude/skills/*.md            # Skill files (invoked via Skill tool)
```

**Priority**: User private > project root > .claude dir > rules.
All `.md` files in `.claude/rules/` are loaded automatically.
Skills are loaded on-demand via the Skill tool.

### Skills pattern (reusable workflows)
```markdown
# .claude/skills/deploy-service.md
Invoked via: Skill("deploy-service")

Skills are prompt templates that encode repeatable workflows.
They get injected into the conversation when invoked.
The agent then follows the skill instructions.
```

### Rules pattern (always-on constraints)
```markdown
# .claude/rules/python.md
Rules are loaded at session start, every session.
They act as persistent constraints on agent behavior.
Use for: coding standards, conventions, safety rules.
```

### Memory pattern (cross-session persistence)
```
/root/.claude/projects/-opt-OS/memory/MEMORY.md   # Index file
/root/.claude/projects/-opt-OS/memory/*.md         # Individual memories

Memory files use frontmatter: name, description, type (user|feedback|project|reference)
MEMORY.md is an index — one line per entry, under 150 chars.
```

### Session state pattern (within-session resume)
```python
# EOS-specific session state (not built into Claude Code)
from eos_ai.session_state import SessionState

# Save at end of significant work
SessionState.save(
    phase="tool_mastery",
    last_completed="docker best_practices.md",
    in_progress=None,
    next_steps=["ollama best_practices.md"],
    files_modified=["skills/tools/docker/references/best_practices.md"],
)

# Resume at session start
print(SessionState.get_resume_context())
```

### Subagent dispatch pattern
```python
# In Claude Code, subagents are dispatched via the Agent tool:
Agent(
    prompt="Search for all TODO comments in eos_ai/",
    subagent_type="Explore",         # specialized agent type
    description="Find TODOs",        # 3-5 word summary
    run_in_background=True,          # non-blocking
)

# Key subagent types:
# - general-purpose: multi-step tasks, code changes
# - Explore: fast codebase search and exploration
# - Plan: architecture and design planning
# - eos-verifier: verification after implementation
# - eos-code-reviewer: adversarial code review
# - eos-simplifier: code simplification review
```

---

## 7. Anti-Patterns

### 1. Writing without reading
```python
# WRONG — assumes file contents
Write(file_path="auth.py", content="...")

# RIGHT — always read first
Read(file_path="auth.py")
# Then use Edit for targeted changes, or Write for full rewrite
```

### 2. Using Bash for file operations
```bash
# WRONG
cat file.py        # Use Read tool
grep "pattern" .   # Use Grep tool
find . -name "*.py"  # Use Glob tool
sed -i 's/old/new/' file.py  # Use Edit tool

# RIGHT — use dedicated tools
Read(file_path="file.py")
Grep(pattern="pattern")
Glob(pattern="**/*.py")
Edit(file_path="file.py", old_string="old", new_string="new")
```

### 3. Monolithic subagent prompts
```python
# WRONG — dumps entire context into subagent
Agent(prompt="Here's everything about the project... now fix the bug")

# RIGHT — focused prompt with specific instructions
Agent(prompt="In /opt/OS/eos_ai/model_router.py, the _call_ollama method "
             "at line 450 has a timeout of 10s that's too low for 7b models. "
             "Change it to 30s. Verify the edit compiles.")
```

### 4. Unnecessary Docker rebuilds
```python
# WRONG — rebuilding for Python-only changes
docker compose build --no-cache os-discord

# RIGHT — Python files are bind-mounted, just restart
docker restart os-discord
```

### 5. Skipping verification
```python
# WRONG — edit and move on
Edit(file_path="module.py", ...)
# "Done!"

# RIGHT — always verify
Edit(file_path="module.py", ...)
Bash("python3 -m py_compile /opt/OS/eos_ai/module.py")
Bash("python3 -c \"import sys; sys.path.insert(0,'/opt/OS'); from eos_ai.module import Class; print('ok')\"")
```

### 6. Hardcoding in CLAUDE.md what belongs in code
```markdown
# WRONG — putting process logic in CLAUDE.md
"When deploying, run these 7 commands in this exact order..."

# RIGHT — put it in a skill
# .claude/skills/deploy-service.md contains the decision tree
# CLAUDE.md just says: "Use deploy-service skill"
```

### 7. Amending commits after hook failure
```bash
# WRONG — hook failed, commit didn't happen, --amend modifies PREVIOUS commit
git commit --amend -m "fix"  # DESTROYS previous commit's changes

# RIGHT — fix issue, re-stage, NEW commit
git add fixed_file.py
git commit -m "fix: resolve lint issue"
```

### 8. Parallel tool calls with dependencies
```python
# WRONG — Edit depends on Read result
Read(file_path="a.py")  # parallel with:
Edit(file_path="a.py", old_string="foo")  # can't know content yet

# RIGHT — sequential when dependent
Read(file_path="a.py")  # wait for result
# Then:
Edit(file_path="a.py", old_string="actual content from read")
```

### 9. Ignoring subagent context isolation
```python
# WRONG — subagent has no session history
Agent(prompt="Based on what we discussed, fix it")

# RIGHT — self-contained prompt
Agent(prompt="In /opt/OS/services/discord_bot.py line 45, "
             "the on_message handler doesn't check for bot messages. "
             "Add 'if message.author.bot: return' as the first line.")
```

### 10. Force-pushing without user confirmation
```bash
# WRONG — destructive, affects shared state
git push --force origin main

# RIGHT — always confirm with user first
# "The branch has diverged. Force push will overwrite remote. Proceed?"
```

---

## 8. Data Model

### Project structure (Claude Code perspective)
```
/opt/OS/                              # Project root
  CLAUDE.md                           # Soul document + conventions
  CLAUDE.local.md                     # Local overrides (gitignored)
  ARCHITECTURE.md                     # System architecture
  PHILOSOPHY.md                       # Design philosophy
  PROTOCOLS.md                        # L0-L3 protocol layers
  .claude/
    CLAUDE.md                         # Session protocols, risk classes
    settings.json                     # Tool permissions, MCP config
    rules/                            # Auto-loaded rule files
      agents.md
      python.md
      skills.md
    skills/                           # On-demand workflow templates
      deploy-service.md
      new-agent.md
      new-skill.md
      new-primitive.md
      debug-agent.md
    agents/                           # CC native subagent definitions
      *.md                            # Each has frontmatter: name, model, tools
  eos_ai/                             # Core AI modules
  services/                           # Running services
  skills/                             # EOS skill library
    tools/                            # Tool mastery skills
    meta/                             # Meta-skills (tool_mastery_engine, etc.)
```

### CC SDK data flow
```
User/Agent request
  → model_router.call_with_fallback()
    → [HEAVY PATH] query_cc_sync(prompt, system, task_type)
      → cc_sdk.query_cc() [async]
        → claude_agent_sdk.query(prompt, options)
          → Claude Code CLI subprocess
            → Claude API (Opus/Sonnet/Haiku per CC_MODEL_MAP)
          ← AssistantMessage (content blocks)
          ← ResultMessage (session_id, result)
        ← CCResult(output, session_id, latency_ms)
      ← return to model_router
    → [FAST PATH] _call_anthropic(Haiku) → escalate to cc_sdk if quality < 0.65
    → [FALLBACK] Gemini → Ollama
  ← RoutingResult(output, provider, model, task_type, latency_ms)
```

### Session persistence model
```python
# Per-agent session persistence (in-memory only)
_agent_sessions: dict[str, str] = {}
# Key: agent_id (e.g., "sales_agent")
# Value: session_id (Claude Code session UUID)

# Session resolution order:
# 1. Explicit session_id parameter
# 2. Persisted session for agent_id
# 3. None (new session)

# Lost on process restart — no disk persistence
```

---

## 9. Webhooks and Events (Hooks System)

Claude Code hooks execute shell commands in response to tool events.

### Hook types
| Hook | Trigger | Use case |
|------|---------|----------|
| `PreToolUse` | Before any tool executes | Validation, permission checks |
| `PostToolUse` | After any tool executes | Logging, side effects |
| `UserPromptSubmit` | When user sends a message | Context injection, preprocessing |
| `Stop` | When Claude stops generating | Post-processing, notifications |
| `SubagentStop` | When a subagent completes | Result collection |

### Hook configuration (settings.json)
```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "",
        "command": "/opt/OS/scripts/session_start_hook.sh"
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Bash",
        "command": "/opt/OS/scripts/validate_bash.sh $TOOL_INPUT"
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write",
        "command": "/opt/OS/scripts/after_write.sh $FILE_PATH"
      }
    ]
  }
}
```

### Hook behavior
- Hooks run as shell commands in the project directory
- `matcher` filters which tool triggers the hook (empty = all tools)
- Hook stdout is injected as `<user-prompt-submit-hook>` context
- If a hook exits non-zero, the tool call is blocked
- Hook feedback is treated as coming from the user
- Hooks run synchronously — keep them fast

### EOS session start hook
```bash
# scripts/session_start_hook.sh — injected on every user prompt
# Outputs system health, pending tasks, intelligence status
# Result appears as <system-reminder> in conversation
```

---

## 10. Limits

### Context window
- Claude Code manages context automatically
- Older messages compressed when approaching limits
- No explicit token limit exposed to user
- Subagents get fresh context windows

### File operations
- Read: up to 2000 lines by default (configurable via `limit`)
- PDF: max 20 pages per Read call
- Glob: no hard limit, sorted by modification time
- Grep: default 250 results (configurable via `head_limit`)

### Bash execution
- Default timeout: 120,000ms (2 minutes)
- Max timeout: 600,000ms (10 minutes)
- Background commands supported via `run_in_background`

### Memory
- MEMORY.md index: lines after 200 truncated
- Individual memory files: no hard limit but keep concise
- Memory loaded at conversation start — large indexes waste context

### CC SDK per-call limits
```python
max_budget_usd=0.10      # default cost cap
max_turns=1               # single turn in EOS (no tool use)
timeout=30.0              # seconds
# Fast tasks: max_budget_usd capped at $0.05
```

---

## 11. Cost Model

### Claude Code CLI
- **Claude Pro** ($20/month): includes Claude Code usage
- **Claude Max** ($100-200/month): higher limits, Opus access
- **API key**: standard Anthropic API pricing applies

### CC SDK cost tracking
```python
# Budget enforcement per call
max_budget_usd=0.10  # hard cap — CLI refuses to exceed

# EFFORT_MAP determines model selection (indirectly affects cost)
EFFORT_MAP = {
    "analyze": "high",        # → Opus ($15/$75 per 1M tokens)
    "fast_response": "low",   # → capped at $0.05
    "generate": "medium",     # → Sonnet ($3/$15 per 1M tokens)
    "code": "high",           # → Opus
}
```

### EOS cost optimization
- CC SDK is "free" with Claude Max subscription (OAuth auth)
- API key fallback uses standard Anthropic pricing
- `economy_mode` in model_preferences.py forces Haiku for pre_revenue stage
- Override: `agent_type='ceo'` or `force_opus=True` for strategic tasks

### Model router quality-cost tradeoff
```python
# Provider quality scores (used for routing decisions)
PROVIDER_QUALITY = {
    "cc_sdk": 0.85,     # Highest quality, "free" via Max
    "anthropic": 0.80,  # Direct API, pay-per-token
    "gemini": 0.65,     # Cheaper but lower quality
    "ollama": 0.30,     # Free but lowest quality
}
```

---

## 12. Version Pinning

### CLI version management
```bash
# Check version
claude --version

# Update (npm global install)
npm update -g @anthropic-ai/claude-code

# Pin in Dockerfile
RUN npm install -g @anthropic-ai/claude-code@latest
# Note: EOS Dockerfile uses @latest — no version pin
```

### Agent SDK version
```bash
# Node.js SDK
npm install @anthropic-ai/claude-code

# Python wrapper (cc_sdk.py) imports from Node SDK at runtime:
from claude_agent_sdk import ClaudeAgentOptions, query
# This is a Python binding of the Node SDK
```

### Model version pinning
```python
# CC_MODEL_MAP in model_router.py uses explicit model versions
CC_MODEL_MAP = {
    TaskType.STRATEGIC: "claude-opus-4-6",
    TaskType.CODE: "claude-opus-4-6",
    TaskType.PLAN: "claude-opus-4-6",
    TaskType.ANALYZE: "claude-sonnet-4-6",
    TaskType.GENERATE: "claude-sonnet-4-6",
    TaskType.RESEARCH: "claude-sonnet-4-6",
    TaskType.SCORE: "claude-haiku-4-5-20251001",
    TaskType.CLASSIFY: "claude-haiku-4-5-20251001",
    TaskType.FAST_RESPONSE: "claude-haiku-4-5-20251001",
}
# Pin to exact model IDs — never use aliases like "opus" in production code
```

### Settings version
```json
// .claude/settings.json — no explicit versioning
// Changes take effect on next session start
// Back up before major changes:
// cp .claude/settings.json .claude/settings.json.bak
```

---

## 13. Design Intent and Tradeoffs

### Why Claude Code exists
Claude Code bridges the gap between "AI that writes code" and "AI that builds software."
Traditional code assistants generate snippets. Claude Code operates as a full development
agent — reading codebases, executing commands, managing files, making architectural decisions.

### Key design decisions

**Direct tool access over abstraction layers**: Claude Code gives the model direct access
to Read, Write, Edit, Bash, etc. No intermediate API. This means the model can compose
tool calls naturally — read a file, understand it, edit precisely. The tradeoff: the model
must manage its own tool sequencing (can't Edit before Read).

**CLAUDE.md as persistent memory**: Instead of training on project specifics, Claude Code
loads CLAUDE.md at session start. This means project context is explicit, versionable,
and editable by humans. Tradeoff: context window cost for every session.

**Skills as reusable prompts**: Skills are not code — they're structured prompt templates
that encode workflows. This means they're easy to write and modify (just markdown), but
they depend on the model's ability to follow instructions. No enforcement mechanism.

**Subagents for isolation**: Rather than one monolithic context, Claude Code supports
spawning subagents with fresh context. This solves context pollution but introduces
coordination overhead — subagents don't share state.

**Permission modes as trust spectrum**: From `default` (ask for everything) to
`bypassPermissions` (ask for nothing). This lets users calibrate trust. EOS uses `auto`
for CC SDK calls (no human in the loop for agent-initiated queries).

### Architectural philosophy
Claude Code is opinionated about developer experience:
- Tools should map to developer mental models (Read/Write/Edit, not "file operations API")
- Context should be explicit (CLAUDE.md) not implicit (training data)
- Verification should be built into workflows (import checks, test runs)
- Parallel execution should be natural (multiple tool calls in one response)

---

## 14. Problem-Solution Map and Hidden Capabilities

### Context window management
**Problem**: Long conversations degrade quality.
**Solution**: Dispatch subagents for isolated tasks. Each gets a fresh window.
Use `run_in_background=True` for non-blocking parallel work.

### Large file editing
**Problem**: Need to modify a 3000-line file.
**Solution**: Read with `offset` and `limit` to target the section.
Edit with `old_string` that includes enough context to be unique.
Never read the entire file if you only need 50 lines.

### Multi-file refactoring
**Problem**: Renaming a function used in 20 files.
**Solution**: `Grep(pattern="old_name")` to find all occurrences.
`Edit(file_path=..., old_string="old_name", new_string="new_name", replace_all=True)`
per file. Verify with `Grep(pattern="old_name")` — should return 0 results.

### Interactive commands
**Problem**: Claude Code can't handle interactive prompts (e.g., `gcloud auth login`).
**Solution**: User runs `! <command>` in the prompt — the `!` prefix executes in the
session so output lands in the conversation.

### Session continuity across conversations
**Problem**: New conversation has no memory of prior work.
**Solution**: Memory system (`/root/.claude/projects/*/memory/`) persists facts.
SessionState (`eos_ai/session_state.py`) persists build phase and progress.
`--resume` flag resumes the exact prior conversation.

### Verification of AI output (Boris Cherny principle)
**Problem**: Claude may generate incorrect code.
**Solution**: Always give Claude a way to verify. Import checks, test runs,
compile checks. Build verification into every skill as a required step.

### Hidden: Agent tool with worktree isolation
```python
Agent(
    prompt="Try the risky refactor",
    isolation="worktree",  # Creates git worktree — changes don't affect main
)
# If changes are good, they're on a separate branch to merge
# If bad, worktree is cleaned up automatically
```

### Hidden: Glob sorted by modification time
Glob results are sorted by modification time (newest first).
Useful for finding recently changed files without `git log`.

### Hidden: Grep multiline mode
```python
Grep(pattern="class Foo.*?def bar", multiline=True)
# Matches patterns that span multiple lines
```

---

## 15. Operational Behavior and Edge Cases

### CLI exit code 1 with valid output
The Claude Code CLI sometimes exits with code 1 after delivering a valid response,
typically due to MCP server shutdown errors. CC SDK handles this:
```python
# cc_sdk.py — if output_parts is non-empty, treats as success
except Exception as e:
    if output_parts:
        logger.debug("cc_sdk: CLI exited with error after response — %s", e)
        # Falls through to return valid CCResult
```

### Nested session detection
If EOS is running inside a Claude Code session (developer interacting via CLI),
cc_sdk.py detects this and skips the CC SDK provider:
```python
def _is_nested_cc_session() -> bool:
    return bool(os.environ.get("CLAUDE_CODE_SESSION"))
```
This prevents infinite recursion: Claude Code CLI → CC SDK → Claude Code CLI → ...

### Conversation compression artifacts
When context is compressed, the summary may lose:
- Exact line numbers referenced earlier
- Specific error messages that were discussed
- File contents that were read but not saved to memory
**Mitigation**: Re-read files when resuming from a compressed context.
Don't reference "the file we looked at earlier" — re-read it.

### Edit tool uniqueness requirement
`Edit(old_string=...)` fails if the string appears multiple times in the file.
Solutions:
1. Include more surrounding context to make it unique
2. Use `replace_all=True` to change all occurrences
3. Use `Write` for complete file rewrites

### Write tool read-first requirement
`Write(file_path=...)` on existing files requires a `Read` of that file
earlier in the same conversation. This prevents blind overwrites.
New files don't have this requirement.

### Bash tool environment
- Working directory persists between Bash calls
- Shell state (variables, aliases) does NOT persist — each Bash call is a new shell
- Shell is initialized from user's profile (bash or zsh)
- Use absolute paths to avoid working directory confusion

### Tool call ordering
Claude Code can make multiple tool calls in a single response.
Independent calls run in parallel. Dependent calls must be sequential.
The model must declare all parallel calls in the same response message.

---

## 16. Ecosystem Position and Composition

### Where Claude Code fits
```
Developer (human)
  └── Claude Code (CLI / Desktop / Web / IDE extension)
        ├── Claude API (intelligence)
        ├── MCP servers (external tools)
        ├── Local filesystem (project)
        └── Bash (system operations)

EOS (AI business OS)
  └── model_router.py (intelligence routing)
        ├── CC SDK (priority 0 — Claude Code as provider)
        │     └── Claude Code CLI (subprocess)
        │           └── Claude API
        ├── Anthropic SDK (priority 1 — direct API)
        ├── Gemini SDK (priority 2)
        └── Ollama (priority 5 — local fallback)
```

### Interfaces

**With Anthropic API**: Claude Code uses the Anthropic API for all intelligence.
The CLI handles authentication, context management, tool routing, and streaming.
CC SDK wraps this as a provider for model_router.

**With MCP servers**: Claude Code connects to MCP servers at session start.
Servers expose tools that Claude can call like built-in tools.
EOS uses: NotebookLM MCP, Chrome DevTools MCP, Stitch MCP, GitLab MCP.

**With Git**: Claude Code reads git state for context (branch, status, recent commits).
Can create commits, branches, PRs via Bash/gh CLI. Never force-pushes without confirmation.

**With IDE extensions**: VS Code and JetBrains extensions embed Claude Code.
Same capabilities as CLI, integrated into editor UI.

---

## 17. Trajectory and Evolution

### Recent evolution (as of 2026-04)
- **Agent SDK**: Enables programmatic use of Claude Code as an LLM provider.
  EOS uses this via `cc_sdk.py` — Claude Code as priority 0 provider.
- **Hooks system**: Shell commands triggered by tool events.
  EOS uses for session start context injection.
- **Memory system**: File-based persistent memory across sessions.
  Replaces ad-hoc notes in CLAUDE.md.
- **Multi-platform**: CLI, desktop app (Mac/Windows), web (claude.ai/code), IDE extensions.
- **Model upgrades**: Opus 4.6 is the latest, with fast mode using same model.

### Expected trajectory
- Deeper MCP integration (more servers, richer tool schemas)
- Better subagent coordination (shared state, result passing)
- Improved context management (smarter compression, selective loading)
- More IDE integrations and editor-native features
- Agent-to-agent communication patterns

### Migration considerations
- Skills are pure markdown — portable across Claude Code versions
- CLAUDE.md format is stable — unlikely to break
- Agent SDK API may evolve — pin to specific npm version for production
- Hooks API is simple (shell commands) — unlikely to change significantly

---

## 18. Conceptual Model and Solution Recipes

### Mental model: Claude Code as a developer colleague
Think of Claude Code as a developer who:
- Just walked into the room (no prior context unless CLAUDE.md provides it)
- Has access to your terminal and editor
- Can read any file, run any command, but asks permission for risky operations
- Works best with clear, specific instructions
- Can delegate to junior developers (subagents) for parallel work

### Recipe: Debug a failing service
```
1. Read the error: docker logs os-discord --tail 50
2. Identify the file: Read the traceback, Grep for the error pattern
3. Read the file: Read(file_path=..., offset=error_line-10, limit=30)
4. Understand the context: Read imports, related files
5. Fix: Edit(file_path=..., old_string=..., new_string=...)
6. Verify: python3 -m py_compile, import check
7. Deploy: docker restart os-discord
8. Confirm: docker logs os-discord --tail 10
```

### Recipe: Add a new EOS agent
```
1. Load skill: Skill("new-agent")
2. Follow the 5-step checklist in the skill
3. Verify: import check, hierarchy check, Neon registration
4. Deploy: docker restart affected services
```

### Recipe: Research a tool for Tool Mastery Engine
```
1. Load skill: Skill("tool-mastery-engine")
2. Read references/research_protocol.md
3. Read references/tool_doc_registry.md for doc URLs
4. WebSearch/WebFetch official documentation
5. Read EOS code that uses the tool (Grep for imports)
6. Write SKILL.md (trigger-based description, EOS integration, gotchas)
7. Write references/best_practices.md (all 19 sections + EOS + Gotchas)
8. Verify: section count = 21 (19 standard + EOS + Gotchas)
```

### Recipe: Safe multi-service deployment
```
1. Import check: python3 -c "import sys; sys.path.insert(0,'/opt/OS'); import eos_ai"
2. Restart ONE service: docker restart os-discord
3. Wait 15 seconds
4. Check logs: docker logs os-discord --tail 10
5. Confirm healthy before moving to next service
6. Never restart all services simultaneously
```

---

## 19. Industry Expert and Cutting-Edge Usage

### CC SDK as intelligence fabric
EOS's use of CC SDK as a model_router provider is an advanced pattern:
```python
# model_router.py — CC SDK as priority 0 provider
# HEAVY PATH: cc_sdk (Opus) first, then registry fallback
if router._cc_sdk_available:
    cc_result = query_cc_sync(prompt, system, task_type, ...)
    if cc_result:
        return RoutingResult(output=cc_result.output, provider="cc_sdk", ...)
    # Falls through to Anthropic → Gemini → Ollama
```

This gives EOS Opus-level intelligence "for free" when Claude Max subscription is active,
with automatic fallback to pay-per-token providers when CC SDK is unavailable.

### Quality-gated escalation
```python
# FAST PATH: Haiku first, escalate to CC SDK if quality < 0.65
_ESCALATION_QUALITY_THRESHOLD = 0.65

if _should_escalate(output, provider):
    # Re-query via CC SDK (Opus) for higher quality
    cc_result = query_cc_sync(prompt, system, ...)
```

This pattern: try cheap first, escalate to expensive only when quality is insufficient.
Reduces cost while maintaining quality floor.

### Session persistence for agent continuity
```python
# cc_sdk.py — agents maintain conversation context across calls
_agent_sessions: dict[str, str] = {}

# First call: new session
result = query_cc_sync(prompt="What's the market like?", agent_id="market_analyst")
# _agent_sessions["market_analyst"] = result.session_id

# Second call: resumes prior conversation
result = query_cc_sync(prompt="How does that affect our pricing?", agent_id="market_analyst")
# Agent has full context of "the market" from prior call
```

### Subagent composition for complex analysis
```python
# Dispatch multiple specialized agents in parallel
Agent(prompt="Analyze code quality", subagent_type="eos-code-reviewer", run_in_background=True)
Agent(prompt="Check for simplification", subagent_type="eos-simplifier", run_in_background=True)
Agent(prompt="Verify correctness", subagent_type="eos-verifier", run_in_background=True)
# All three run concurrently, each with fresh context
# Results collected and synthesized by the orchestrating session
```

### CLAUDE.md as executable documentation
EOS treats CLAUDE.md not as documentation but as executable configuration:
- Soul documents define agent identity and behavior
- Risk classes gate which changes need validation
- Confirmed working components prevent regressions
- Rules files enforce coding standards automatically

This pattern turns project README into a living system specification
that actively shapes AI behavior every session.

---

## 20. EOS Usage Patterns

### CC SDK in model_router (primary integration)
```python
# model_router.py — two routing paths

# HEAVY PATH (analyze, generate, code, strategic):
# 1. CC SDK (Opus via Agent SDK) — "free" via Max subscription
# 2. Anthropic direct (Haiku/Sonnet) — pay per token
# 3. Gemini (Flash) — cheaper alternative
# 4. Ollama (qwen2.5) — free local fallback

# FAST PATH (fast_response, conversation, classify):
# 1. Anthropic (Haiku) — fast and cheap
# 2. Escalate to CC SDK if quality < 0.65
# 3. Gemini fallback
# 4. Ollama fallback
```

### CLAUDE.md project files
| File | Purpose | Loaded |
|------|---------|--------|
| `/opt/OS/CLAUDE.md` | Soul document, conventions, routing config | Always |
| `/opt/OS/CLAUDE.local.md` | Local preferences, working style | Always (gitignored) |
| `/opt/OS/.claude/CLAUDE.md` | Session protocols, risk classes, confirmed components | Always |
| `/opt/OS/.claude/rules/python.md` | Python coding standards | Always (auto) |
| `/opt/OS/.claude/rules/agents.md` | Agent creation rules | Always (auto) |
| `/opt/OS/.claude/rules/skills.md` | Skill creation rules | Always (auto) |
| `/opt/OS/eos_ai/CLAUDE.md` | Module-level context for eos_ai/ | When in directory |

### Skills used by Developer Agent
| Skill | Path | Purpose |
|-------|------|---------|
| deploy-service | `.claude/skills/deploy-service.md` | Service deployment decision tree |
| new-agent | `.claude/skills/new-agent.md` | 5-step agent creation checklist |
| new-skill | `.claude/skills/new-skill.md` | Skill creation + Neon sync |
| new-primitive | `.claude/skills/new-primitive.md` | Business primitive creation |
| debug-agent | `.claude/skills/debug-agent.md` | 4-step agent debugging |

### Docker auth for CC SDK
```yaml
# docker-compose.yml — os-discord service
os-discord:
  volumes:
    - /opt/OS:/app
    - /root/.claude:/root/.claude:ro        # CC auth state
    - /root/.claude.json:/root/.claude.json:ro  # CC config
  environment:
    - CLAUDE_CODE_SESSION=docker   # Marks as nested (prevents recursion)
```

---

## 21. Gotchas (Real EOS Production Issues)

### CC SDK auth requires mounted volumes (ACTIVE)
Docker containers need read-only access to `~/.claude` and `~/.claude.json`.
Without both, CC SDK returns None and falls through to next provider.
**Symptom**: All CC SDK calls fail silently, Anthropic direct becomes primary.
**Fix**: Ensure both volumes mounted in docker-compose.yml.

### Nested session infinite recursion (RESOLVED — BY DESIGN)
If the Developer Agent (running in Claude Code CLI) triggers model_router,
which calls CC SDK, which spawns another Claude Code CLI... infinite recursion.
**Fix**: `_is_nested_cc_session()` checks `CLAUDE_CODE_SESSION` env var.
Docker containers set this to "docker". Interactive sessions set it automatically.

### CLI exit code 1 with valid output (ACTIVE — KNOWN)
MCP server shutdown errors cause non-zero exit after successful response.
`cc_sdk.py` checks `output_parts` — if non-empty, treats as success.
**Symptom**: Warning logs about CLI errors, but output is correct.

### Budget cap too low for complex tasks (ACTIVE)
Default `max_budget_usd=0.10` may be insufficient for strategic analysis.
Fast tasks auto-capped at $0.05.
**Symptom**: Truncated or shallow responses on complex prompts.
**Fix**: Increase `max_budget_usd` for strategic tasks (0.50+).

### Session state lost on process restart (BY DESIGN)
`_agent_sessions` dict is in-memory only. Container restart = all sessions lost.
Agents start fresh conversations after restart.
**Symptom**: Agent loses context of prior conversation after `docker restart`.
**Impact**: Low — most agent calls are single-turn anyway.

### Write tool requires Read in same conversation (ACTIVE)
Attempting to Write to an existing file without first Reading it in the current
conversation causes "File has not been read yet" error.
**Symptom**: Write fails even though you read the file in a prior session.
**Fix**: Always Read before Write. Subagents must Read within their own context.

### CLAUDE.md context window cost (BY DESIGN)
Large CLAUDE.md files consume context tokens every session. EOS has ~4KB across
all CLAUDE.md files. This is intentional — project context is worth the token cost.
**Mitigation**: Keep CLAUDE.md concise. Move detailed references to skills
(loaded on demand) rather than rules (loaded always).

### MCP server connection timeout blocks session start (RESOLVED)
Slow MCP servers can delay session start by 10+ seconds per server.
**Fix**: `MCP_CONNECTION_NONBLOCKING=true` in environment. EOS sets this in CLAUDE.md.

### Agent SDK import path confusion (ACTIVE)
The Python import `from claude_agent_sdk import ...` references a Node.js SDK
with Python bindings. If `@anthropic-ai/claude-code` is not installed globally
via npm, the import fails silently and CC SDK returns None.
**Fix**: Dockerfile includes `npm install -g @anthropic-ai/claude-code`.
Verify: `python3 -c "from claude_agent_sdk import query; print('ok')"`.

### Subagent context is completely isolated (BY DESIGN)
Subagents have no access to the parent conversation's context, tool results,
or memory. They start fresh. Prompt must be self-contained.
**Symptom**: Subagent doesn't know about files you just read or decisions you just made.
**Fix**: Include all relevant context in the subagent prompt. File paths, line numbers,
what specifically to change — not "based on what we discussed."
