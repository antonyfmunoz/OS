---
name: claude-code-best-practices
description: "Load before ANY Claude Code configuration change, infrastructure build, hook addition, skill creation, settings update, or agent modification. Product of applying the best-practices-principle to Claude Code. Self-updating when CC version changes or Boris posts new patterns."
allowed-tools: "Read, WebFetch, WebSearch, Bash"
effort: high
trigger: both
version: "2.0"
cc_version_at_research: "2.1.119"
last_researched: "2026-04-28"
boris_threads_captured: "Jan 2 – Apr 2026"
source_boris: "https://howborisusesclaudecode.com"
source_docs: "https://code.claude.com/docs/en"
source_reference: "/opt/OS/skills/tools/claude_code/references/"
context: fork
---
<!-- claude-doc: auto-maintain -->


# Claude Code Best Practices for EOS

This skill is the result of applying the Tool Mastery Engine
to Claude Code itself. The authoritative reference library
lives at `skills/tools/claude_code/references/`.
This skill distills that reference into enforceable rules.

!`claude --version 2>/dev/null | head -1`
!`python3 -c "
import json
try:
    with open('/opt/OS/.claude/settings.json') as f:
        s = json.load(f)
    hooks = s.get('hooks', {})
    schema = s.get('\$schema', 'MISSING')
    print('Model:', s.get('model','?'))
    print('Schema:', 'present' if schema != 'MISSING' else 'MISSING')
    print('Hooks:', list(hooks.keys()))
    print('AutoMemory:', s.get('autoMemoryEnabled'))
except Exception as e:
    print('Settings error:', e)
" 2>/dev/null`

## When This Skill Is Stale

Check: does the CC version above match
cc_version_at_research in frontmatter?

If different: re-read the reference library at
`skills/tools/claude_code/references/`
and run the Cascade Update Protocol below.


## Boris Cherny — Non-Negotiables

Boris is the creator and Head of Claude Code
at Anthropic. His workflow is ground truth.

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
alwaysThinkingEnabled: true (global)
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
/commit-push-pr.

### #6: Subagents for PR Workflows

code-simplifier — after every implementation.
verify-app — E2E before marking done.
EOS equivalents in .claude/agents/:
eos-simplifier, eos-verifier,
eos-code-reviewer, eos-researcher.

### #7: /loop for Recurring Tasks

EOS loops:
/loop 5m check_pending_tasks
/loop 15m check_dm_replies

### #8: Remote Control Always On

/config — Enable Remote Control for all sessions.
Control VPS from iPhone. Always on.

### #9: Parallel Sessions

claude -w — new worktree session.
5 terminal + 5-10 web sessions.

### #10: --bare for All Scripted Calls

All claude -p subprocess calls:
claude --bare -p "prompt" \
  --output-format text \
  --model claude-opus-4-6
"Up to 10x faster startup."


## CC Artifact Compliance Standards

These are the enforceable standards for every CC artifact
in the EOS system. When this skill updates, ALL existing
artifacts must be audited against these standards.

### settings.json — Required Shape

Reference: `skills/tools/claude_code/references/claude-settings.md`

Required keys:
- `$schema`: `"https://json.schemastore.org/claude-code-settings.json"`
- `model`: explicit model alias
- `autoMemoryEnabled`: true
- `alwaysThinkingEnabled`: true (extended thinking every session)
- `permissions`: object with `allow`, `deny`, `defaultMode`
- `statusLine`: object with `type`, `command`, `refreshInterval`

Prohibited keys (not real CC settings):
- `autoDreamEnabled` — does not exist in CC schema
- Any key not in the CC JSON schema

Validation: `python3 -c "import json; d=json.load(open('.claude/settings.json')); assert '\$schema' in d; assert 'autoDreamEnabled' not in d; print('PASS')"`

### Skill Frontmatter — Required Fields

Reference: `skills/tools/claude_code/references/claude-skills.md`

CC-native skills (`.claude/skills/*.md`):
```yaml
---
name: skill-name
description: "Use when [trigger condition]"
allowed-tools: Tool1, Tool2
---
```

- `name` — slug, matches filename
- `description` — MUST be a trigger condition ("Use when...")
  NOT a description ("This skill does...")
- `allowed-tools` — explicit tool allowlist

TME tool skills (`skills/tools/*/SKILL.md`) have additional
fields: `version`, `source_url`, `last_researched`, `api_version`,
`sdk_version`, `speed_category`, `trigger`, `effort`, `context`.

### Subagent Frontmatter — Required Fields

Reference: `skills/tools/claude_code/references/claude-subagents.md`

```yaml
---
name: agent-name
description: "Trigger condition for auto-delegation"
model: opus|sonnet|haiku|inherit
tools: Tool1, Tool2
context: fork
memory: user
effort: high|medium|low
---
```

- `name` — unique, lowercase-hyphenated
- `description` — when CC should auto-delegate
- `tools` — explicit allowlist (inherit all if omitted)
- Verification step in body — always required

### Skill Content — Always Include

1. Dynamic context via `!command` injection
2. Gotchas section (add failures over time)
3. Verification step in execution
4. References/ for detailed docs (if applicable)

### Wiki Files (Obsidian) — Required Properties

Reference: `/opt/OS/.claude/skills/obsidian-markdown/SKILL.md`

All `.md` files in `10_Wiki/`:
- YAML frontmatter with `type` property
- `[[wikilinks]]` for internal vault navigation
- `tags` and `aliases` on human-authored files
  (auto-generated palace rooms are exempt)


## Cascade Update Protocol

When this skill updates (CC version change, new Boris
pattern, or manual trigger), ALL downstream artifacts
must be audited and fixed. This is not optional.

### What cascades to what

```
THIS SKILL (source of truth)
  ├── .claude/settings.json — validate against CC schema
  ├── ~/.claude/settings.json — validate against CC schema
  ├── .claude/skills/*.md (11 files) — validate frontmatter
  ├── .claude/agents/*.md (4 files) — validate frontmatter
  ├── .claude/commands/*.md (24 files) — validate format
  ├── .claude/rules/*.md — validate format
  ├── CLAUDE.md files — validate no stale CC references
  └── skills/tools/*/SKILL.md (96 files) — validate TME frontmatter
```

### Cascade execution

```bash
# 1. Validate settings
python3 -c "
import json, sys
for path in ['/opt/OS/.claude/settings.json', '/root/.claude/settings.json']:
    try:
        d = json.load(open(path))
        errs = []
        if '\$schema' not in d: errs.append('missing \$schema')
        if 'autoDreamEnabled' in d: errs.append('has autoDreamEnabled (not a real CC setting)')
        sl = d.get('statusLine', {})
        if sl and 'refreshInterval' not in sl: errs.append('statusLine missing refreshInterval')
        print(f'{path}: {\"FAIL: \" + \"; \".join(errs) if errs else \"PASS\"}')
    except Exception as e:
        print(f'{path}: ERROR: {e}')
"

# 2. Validate skill frontmatter
python3 -c "
import os, re
skills_dir = '/opt/OS/.claude/skills'
for f in sorted(os.listdir(skills_dir)):
    if not f.endswith('.md'): continue
    path = os.path.join(skills_dir, f)
    content = open(path).read()
    if not content.startswith('---'):
        print(f'  FAIL {f}: no frontmatter')
        continue
    parts = content.split('---', 2)
    if len(parts) < 3:
        print(f'  FAIL {f}: broken frontmatter')
        continue
    fm = parts[1]
    has_name = 'name:' in fm
    has_desc = 'description:' in fm
    desc_trigger = bool(re.search(r'description:.*[Uu]se when', fm))
    errs = []
    if not has_name: errs.append('missing name')
    if not has_desc: errs.append('missing description')
    if has_desc and not desc_trigger: errs.append('description is not a trigger condition')
    print(f'  {\"FAIL\" if errs else \"PASS\"} {f}{(\": \" + \"; \".join(errs)) if errs else \"\"}')
"

# 3. Validate subagent frontmatter
python3 -c "
import os
agents_dir = '/opt/OS/.claude/agents'
for f in sorted(os.listdir(agents_dir)):
    if not f.endswith('.md'): continue
    path = os.path.join(agents_dir, f)
    content = open(path).read()
    parts = content.split('---', 2)
    fm = parts[1] if len(parts) >= 3 else ''
    errs = []
    if 'name:' not in fm: errs.append('missing name')
    if 'description:' not in fm: errs.append('missing description')
    if 'model:' not in fm: errs.append('missing model')
    if 'tools:' not in fm: errs.append('missing tools')
    body = parts[2] if len(parts) >= 3 else content
    if 'verif' not in body.lower(): errs.append('no verification step in body')
    print(f'  {\"FAIL\" if errs else \"PASS\"} {f}{(\": \" + \"; \".join(errs)) if errs else \"\"}')
"

# 4. Validate TME tool skill frontmatter
python3 -c "
import os
tools_dir = '/opt/OS/skills/tools'
fails = 0
for d in sorted(os.listdir(tools_dir)):
    skill = os.path.join(tools_dir, d, 'SKILL.md')
    if not os.path.isfile(skill): continue
    content = open(skill).read()
    if not content.startswith('---'):
        print(f'  FAIL {d}: no frontmatter')
        fails += 1
        continue
    parts = content.split('---', 2)
    fm = parts[1] if len(parts) >= 3 else ''
    errs = []
    for key in ['name:', 'description:', 'last_researched:', 'source_url:']:
        if key not in fm: errs.append(f'missing {key.rstrip(\":\")}')
    if errs:
        print(f'  FAIL {d}: {\"; \".join(errs)}')
        fails += 1
total = len([d for d in os.listdir(tools_dir) if os.path.isfile(os.path.join(tools_dir, d, 'SKILL.md'))])
print(f'  --- {total - fails}/{total} pass')
"
```


## EOS Current State vs Required

### Applied

- model: opus, autoMemory, alwaysThinkingEnabled
- $schema in both settings files
- statusLine with refreshInterval
- agent teams, MCP nonblocking
- TaskCreated/TaskCompleted hooks
- 4 CC native subagents
- --bare flag
- 96 tool skills + 11 CC skills
- gateway fallback working
- PostToolUse: ruff formatter
- Stop hook: conditional exit 2
- SessionStart: dynamic context injection
- .claude/commands/ slash commands (24 total)
- context: fork on research-heavy skills
- .claude/rules/ directory (python, skills, agents)
- Adversarial review wired to Developer Agent
- All 11 .claude/skills/ have frontmatter (v2.0)
- 5 external skills absorbed into TME (obsidian-markdown, obsidian-bases, obsidian-cli, json-canvas, defuddle)
- 2 duplicate .claude/skills/ removed (notebooklm, ollama — TME authoritative)
- 10_Wiki wikilinks (v2.0)

### Remaining Gaps

- GitHub Code Review action
- Palace room auto-generated frontmatter (tags/aliases)
  requires build_palace.py modification


## Self-Update Protocol

This skill updates when:

1. claude --version changes
2. Boris posts new patterns (weekly check)
3. Major Anthropic announcement
4. CC reference library at `skills/tools/claude_code/` updates

Update process:

1. Read `skills/tools/claude_code/references/claude-settings.md`
2. Read `skills/tools/claude_code/references/claude-skills.md`
3. Read `skills/tools/claude_code/references/claude-subagents.md`
4. Diff against current standards in this skill
5. Update this skill's standards
6. Run Cascade Update Protocol (above)
7. Bump last_researched, cc_version_at_research, version

Run /check-cc-updates to trigger manually.


## Gotchas — Real EOS Failures

- `autoDreamEnabled` was in settings.json for months. Not a real CC setting.
  Caused by this skill teaching it as required (v1.0). Fixed in v2.0.
  Root cause: skill was stale (v2.1.90 → v2.1.119 gap). Cascade protocol
  now exists to prevent recurrence.
- claude -p hangs without CC auth.
  Fix: claude auth login --console
- --no-stream flag doesn't exist.
  Remove from all subprocess calls.
- Business stage pre_revenue — economy mode — forces Haiku.
  Fix: agent_type='ceo'
- skill_registry.py used path.stem ('SKILL') not path.parent.name.
  Fixed. 91 skills now resolve.
- ANTHROPIC_API_KEY is not CC auth token.
  CC = claude.ai OAuth (Max subscription).
  SDK = console.anthropic.com API key.
  Different systems. Both needed.
- Stop hook exit 2 prevents Claude stopping.
  Our hook just echoes — doesn't actually
  keep agents working on long tasks.
- PostToolUse cannot modify already-executed
  tool output. Only logs and side effects.
- .claude/skills/ files without frontmatter are invisible to CC auto-discovery.
  ALL skills need at minimum: name, description (trigger condition), allowed-tools.
- Two competing CC best practice artifacts existed (meta skill + external reference).
  Resolved: meta skill is the EOS-specific enforcer, external reference is the
  authoritative CC docs. Meta skill reads external reference, not vice versa.
- Settings keys not in the CC JSON schema are silently ignored but misleading.
  Always validate against $schema. When in doubt, check references/claude-settings.md.
- Skill descriptions that describe instead of trigger ("This skill manages X")
  don't fire automatically. Must use "Use when [condition]" pattern.
