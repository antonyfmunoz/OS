# TME Scope Correction + Conflict Stabilization — Report v1

**Phase**: TME Scope Correction (pre-96.7)
**Status**: COMPLETE
**Date**: 2026-05-05

---

## 1. Executive Summary

The Tool Mastery Engine (TME) scope has been corrected from "EOS subsystem" to "UMH substrate subsystem." EOS is demoted from owner to platform consumer. Merge conflict markers in SKILL.md and CLAUDE.md have been resolved. Three new doctrine docs establish the corrected relationship between TME, Adapter Engine, Adapter Packages, and Worker Runtime.

## 2. Founder Correction

The founder clarified that TME is not meant to be EOS-specific. TME belongs to the Universal Meta Harness (UMH) substrate. EOS, LyfeOS, CreatorOS, and other platforms may consume TME outputs, but they do not own TME.

**Before**: "TME governs every build in EOS"
**After**: "TME governs every external tool, SaaS, API, adapter, runtime, and capability UMH touches."

## 3. TME Is UMH Substrate, Not EOS-Specific

TME creates and maintains Tool Mastery Packs — structured expert-level knowledge about external tools. This knowledge is platform-independent. Any UMH runtime, any platform consumer, any Adapter Package can reference TME-produced mastery packs.

TME's 19-section research protocol, staleness thresholds, quality tiers, and decision tree are all UMH-level concerns, not EOS-level concerns.

## 4. EOS as Consumer/Projection, Not Owner

EOS is one platform that projects TME outputs into its workflows:
- EOS agents load tool skills via the TME decision tree
- EOS Adapter Packages reference TME-produced Tool Mastery Packs as Layer 4
- EOS workers execute using mastery guidance from TME
- EOS syncs tool skills to its Neon database for runtime query

Other platforms (LyfeOS, CreatorOS, future platforms) can consume the same TME outputs through their own projection mechanisms.

## 5. Current TME File Locations

| Component | Path |
|-----------|------|
| Engine skill (decision tree, create/re-research flows) | `/opt/OS/skills/meta/tool_mastery_engine/SKILL.md` |
| System reference (5 utility scripts, operating workflow) | `/opt/OS/docs/system/tool_mastery_engine_system.md` |
| Control Plane integration (advisory + active paths) | `/opt/OS/core/action_system/tme.py` |
| Utility: shared loader | `/opt/OS/scripts/_tme_common.py` |
| Utility: Neon sync | `/opt/OS/scripts/sync_skills_to_neon.py` |
| Utility: linter/verifier | `/opt/OS/scripts/verify_tool_skill.py` |
| Utility: staleness audit | `/opt/OS/scripts/check_skill_staleness.py` |
| Utility: dependency graph | `/opt/OS/scripts/build_skill_graph.py` |
| Utility: CLI registry | `/opt/OS/scripts/query_skills.py` |
| Tool skills (~89+) | `/opt/OS/skills/tools/{toolname}/SKILL.md` |
| Tool Mastery Manager | `/opt/OS/core/tool_mastery_manager/` |
| Tool Mastery Research Agent | `/opt/OS/core/tool_mastery_research_agent/` |

Note: TME implementation currently lives under `/opt/OS/` alongside EOS code. This is a legacy namespace — TME logically belongs to UMH substrate. No directory renaming was performed in this phase.

## 6. Conflict Markers Found and Resolved

### SKILL.md
- **Location**: `/opt/OS/skills/meta/tool_mastery_engine/SKILL.md`
- **Conflict**: `<<<<<<< Updated upstream` (line 1) through `>>>>>>> Stashed changes` (line 1141)
- **Content**: v4.0 (Updated upstream, 698 lines) duplicated by v3.0 (Stashed changes, 442 lines)
- **Resolution**: Kept v4.0 content (version 4.0, last_updated 2026-04-28). Removed v3.0 duplicate. v4.0 includes Context7 integration, parallel subagents, absorption pattern, expanded staleness thresholds (fast=14d), quality tiers, and 6 depth markers — all absent from v3.0.

### CLAUDE.md
- **Location**: `/opt/OS/CLAUDE.md`
- **Conflict**: `<<<<<<< Updated upstream` (line 1) through `>>>>>>> Stashed changes` (line 522)
- **Content**: Nearly identical versions. Updated upstream had `Extended thinking: always on (alwaysThinkingEnabled: true)` in Model Strategy; Stashed changes lacked it.
- **Resolution**: Kept Updated upstream version. TME section wording corrected from "These govern every build, configuration, and execution in EOS" to "These govern every build, configuration, and execution." Added "TME is a UMH substrate subsystem, not EOS-specific."

## 7. Scope Wording Corrected

| File | Original | Corrected |
|------|----------|-----------|
| `SKILL.md` | "This skill ensures EOS operates at creator-level expertise" | "TME is a UMH substrate subsystem that guarantees creator-level expertise with every external tool, SaaS, API, adapter, runtime, and capability UMH touches. [...] EOS is one platform consumer of TME." |
| `tool_mastery_engine_system.md` | "The Tool Mastery Engine (TME) is the EOS sub-system that guarantees creator-level expertise with every external tool." | "The Tool Mastery Engine (TME) is a UMH substrate subsystem that guarantees creator-level expertise with every external tool, SaaS, API, adapter, runtime, and capability UMH touches. EOS is one platform consumer of TME." |
| `CLAUDE.md` | "These govern every build, configuration, and execution in EOS. Apply them always." | "These govern every build, configuration, and execution. Apply them always." + "TME is a UMH substrate subsystem, not EOS-specific." |

## 8. Relationship to Adapter Engine

TME is not the Adapter Engine. The Adapter Engine integrates external capabilities. TME creates and maintains Tool Mastery Packs — the expert knowledge layer (Layer 4) that Adapter Packages consume.

- **Adapter Engine** = the UMH subsystem that makes external tools usable
- **TME** = the UMH subsystem that creates/maintains the expert knowledge those adapters need
- **Adapter Package** = 8-layer operational bundle that references a TME-produced Tool Mastery Pack

TME feeds into the Adapter Engine. The Adapter Engine does not own TME.

## 9. Relationship to Adapter Packages

Each mature Adapter Package has 8 layers. Layer 4 (Tool Mastery Pack) is populated by TME. The relationship:

1. TME creates a tool skill at `/opt/OS/skills/tools/{toolname}/SKILL.md`
2. The Adapter Engine's `build_tool_mastery_pack_from_skill()` loads this skill
3. The resulting `ToolMasteryPack` instance becomes Layer 4 of the `AdapterPackage`
4. The quality gate checks `tool_mastery_is_mature()` for all 4 critical sections
5. An adapter without a mature mastery pack is not promotable

## 10. Relationship to Worker Runtime

Worker Runtime executes through adapter packages using mastery guidance:
- Selection Engine chooses the right Adapter Package / access path
- Worker Runtime loads the adapter's Tool Mastery Pack
- Mastery guidance informs execution (e.g., setting `includeTabsContent=true`)
- Governance policy constrains execution
- The Control Plane's `ensure_tool_mastery()` can block execution if mastery is missing

## 11. What Was Intentionally Not Changed

- **No eos_ai package renaming** — TME code paths still use `eos_ai/substrate/`. This is a legacy namespace; renaming is deferred.
- **No Python code modified** — only markdown/doc files were changed. No imports, contracts, or tests were touched.
- **No TME skill content rewritten** — the v4.0 decision tree, create flow, re-research flow, incremental update flow, absorption pattern, quality tiers, staleness thresholds, and gotchas were preserved exactly as authored.
- **No Neon sync performed** — skill database state unchanged.
- **No automation wiring** — the 3 scheduled sweeps remain defined but not wired to the orchestrator cron.
- **No other docs modified** — only the 3 files with EOS-ownership phrasing and conflict markers were touched.
- **No memory promoted** — per explicit instruction.

## 12. Remaining Gaps

1. **TME code still in eos_ai/ namespace** — logically belongs under UMH substrate namespace. Deferred to avoid broad renaming.
2. **Automation not wired** — 3 scheduled TME sweeps (daily fast, 3-day medium, weekly full) are defined in SKILL.md but not connected to orchestrator cron.
3. **Neon sync state unknown** — unclear how many of ~89+ skills are actually synced to database vs. file-only.
4. **Control Plane tme.py still references EOS-specific paths** — `core/action_system/tme.py` shells out to `/opt/OS/scripts/query_skills.py`. The path is physically correct but semantically belongs to UMH.
5. **tool_mastery_pack_doctrine_v1.md** references `eos_ai/adapter_engine_contracts.py` and `eos_ai/adapter_quality_gate.py` — accurate paths but legacy namespace.
6. **EOS Usage Patterns section** in individual tool skills references EOS-specific integration points. This is correct behavior — EOS *is* a consumer, so EOS-specific patterns belong in the consumer section of each skill.

## 13. Phase 96.7A Completion Note

Phase 96.7A delivered the Mastery Assurance Gate, Natural Language Resolver, and Active Tool Context as UMH substrate subsystems. 94 new tests pass with zero regressions against the 25 existing Phase 96.6 tests. See `docs/system/phase967a_tme_mastery_assurance_resolver_report.md` for full details.

## 14. Recommended Next Gate

**BUILD_ADAPTER_PACKAGE_MVP_AFTER_TME_STABILIZATION**

TME scope is corrected. Conflict markers are resolved. The TME-to-Adapter-Engine relationship is documented. The next natural step is building the first real Adapter Package MVP that wires TME-produced mastery packs into an 8-layer bundle with working code paths.

Alternative gates if MVP is not the priority:
- `FIX_TME_AUTOMATION_WIRING` — wire staleness sweeps to orchestrator cron
- `REVIEW_TME_SKILL_DATABASE_SYNC` — audit which skills are synced to Neon
- `CONTINUE_TME_IMPLEMENTATION_AUDIT` — deeper audit of TME code paths

## References

- `docs/operations/tme_umh_substrate_doctrine_v1.md` — UMH substrate doctrine
- `docs/operations/tme_adapter_engine_relationship_v1.md` — TME/Adapter Engine relationship
- `docs/operations/adapter_package_doctrine_v1.md` — 8-layer bundle model
- `docs/operations/tool_mastery_pack_doctrine_v1.md` — mastery requirements
- `skills/meta/tool_mastery_engine/SKILL.md` — TME engine skill (v4.0)
- `docs/system/tool_mastery_engine_system.md` — TME system reference
