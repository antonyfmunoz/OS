# Docs Truth Report — Phase 7

**Date:** 2026-05-27

---

## Documents Fixed

### cloud.md (REWRITTEN)
- **Was:** "EOS Cloud — System Context" referencing eos_ai/memory.py, eos_ai/db.py (dead paths)
- **Now:** "UMH Cloud — System Context" with correct paths to substrate/ modules
- **Impact:** New AI sessions will no longer be misled about codebase structure

### docs/deploy.md (REWRITTEN)
- **Was:** Claims "SQLite-backed", "No external services required", references SQLite databases
- **Now:** Correctly describes Docker + Neon PostgreSQL deployment, lists all containers and ports
- **Impact:** Anyone deploying will get accurate instructions

### .claude/CLAUDE.md (FIXED)
- Removed nonexistent `transports/discord/bot.py` from component status
- Changed nonexistent `interface/` → `sockets/` in project structure
- **Impact:** CC sessions won't reference phantom files

### CLAUDE.md (FIXED)
- Changed `alwaysThinkingEnabled: true` → `false` to match settings.json reality
- **Impact:** Model strategy section now matches actual settings

### skills/tools/python/SKILL.md (FIXED)
- Changed `Python 3.12` → `Python 3.11` (Docker containers run 3.11)
- **Impact:** Python skill won't suggest 3.12+ syntax features

### knowledge/agents/business (REMOVED)
- Broken symlink to /opt/OS/12_Agents (doesn't exist)

### knowledge/workflows/business (REMOVED)
- Broken symlink to /opt/OS/05_Workflows (doesn't exist)

## Documents Verified — No Changes Needed

### README.md
Accurately describes UMH as a governed intelligence substrate. No changes needed.

### AGENTS.md
Clean and accurate. References correct paths (substrate/, adapters/, transports/).

### PROTOCOLS.md
Well-written and architecturally sound. Layer 0-3 protocol architecture is accurate.
"EOS" references in Layer 1-3 context are semantically correct (EOS is the active projection).

### knowledge/north-star.md
Does not exist. The $10K/month target is in CLAUDE.md (global instructions) which is correct.
No knowledge file to fix.

## Empty Palace Rooms

No empty palace rooms found. All rooms in `knowledge/palace/rooms/` have content.

## Knowledge Deduplication

Deferred — requires analysis of 135 concept files against wiki content.
Low risk (knowledge files are read-only context, not runtime dependencies).

## Remaining Stale References (documented, not fixed)

1. `skills/tools/python/SKILL.md` body still references `eos_ai/` namespace — skill body should
   be regenerated via TME when next used
2. `skills/tools/python/references/best_practices.md` references Python 3.12 — same
3. Several other tool skills may reference stale paths — recommend TME re-research cycle
