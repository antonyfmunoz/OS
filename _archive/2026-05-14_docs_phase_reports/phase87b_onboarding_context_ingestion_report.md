# Phase 87B — Tool-Agnostic Onboarding Context Ingestion + Source Assimilation v1

**Date**: 2026-05-03
**Status**: Complete
**Extends**: Phase 87A (Distributed Node Registry + Runtime Routing v1)
**Tests**: 164 passing (Phase 87B), 509 total (Phase 86 + 87 + 87A + 87B)
**Safety**: 10 modules checked, 0 violations, 0 warnings
**Hard rules**: 20

## Executive Summary

Phase 87B introduces the Tool-Agnostic Onboarding Context Ingestion system —
a typed taxonomy that models how any user's data sources should be discovered,
classified, permissioned, routed, reviewed, and progressively onboarded into EOS.

Four doctrines govern the system:

1. **Source-Class Abstraction Doctrine** — Apps are not the primitive. Source
   classes are. Gmail, Outlook, Apple Mail are all implementations of "email."
2. **Permission-First Ingestion Doctrine** — No source ingested until user
   approves scope, access method, node location, sensitivity, review behavior.
3. **User Instance Onboarding Ingestion Doctrine** — Ingestion is part of first
   boot, not optional later utility. Progressive tiers from manual to continuous.
4. **Raw Before Memory Doctrine** — Raw artifacts → parsed candidates → review →
   confidence/conflict/supersession checks → promotion. No shortcut.

The system maps 28 source classes across 46 platforms, 12 modalities, 12 access
methods, 6 progressive onboarding tiers, and integrates with Phase 87A's
distributed node routing for source-to-node affinity.

Integration with existing `umh/distributed/` is read-only — imports enums
(CapabilityDomain, RuntimeNodeType, SourceAffinity) but does not modify any
Phase 87A files.

Advisory/planning only. No scraping. No API calls. No account connections.
No file reading. No memory promotion. No execution. Deterministic v1.

## Relationship to Existing Modules

| Module | Phase | Focus |
|--------|-------|-------|
| `umh/distributed/` (8 files) | Phase 87A | Node taxonomy, capability mapping, routing advisory |
| `umh/ingestion/` (11 files) | **Phase 87B** | **Source taxonomy, tool-stack discovery, onboarding, permissions, routing, review** |

Phase 87B reads from Phase 87A's enums for routing integration.
Phase 87B does NOT modify any existing module.

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `umh/ingestion/__init__.py` | 5 | Package marker |
| `umh/ingestion/contracts.py` | ~580 | 12 enums, 12 normalizers, 5 dataclasses, helpers |
| `umh/ingestion/source_classes.py` | ~411 | 28 source-class-to-platform mappings, modalities, access, tier, sensitivity, priority, cadence defaults |
| `umh/ingestion/tool_stack.py` | ~105 | Tool-stack profile building, coverage gaps, suggestions |
| `umh/ingestion/onboarding.py` | ~279 | 6 progressive tiers, plan generation, prerequisites, success criteria |
| `umh/ingestion/permissions.py` | ~146 | Permission requests, grant validation, readiness checks, risk classification |
| `umh/ingestion/source_registry.py` | ~429 | 20 seed source configurations, filters by tier/class/sensitivity |
| `umh/ingestion/routing.py` | ~227 | Source-to-node routing via Phase 87A integration, affinity/capability mapping |
| `umh/ingestion/review_policy.py` | ~210 | 8 default review policies, auto-promote logic, supersession checks |
| `umh/ingestion/views.py` | ~293 | 6 UI-safe view types, converters, dashboard builder |
| `umh/ingestion/safety.py` | ~205 | AST-based safety checking (expanded patterns including scrape/fetch/crawl) |
| `tests/test_phase87b_onboarding_context_ingestion.py` | ~1378 | 156 tests across 16 test classes |

## Files Modified

| File | Change | Risk |
|------|--------|------|
| `docs/strategy/current_doctrine_index.md` | Added 4 new doctrines (Source-Class Abstraction, Permission-First, Onboarding Ingestion, Raw Before Memory) | LOW |
| `docs/strategy/war_sprint_context_manifest.md` | Added Phase 87B as Complete | LOW |
| `docs/strategy/source_ingestion_map.md` | Added 4 doctrine references in Governing Doctrines section | LOW |
| `docs/strategy/ai_chat_archive_ingestion_plan.md` | Added Phase 87B foundation reference in Future Module section | LOW |

## Enums (12)

| Enum | Count | Purpose |
|------|-------|---------|
| SourceClass | 29 | email, calendar, task_management, note_taking, ... 3d_modeling, unknown |
| PlatformType | 47 | gmail, outlook, notion, github, instagram, stripe, chatgpt, claude, ... unknown |
| SourceModality | 12 | text, image, video, audio, structured_data, code, pdf, rich_text, conversation, feed, transaction, unknown |
| AccessMethod | 12 | official_api, oauth, api_key, export_file, browser_session, local_filesystem, ... unknown |
| PermissionScope | 11 | read_only, read_write, read_metadata, read_content, read_analytics, ... unknown |
| OnboardingTier | 8 | tier_0_manual_core through tier_5_continuous, deferred, unknown |
| IngestionPriority | 7 | critical, high, medium, low, background, deferred, unknown |
| SourceSensitivity | 6 | public, internal, confidential, financial, credential, unknown |
| ReviewRequirement | 7 | none, spot_check, sample_review, full_review, approval_required, legal_review, unknown |
| MemoryPromotionPolicy | 8 | auto_promote, confidence_threshold, human_review, batch_review, never_promote, supersession_check, conflict_resolution, unknown |
| SourceStatus | 12 | discovered through blocked + unknown |
| RefreshCadence | 8 | real_time, hourly, daily, weekly, on_demand, one_time, continuous, unknown |

## Progressive Onboarding Tiers (6)

| Tier | Focus | Example Sources |
|------|-------|----------------|
| Tier 0: Manual Core | User declares identity, goals, companies | (manual entry only) |
| Tier 1: Local Archives | AI chat exports, notes, voice memos, ebooks | ai_assistant, note_taking, voice_memo |
| Tier 2: Workspace | Email, calendar, tasks, docs, code, messaging | email, calendar, code_repository, messaging |
| Tier 3: Social/Algorithm | Social media, video, advertising | social_media, video_platform, advertising |
| Tier 4: Computer-Use | Browser history, screen capture | browser_history, screen_capture |
| Tier 5: Continuous | Real-time webhooks, live feeds | (continuous versions of all above) |

## Seed Sources (20)

| Platform | Source Class | Tier | Sensitivity | Priority |
|----------|-------------|------|-------------|----------|
| Gmail | email | Tier 2 | confidential | high |
| Google Calendar | calendar | Tier 2 | internal | high |
| Obsidian | note_taking | Tier 1 | internal | high |
| Notion | note_taking | Tier 2 | internal | high |
| GitHub | code_repository | Tier 2 | internal | high |
| Discord | messaging | Tier 2 | confidential | high |
| Telegram | messaging | Tier 2 | confidential | high |
| Instagram | social_media | Tier 3 | public | medium |
| Twitter/X | social_media | Tier 3 | public | medium |
| LinkedIn | social_media | Tier 3 | public | medium |
| TikTok | social_media | Tier 3 | public | medium |
| YouTube | video_platform | Tier 3 | public | low |
| Stripe | payment_processing | Tier 2 | financial | critical |
| ChatGPT | ai_assistant | Tier 1 | confidential | high |
| Claude | ai_assistant | Tier 1 | confidential | high |
| Google Drive | cloud_storage | Tier 2 | internal | medium |
| Apple Notes | note_taking | Tier 1 | internal | high |
| Google Analytics | analytics | Tier 2 | internal | medium |
| Docker | container_runtime | Tier 2 | internal | low |
| Calendly | task_management | Tier 2 | internal | medium |

## Default Review Policies (8)

| Policy | Source Class | Promotion | Threshold |
|--------|-------------|-----------|-----------|
| Public Content | social_media | batch_review | 0.70 |
| Workspace Documents | document_editing | confidence_threshold | 0.80 |
| Messaging / Conversations | messaging | human_review | 0.85 |
| Financial Data | payment_processing | human_review | 0.95 |
| AI Chat Archives | ai_assistant | supersession_check | 0.80 |
| Calendar / Scheduling | calendar | auto_promote | 0.60 |
| Code Repositories | code_repository | auto_promote | 0.70 |
| Email | email | confidence_threshold | 0.80 |

## Safety Validation

- **Modules checked**: 10 (all ingestion/*.py except __init__)
- **Forbidden imports**: 0 (subprocess, requests, httpx, aiohttp, socket, selenium, playwright, smtplib, telegram, discord, paramiko, scrapy, bs4)
- **Forbidden module prefixes**: 0 (umh.adapters, umh.execution, umh.governance, umh.memory, umh.storage)
- **Execution patterns**: 0 (execute, run_action, send_message, scrape, ingest, fetch, crawl, download)
- **Network listener patterns**: 0 (bind, listen, serve, accept, start_server, run_server)
- **Secret patterns**: 0 (os.getenv, load_dotenv, os.environ)

### Safety Reconciliation (Phase 87B.1)

During Phase 87B, an intermediate validation run showed "Modules checked: 0"
while the final report correctly stated 10 modules. Phase 87B.1 investigated
and reconciled.

**Root cause**: `check_all_ingestion_modules()` used `Path(__file__).parent`
with no fallback and no guard for zero results. If called before all modules
were written, from a different cwd without sys.path, or in a context where
`__file__` resolved unexpectedly, it would silently return 0 modules with
`all_safe: True` — a false positive.

**Fix applied** (Phase 87B.1):
1. Added explicit `ingestion_dir` parameter with `Path(__file__).parent` default
2. Added non-existent directory guard — returns `all_safe: False` with warning
3. Added empty-directory guard — 0 modules is now `all_safe: False` with warning
4. Added `scanned_paths` list — full traceability of which files were scanned
5. Added `warning_count` field — aggregates per-module + scan-level warnings
6. Added 8 new tests covering: module count positive, scanned_paths, warning_count,
   explicit dir, non-existent dir, empty dir, forbidden module prefix detection,
   network listener pattern detection

**Post-reconciliation**: 10 modules, 0 violations, 0 warnings, 10 scanned paths verified.

## Tests

| Class | Tests | Covers |
|-------|-------|--------|
| TestContractEnums | 19 | All 12 enums, UNKNOWN fallback, member counts, str-based |
| TestContractNormalizers | 16 | All 12 normalizers + unknown degradation + passthrough |
| TestContractHelpers | 3 | _ingest_id format/uniqueness/prefix |
| TestContractSerialization | 5 | All 5 dataclass to_dict/from_dict round-trips |
| TestSourceClasses | 16 | Platform mapping, classification, modalities, access, tier, sensitivity, priority, completeness |
| TestToolStack | 6 | Profile building, coverage gaps, suggestions |
| TestOnboarding | 11 | 6 tiers, prerequisites, warnings, next tier, effort, serialization |
| TestPermissions | 8 | Permission requests, grants, validation, risk classification, readiness |
| TestSourceRegistry | 9 | 20 seeds, unique IDs, filters, serialization, no credentials |
| TestRouting | 9 | Affinity, capability, node routing, 87A integration, warnings |
| TestReviewPolicy | 10 | 8 policies, auto-promote logic, supersession, urgency |
| TestViews | 7 | 6 converters + dashboard + no sensitive data |
| TestSafety | 15 | Module scan, fixture detection, source safety, scanned_paths, warning_count, explicit dir, empty dir, nonexistent dir, forbidden prefix, network listener |
| TestLayering | 4 | Per-file forbidden imports, no model_router, no LLM, distributed import |
| TestIntegration | 5 | Phase 87A compat, distributed enums, full pipeline, routing |
| TestPhase87BRegression | 10 | Phase 80–87B import smoke tests |
| TestToolAgnostic | 5 | No hardcoded names/URLs/paths, generic enums |
| TestSeedMapCompleteness | 6 | Modalities, access, permissions, financial review, supersession, tier coverage |
| **Total** | **164** | |

## Regression

- **Phase 87B tests**: 164/164 passing (156 original + 8 safety reconciliation)
- **Phase 87A tests**: 146/146 passing (unchanged)
- **Phase 87 tests**: 118/118 passing (unchanged)
- **Phase 86 tests**: 81/81 passing (unchanged)
- **Combined regression**: 509/509 passing
- **Safety validation**: 10 modules, 0 violations, 10 scanned paths, 0 warnings

## Known Limitations

- Advisory/planning only — no execution
- No actual API connections, scraping, or file reading
- No actual memory promotion or supersession execution
- Tool-stack discovery is declaration-based, not automatic detection
- Seed sources are static — no dynamic platform discovery
- No live OAuth flow implementation
- No actual browser session management
- Review pipeline is contract-only — no processing engine
- Registry/observability/API/CLI integration deferred

## Is Phase 88 Template System Safe?

Yes. Phase 88 can safely build on Phase 87B:
- Source class taxonomy informs what templates need to handle
- Onboarding tier plans can become template-driven workflows
- Permission/review policies inform template authorization requirements
- Source-to-node routing tells templates where data lives
- No Phase 87B code needs modification — Phase 88 extends, not changes
