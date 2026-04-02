---
name: claude-code-best-practices
description: "Load before ANY Claude Code configuration change, infrastructure build, hook addition, skill creation, settings update, or agent modification. Product of applying the best-practices-principle to Claude Code. Self-updating when CC version changes or Boris posts new patterns."
allowed-tools: "Read, WebFetch, WebSearch, Bash"
effort: high
trigger: both
version: "1.0"
cc_version_at_research: "2.1.90"
last_researched: "2026-04-02"
boris_threads_captured: "Jan 2 – Mar 30 2026"
source_boris: "https://howborisusesclaudecode.com"
source_docs: "https://code.claude.com/docs/en"
---

# Claude Code Best Practices for EOS

This skill is the result of applying
/best-practices-principle to Claude Code.
Research source: Boris Cherny (creator,
Head of Claude Code at Anthropic) +
official Anthropic documentation.

!`claude --version 2>/dev/null | head -1`
!`python3 -c "
import json
try:
    with open('/opt/OS/.claude/settings.json') as f:
        s = json.load(f)
    hooks = s.get('hooks', {})
    print('Model:', s.get('model','?'))
    print('Hooks:', list(hooks.keys()))
    print('AutoMemory:', s.get('autoMemoryEnabled'))
    print('AutoDream:', s.get('autoDreamEnabled'))
except Exception as e:
    print('Settings error:', e)
" 2>/dev/null`

## When This Skill Is Stale

Check: does the version above match
cc_version_at_research in frontmatter?

If different: run /check-cc-updates before
proceeding. The skill may be missing new
capabilities or changed patterns.

## Boris Cherny — Non-Negotiables

Boris is the creator and Head of Claude Code
at Anthropic. His workflow is ground truth
for how CC is meant to be used.

### #1: Verification Before Anything Else

"Give Claude a way to verify its output.
2-3x quality improvement."

Implementation in EOS:
Every agent task needs verification before
TaskCompleted fires.
eos-verifier subagent: runs after every change.
TaskCompleted hook: verify before marking done.

### #2: Opus With Thinking Always

"Less steering + better tool use = faster
overall even though slower per token."

Implementation:
settings.json: model: "opus"
CEO agents: agent_type='ceo' forces Opus
opusplan: Opus in plan mode,
  Sonnet in execution (cost-efficient)
Never downgrade for speed.

### #3: CLAUDE.md as Living Document

Every mistake — rule added immediately.
Under 200 lines or it gets ignored.
@imports for modular content.
Checked into git. Team contributes.

### #4: Plan Mode First

Shift+Tab twice — plan mode.
Iterate until plan is solid.
Second Claude reviews as staff engineer.
Then auto-accept. Claude 1-shots it.

### #5: Slash Commands for Inner Loops

Every daily workflow — slash command.
Location: .claude/commands/ (git-tracked).
EOS required: /morning-brief, /eod-sync,
/constraint-check, /run-outreach,
/commit-push-pr, /icp-check.

### #6: Subagents for PR Workflows

code-simplifier — after every implementation.
verify-app — E2E before marking done.
EOS equivalents in .claude/agents/:
eos-simplifier, eos-verifier,
eos-code-reviewer, eos-researcher.

### #7: /loop for Recurring Tasks

EOS loops needed:
/loop 5m check_pending_tasks
/loop 15m check_dm_replies
/loop daily check_cc_version
/loop every morning run_morning_intel

### #8: Remote Control Always On

/config — Enable Remote Control for all sessions.
Control VPS from iPhone. Always on.

### #9: Parallel Sessions

claude -w — new worktree session.
Shell aliases: za, zb, zc.
5 terminal + 5-10 web sessions.

### #10: --bare for All Scripted Calls

All claude -p subprocess calls:
claude --bare -p "prompt" \
  --output-format text \
  --model claude-opus-4-6
"Up to 10x faster startup."

## Official Docs — Required Configuration

### settings.json Must Have

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "model": "opus",
  "autoMemoryEnabled": true,
  "autoDreamEnabled": true,
  "showThinkingSummaries": false,
  "permissions": {
    "defaultMode": "acceptEdits"
  },
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1",
    "CLAUDE_CODE_ENABLE_TELEMETRY": "1",
    "MCP_CONNECTION_NONBLOCKING": "true"
  }
}
```

### Required Hooks

- PostToolUse(Edit|Write): ruff format
- PostToolUse(Edit|Write): audit log append
- SessionStart: inject venture context + version check
- PermissionRequest: route to Telegram
- Stop: exit 2 for long-running tasks
- TaskCompleted: verify before marking done
- SubagentStart: inject agent-type context
- PostCompact: reload critical context

### .claude/ Structure Required

```
.claude/
  settings.json
  settings.local.json (gitignored)
  CLAUDE.md
  CLAUDE.local.md (gitignored)
  agents/
    eos-researcher.md (context: fork)
    eos-code-reviewer.md (adversarial)
    eos-verifier.md (Boris #1)
    eos-simplifier.md (post-impl)
  rules/
    python.md (globs: eos_ai/**)
    skills.md (globs: skills/**)
    agents.md (globs: agents/**)
  commands/
    morning-brief.md
    eod-sync.md
    constraint-check.md
    run-outreach.md
    commit-push-pr.md
```

### Skill Frontmatter — All Required Fields

```yaml
name: skill-name
description: "Trigger condition not description"
allowed-tools: "Read, Bash"
effort: high|medium|low
trigger: scheduled|conversational|both
context: fork  # for research-heavy skills
memory: user   # for skills that accumulate
```

### Skill Content — Always Include

1. Dynamic context via !command injection
2. Gotchas section (add failures over time)
3. Verification step in execution
4. References/ for detailed docs
5. Scripts/ for executable code

### Hook Event Reference

- PreToolUse — before tool (can block)
- PostToolUse — after success (can't undo)
- PostToolUseFailure — after failure
- PermissionRequest — at prompt dialog
- SessionStart — session begins
- UserPromptSubmit — before processing
- Stop — Claude finishes (exit 2 = continue)
- TaskCreated — task created (blocking)
- TaskCompleted — task done (blocking)
- SubagentStart — subagent spawns
- SubagentStop — subagent finishes
- PreCompact / PostCompact — around compaction

## EOS Current State vs Required

### Applied

- model: opus, autoMemory, autoDream
- agent teams, MCP nonblocking
- TaskCreated/TaskCompleted hooks
- 4 CC native subagents
- --bare flag
- 70+ skills loaded
- gateway fallback working
- 3 agents returning output
- PostToolUse: ruff formatter
- Stop hook: conditional exit 2
- SessionStart: dynamic context injection
- .claude/commands/ slash commands (21 total)
- context: fork on research-heavy skills
- .claude/rules/ directory (python, skills, agents)
- $schema in settings.json
- Adversarial review wired to Developer Agent

### Still Needed

- PermissionRequest — Telegram routing
- /loop skills configured
- Remote Control always-on
- !command in skills (partially done)
- effort frontmatter in all skills (partially done)
- SubagentStart context injection
- PostCompact hook
- GitHub Code Review action
- Channels (Telegram) configured
- opusplan alias

## Self-Update Protocol

This skill updates automatically when:

1. claude --version changes
2. Boris posts new patterns (weekly check)
3. Major Anthropic announcement

Update process:

1. Fetch code.claude.com/docs/en/changelog
2. Diff against cc_version_at_research
3. Fetch howborisusesclaudecode.com
4. Extract new patterns
5. Propose additions (human approves)
6. Apply approved updates
7. Bump last_researched and version

Run /check-cc-updates to trigger manually.

## Gotchas — Real EOS Failures

- claude -p hangs without CC auth.
  Fix: claude auth login --console
- --no-stream flag doesn't exist in v2.1.90.
  Remove from all subprocess calls.
- Business stage pre_revenue — economy mode
  — forces Haiku. Fix: agent_type='ceo'
- skill_registry.py used path.stem ('SKILL')
  not path.parent.name (directory name).
  Fixed. 60 skills now resolve.
- agent_runtime.py retried Anthropic 4x
  with no fallback. Fixed to use
  call_with_fallback() from model_router.py
- ANTHROPIC_API_KEY is not the same as CC auth token.
  CC = claude.ai OAuth (Max subscription).
  SDK = console.anthropic.com API key.
  Different systems. Both needed.
- team: 'ea' wrong. Use agent: 'executive_assistant'
- Stop hook exit 2 prevents Claude stopping.
  Our hook just echoes — doesn't actually
  keep agents working on long tasks.
- PostToolUse cannot modify already-executed
  tool output. Only logs and side effects.
