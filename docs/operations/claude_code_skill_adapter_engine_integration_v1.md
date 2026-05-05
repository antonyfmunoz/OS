# Claude Code Skill — Adapter Engine Integration — Doctrine v1

**Phase**: 96.5  
**Status**: ACTIVE  
**Date**: 2026-05-04

---

## Core Rule

The Claude Code Best Practices Skill (`.claude/skills/claude-code-cli.md`) is classified as **ToolMasteryPack: Claude Code**. It belongs inside the Claude Code Adapter Package as Layer 4 (Tool Mastery Pack). This is not a metaphor — the skill file is the mastery layer for the Claude Code adapter.

## Classification

| Attribute | Value |
|-----------|-------|
| Skill file | `.claude/skills/claude-code-cli.md` |
| Classification | ToolMasteryPack |
| Tool | Claude Code |
| Adapter Package | Claude Code Adapter |
| Layer position | 4 of 8 (Tool Mastery Pack) |

## How It Works

1. **Skill file exists** at `.claude/skills/claude-code-cli.md` — contains best practices, workflows, failure modes, edge cases, and quality standards for Claude Code usage.
2. **`adapter_best_practices_loader.py`** (now "Tool Mastery Pack loader") reads and parses skill files into structured `ToolMasteryPack` instances.
3. **`build_tool_mastery_pack_from_skill()`** is the bridge function — it takes a skill file path and returns a `ToolMasteryPack` object that the Adapter Engine can consume.
4. **The Adapter Engine** stores the mastery pack at Layer 4 of the Claude Code adapter package, making it available during backend selection and worker execution.

## Why This Matters

- Tool Mastery Packs are not external references — they are internal adapter layers. The Claude Code skill file was always a mastery pack; this integration formalizes that relationship.
- When the Adapter Engine selects the Claude Code backend for a task, the mastery pack informs execution — not just connectivity, but expert-level usage patterns.
- The loader pattern (`build_tool_mastery_pack_from_skill()`) is reusable. Any skill file that encodes tool expertise can be loaded as a mastery pack for its corresponding adapter.

## Loader Interface

```python
from eos_ai.adapter_best_practices_loader import build_tool_mastery_pack_from_skill

pack = build_tool_mastery_pack_from_skill(
    skill_path=".claude/skills/claude-code-cli.md",
    tool_name="claude_code"
)
# Returns ToolMasteryPack with:
#   .best_practices: list[str]
#   .workflows: list[dict]
#   .failure_modes: list[dict]
#   .edge_cases: list[str]
#   .quality_standards: list[str]
```

## Hard Rules

- Never duplicate mastery content between the skill file and a separate mastery doc. The skill file IS the mastery source.
- Never load a mastery pack without validating it has at least best_practices and failure_modes populated.
- Never treat the Claude Code skill as "just a skill" — it is a classified adapter layer with a defined position in the 8-layer model.

## References

- `.claude/skills/claude-code-cli.md` — source skill / mastery pack
- `eos_ai/adapter_best_practices_loader.py` — Tool Mastery Pack loader
- `eos_ai/adapter_engine.py` — consumer of mastery packs
- `docs/operations/adapter_engine_doctrine_v1.md` — 8-layer model
