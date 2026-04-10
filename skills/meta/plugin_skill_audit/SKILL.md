---
name: plugin-skill-audit
description: "Use when auditing installed Claude Code plugins to understand what skills are available outside /opt/OS/skills/, or when debugging why a plugin skill is or is not triggering"
trigger: conversational
effort: medium
context: fork
---

# Plugin Skill Audit

Audits every Claude Code plugin skill loaded into the active session
and records them in `registry.md` next to this file. The registry is
the single source of truth for "what plugin surface exists outside
EOS" and what trigger conflicts exist with `/opt/OS/skills/tools/`.

## Why this exists

EOS owns its own skill library under `/opt/OS/skills/`. Plugins
installed into `~/.claude/plugins/` add a parallel skill surface that
CC can auto-trigger without the developer noticing. When a plugin
skill description overlaps an EOS tool skill, CC may pick the plugin
version and bypass EOS conventions (model routing, Neon registration,
verification steps). This audit makes that surface visible.

## What `registry.md` contains

- One row per loaded plugin skill, grouped by plugin
- Trigger condition (what makes CC fire the skill)
- A `Conflicts & Overlaps` section listing every plugin skill whose
  trigger overlaps an EOS tool skill or core EOS protocol

## How to update

Re-run the audit:
1. Read the active CC session's loaded-skills manifest (system-reminder
   block at session start lists every plugin skill with its plugin
   prefix). This is more reliable than globbing
   `/root/.claude/plugins/cache/` which often hits `E2BIG`.
2. For each plugin skill, capture: plugin name, skill name, trigger
   (description field), and a one-line note.
3. Re-glob `/opt/OS/skills/tools/*` and re-compute the
   Conflicts & Overlaps section by matching tool slugs against plugin
   skill names and triggers.
4. Overwrite `registry.md` in place. Diff against the prior version
   to surface plugins that changed silently.

## Verification

After updating registry.md:
- Confirm every plugin prefix in the session manifest appears at least
  once in the table.
- Confirm every directory under `/opt/OS/skills/tools/` is checked
  against plugin skill names — if an EOS tool has no overlap, that is
  fine, but the check must have happened.
- `git diff /opt/OS/skills/meta/plugin_skill_audit/registry.md` and
  read every changed row out loud — silent plugin upgrades show up
  here as renamed or reworded triggers.

## Gotchas

- Plugin version updates rewrite SKILL.md files in
  `~/.claude/plugins/cache/` without notice. A skill that was safe
  yesterday can have a broader trigger today. Always diff.
- `/root/.claude/plugins/` often breaks `Glob` and `find` with
  `spawn E2BIG` because of the size of the cache tree. Use the CC
  session-loaded skill manifest as the authoritative input instead of
  walking the filesystem.
- Plugin skills with `mcp__*` tool allow-lists pull in MCP servers
  that may not be configured in EOS — triggering them can hang.
- `superpowers:*`, `skill-creator:*`, and `plugin-dev:skill-development`
  all want to own skill authoring. EOS skill rules
  (`/opt/OS/.claude/rules/skills.md`) override all three — never let
  a plugin skill author a SKILL.md without a Gotchas section and a
  verification step.
- `claude-api` (builtin) triggers on `anthropic` SDK imports and will
  push toward direct SDK use. EOS code MUST route through
  `eos_ai/model_router.py::call_with_fallback`.
- Apify plugin ships 8 separate skills that overlap the single EOS
  apify tool skill. The EOS skill is canonical for project work.
