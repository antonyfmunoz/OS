# Deletion Ledger — Phase 3

**Date:** 2026-05-27

## Items Removed

### Dead Scripts (git rm)

| File | Reason | Import Search |
|------|--------|--------------|
| scripts/wiki_session_start_hook.py | Explicitly a no-op (docstring says "Previously created...") | Only referenced in historical audit doc |
| scripts/fix_founder_refs.py | One-time fixer, job completed | 0 importers |
| scripts/fix_merge_conflicts.py | One-time fixer, job completed | 0 importers |

### Broken Symlinks (git rm)

| Symlink | Target | Status |
|---------|--------|--------|
| knowledge/agents/business | /opt/OS/12_Agents | Target doesn't exist |
| knowledge/workflows/business | /opt/OS/05_Workflows | Target doesn't exist |

## Items NOT Removed (documented only)

### Empty Directories (untracked — only in main worktree)
- services/handlers/ — empty, untracked
- services/jarvis/ — empty, untracked
- services/umh/ — only contains untracked data files
- .claire/worktrees/ — untracked
- 10_Wiki/ — untracked

These exist only as untracked items in the main worktree, not in git.
They cannot be removed via git operations. Manual cleanup on main recommended.

### Historical Archive (preserved, not deleted)
12 services files classified HISTORICAL_ARCHIVE — they contain unique logic
(ICP scoring, cost tracking, magic link auth) but are not imported by production.
Preserved for reference. May be promoted to CANONICAL_FUTURE or cleaned up in a later sprint.

## Bug Fixes Applied During Phase 3

| File | Fix |
|------|-----|
| substrate/control_plane/context/__init__.py | ConversationMemory() called without ctx arg — added SimpleNamespace(org_id=...) |
| substrate/control_plane/memory.py | ConcreteMemorySystem.__init__() — made ctx optional, passes to ConversationMemory when available. Fixed store() and log_interaction() API mismatches. |
