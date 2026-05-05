# TME / Adapter Engine Relationship — Doctrine v1

**Phase**: TME Scope Correction (pre-96.7)
**Status**: ACTIVE
**Date**: 2026-05-05

---

## Core Rule

TME and the Adapter Engine are separate UMH substrate subsystems with a producer-consumer relationship. TME produces Tool Mastery Packs. The Adapter Engine consumes them as Layer 4 of 8-layer Adapter Packages.

## The Two Subsystems

### Tool Mastery Engine (TME)
- **Domain**: Expert-level tool knowledge
- **Produces**: Tool Mastery Packs (structured operational expertise)
- **Owns**: Decision tree, create flow, re-research flow, staleness thresholds, quality tiers, 19-section research protocol
- **Interface**: `/opt/OS/skills/tools/{toolname}/SKILL.md` (file-based) + `ensure_tool_mastery()` (programmatic)
- **Scope**: UMH substrate (not EOS-specific)

### Adapter Engine
- **Domain**: Operational integration of external tools
- **Produces**: 8-layer Adapter Packages
- **Owns**: Access adapters, auth adapters, capability maps, governance policies, execution wrappers, tests, registry
- **Interface**: `AdapterPackage` dataclass + Selection Engine + Worker Runtime
- **Scope**: UMH substrate (not EOS-specific)

## How TME Feeds the Adapter Engine

```
TME                                    Adapter Engine
────                                   ──────────────
1. TME creates tool skill              
   /skills/tools/{tool}/SKILL.md       
                                       2. Adapter Factory runs
                                          TOOL_MASTERY_GENERATION stage
                                       
3. build_tool_mastery_pack_from_skill()
   loads skill → ToolMasteryPack       
                                       4. ToolMasteryPack becomes
                                          Layer 4 of AdapterPackage
                                       
                                       5. Quality gate checks
                                          tool_mastery_is_mature()
                                       
                                       6. If mature → adapter promotable
                                          If not → adapter blocked
```

## What TME Does NOT Do

- TME does not create access adapters (Layer 1)
- TME does not manage auth (Layer 2)
- TME does not enumerate capabilities (Layer 3)
- TME does not set governance policy (Layer 5)
- TME does not implement execution wrappers (Layer 6)
- TME does not write adapter tests (Layer 7)
- TME does not manage the adapter registry (Layer 8)

TME provides knowledge. The Adapter Engine provides integration.

## What the Adapter Engine Does NOT Do

- The Adapter Engine does not research tools
- The Adapter Engine does not maintain staleness thresholds
- The Adapter Engine does not run quality audits on tool knowledge
- The Adapter Engine does not own the 19-section research protocol
- The Adapter Engine does not absorb community knowledge repos

The Adapter Engine consumes mastery. TME creates and maintains it.

## Selection Engine and Worker Runtime

- **Selection Engine** chooses which Adapter Package to use for a task. It considers the mastery pack's maturity when scoring candidates.
- **Worker Runtime** executes through the selected adapter. It loads the mastery pack's guidance (e.g., "set `includeTabsContent=true`") and applies it during execution.
- **Control Plane** provides both advisory (`query_relevant_skills`) and active (`ensure_tool_mastery`) paths for TME integration.

## Why They Must Stay Separate

1. **Different update cadences** — TME mastery packs update when tool knowledge changes (API versions, community discoveries). Adapter code updates when integration logic changes. These are independent triggers.
2. **Different ownership** — TME is maintained by the research protocol. Adapters are maintained by engineering.
3. **Reusability** — One TME mastery pack can serve multiple adapters for the same tool (e.g., API adapter and MCP adapter for Google Docs both reference the same mastery pack).
4. **Platform independence** — TME mastery packs are usable by any UMH consumer. Adapter code may have platform-specific bindings.

## Hard Rules

- TME does not depend on the Adapter Engine. TME can exist and produce mastery packs without any adapters.
- The Adapter Engine depends on TME for Layer 4 content. An adapter without mastery is technically connected but operationally ignorant.
- TME and Adapter Engine are both UMH substrate subsystems, not EOS-specific.
- A single TME mastery pack can serve multiple adapters for the same tool.

## References

- `docs/operations/tme_umh_substrate_doctrine_v1.md` — TME UMH substrate doctrine
- `docs/operations/adapter_package_doctrine_v1.md` — 8-layer bundle model
- `docs/operations/adapter_engine_doctrine_v1.md` — Adapter Engine doctrine
- `docs/operations/tool_mastery_pack_doctrine_v1.md` — mastery pack requirements
- `eos_ai/substrate/adapter_engine_contracts.py` — AdapterPackage, ToolMasteryPack dataclasses
- `eos_ai/substrate/adapter_best_practices_loader.py` — build_tool_mastery_pack_from_skill()
- `core/action_system/tme.py` — Control Plane TME integration
