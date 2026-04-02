# Claude Code — Best Practices
Source: Anthropic Documentation + EOS experience
Last Researched: 2026-04-01

## Key Principles
- Read before write — never assume file contents
- Parallel tool calls for independent operations
- Subagents for isolated tasks (fresh context, no pollution)
- Skills (SKILL.md) for repeatable workflows

## Session Management
- CLAUDE.md provides project context loaded at session start
- Session state: use SessionState.save() / SessionState.get_resume_context()
- Memory: /root/.claude/projects/ for cross-session context

## Subagent Pattern
- Dispatch one subagent per independent phase
- Provide complete context in prompt — subagent has no session history
- Two-stage review: spec compliance, then code quality
- Model selection: haiku for mechanical tasks, sonnet for complex ones

## EOS-Specific Rules
- Import check: `python3 -c "import sys; sys.path.insert(0,'/opt/OS'); import eos_ai; print('clean')"` after every Python change
- Docker: `docker restart os-discord` (container name), not `docker compose restart`
- Python-only changes: restart only, never rebuild
- Before deploy: import check → restart → check logs

## Common Failures and Fixes
- Context overflow: break into smaller subagent tasks
- Import error after rename: grep for old path, update remaining references
- Docker container not picking up changes: verify restart completed, check logs

## Skill Development
- New skills go in skills/[dept]/[name]/SKILL.md
- Sync new skills to Neon after creating
- Tool skills go in skills/tools/[tool]/
