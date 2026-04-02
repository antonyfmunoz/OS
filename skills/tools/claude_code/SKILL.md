---
name: claude-code-tool
description: "Claude Code integration for EOS Developer Agent. Use when Developer Agent needs to execute code changes, file operations, or system modifications."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://docs.anthropic.com/en/docs/claude-code"
last_researched: "2026-04-01"
---

# Tool: Claude Code

## What This Tool Does
Claude Code is an agentic CLI for software development. It reads, writes, and edits files,
runs bash commands, and executes multi-step development tasks autonomously.

For EOS, Claude Code is the Developer Agent's execution environment.
The Developer Agent runs inside Claude Code. Claude Code IS the developer agent interface.

## EOS Integration
- Developer Agent uses Claude Code as primary execution tool
- Skills define HOW to build — Claude Code executes
- CLAUDE.md files at /opt/OS/ and /opt/OS/.claude/ provide session context
- Subagent pattern: main session dispatches specialized subagents per phase

## Key Capabilities
- File read/write/edit with full context
- Bash execution (tests, imports, Docker commands)
- Multi-file refactoring
- Parallel subagent dispatch
- MCP tool integration

## EOS-Specific Conventions
- Always run import check before declaring done
- Use `docker restart [container]` not `docker compose restart`
- Never rebuild Docker for Python-only changes
- Session state saved via SessionState.save() at end of significant builds
- skills in .claude/skills/ define repeatable workflows

See references/best_practices.md for skill patterns and session management.
