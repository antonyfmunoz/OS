# Template Candidate Inventory v1

**Date**: 2026-05-03
**Phase**: 89 — Controlled Ingestion Batch + Context Rehydration v1
**Source**: Extracted from local files — strategy docs, operations docs, phase reports, workflow modules

---

## What This Is

Templates are repeating patterns that should be standardized so they never need to be rebuilt from scratch. This inventory catalogs every template candidate found during context rehydration, whether it already exists as a template, exists as a one-off that should be promoted, or is missing entirely.

---

## Existing Templates (Already Formalized)

| # | Template | Location | Status | Used By |
|---|----------|----------|--------|---------|
| 1 | Daily test run template (business track) | `docs/operations/business_workflow_test_run_template.md` | ACTIVE | BOT-001+ |
| 2 | Daily test run template (self-build track) | `docs/operations/self_build_workflow_test_run_template.md` | ACTIVE | Self-build tests |
| 3 | Daily test run template (generic) | `docs/operations/first_workflow_test_run_template.md` | ACTIVE | Phase 88 generic |
| 4 | North Star test run template | `docs/operations/north_star_test_run_template.md` | ACTIVE | Dual-track tests |
| 5 | EA soul doc template | `agents/ea_template.md` | ACTIVE | New EA agent creation |
| 6 | Phase report template | (implicit in phase reports) | IMPLICIT | All phase reports follow same structure |
| 7 | Agent soul doc structure | `agents/CLAUDE.md` | DOCUMENTED | 5-section structure documented |
| 8 | CC subagent structure | `.claude/agents/*.md` | DOCUMENTED | Frontmatter + gotchas + verification |
| 9 | SKILL.md structure | `.claude/rules/skills.md` | DOCUMENTED | All 158 skills follow this |
| 10 | KPI capture template | `umh/workflows/kpis.py` → `build_default_kpis_for_first_workflow()` | CODE | Daily KPI tracking |

---

## One-Off Patterns That Should Become Templates

These patterns exist in a single file but repeat or would repeat across future operations.

### Revenue Operations Templates

| # | Pattern | Found In | Repeats When | Template Action |
|---|---------|----------|-------------|----------------|
| 11 | Objection capture table | `business_test_001_packet.md` | Every outreach day | Extract to standalone objection tracker template |
| 12 | Qualification criteria (3-of-5) | `business_test_001_packet.md` | Every prospect evaluation | Extract to qualification scorecard template |
| 13 | Outreach playbook (6-step approach) | `business_test_001_packet.md` | Every outreach session | Extract to outreach SOP template |
| 14 | Prospect disqualification criteria | `business_test_001_packet.md` | Every prospect evaluation | Include in qualification scorecard |
| 15 | Content angle selection | `business_test_001_packet.md` | Every content day | Extract to content angle picker template |
| 16 | Hook formula | `business_test_001_packet.md` | Every piece of content | Extract to hook formula library |
| 17 | End-of-day review structure | `business_test_001_packet.md` + `results.md` | Every operating day | Already exists in test templates — confirm it generalizes |
| 18 | Non-actions / distraction blocklist | `business_test_001_packet.md` | Every operating day | Extract to daily guardrails template |

### System/Development Templates

| # | Pattern | Found In | Repeats When | Template Action |
|---|---------|----------|-------------|----------------|
| 19 | Phase report structure | All `docs/system/phase*_report.md` | Every phase completion | Formalize as `docs/templates/phase_report_template.md` |
| 20 | Safety scan pattern | `umh/workflows/safety.py` | Every new module category | Extract forbidden-import/execution-pattern config to template |
| 21 | Contract dataclass pattern | `umh/workflows/contracts.py` | Every new domain module | Document the `_normalize()` + `UNKNOWN` + `_wf_id()` pattern |
| 22 | Test file structure | `tests/test_phase88_*.py` | Every new phase test | Formalize 11-class test organization pattern |
| 23 | Doctrine addition to strategy docs | Phase 87C strategy doc updates | Every phase that produces doctrines | Checklist: doctrine_index + source_ingestion_map + war_sprint_manifest |

### Operational Templates

| # | Pattern | Found In | Repeats When | Template Action |
|---|---------|----------|-------------|----------------|
| 24 | Bottleneck capture + fix tracking | `business_test_001_packet.md` | Every operating day | Included in test templates — verify standalone value |
| 25 | Win/loss capture | `business_test_001_packet.md` | Every operating day | Included in test templates — verify standalone value |
| 26 | Leverage-sorted task list | `umh/workflows/test_harness.py` | Every daily plan | Already in code — expose as operator-facing format |
| 27 | KPI comparison report | `umh/workflows/kpis.py` | Every review cycle | `compare_kpis_to_targets()` exists — need printable format |
| 28 | Next-day improvement recommendation | `umh/workflows/test_harness.py` | Every review cycle | Already in code — expose as operator-facing prompt |

---

## Missing Templates (Don't Exist Yet)

| # | Template Needed | Why | Priority | Create When |
|---|----------------|-----|----------|------------|
| 29 | Sales call script | No documented call flow for Initiate Arena | HIGH | Before first call booked |
| 30 | Onboarding checklist | No documented student onboarding process | HIGH | Before first sale closes |
| 31 | Fulfillment tracker | No documented delivery tracking | HIGH | Before first sale closes |
| 32 | Testimonial capture script | No documented testimonial request process | MEDIUM | After first student completes |
| 33 | Objection response library | Objections listed but no scripted responses | HIGH | Iteratively from BOT-001+ data |
| 34 | Content calendar template | No standardized content planning format | MEDIUM | When content becomes regular |
| 35 | Lead CRM entry format | No standardized lead record format | HIGH | Before lead volume increases |
| 36 | Weekly review template | Daily exists but no weekly rollup | MEDIUM | After 7+ operating days |
| 37 | Monthly review template | No monthly review process documented | LOW | After 30+ operating days |
| 38 | New venture kickstart template | No standardized process for activating new entity | LOW | When Empyrean Studio activates |
| 39 | Client project template | No standardized Empyrean Studio project structure | LOW | When Empyrean Studio activates |
| 40 | Agent creation checklist | Process exists in skills but no operator-facing checklist | MEDIUM | When non-developer creates agents |

---

## Template Priority Matrix

### Must-Have Before First Sale

| Template | Exists? | Action |
|----------|---------|--------|
| Objection response library | NO | Create from BOT-001+ outreach data |
| Sales call script | NO | Create before first call booked |
| Lead CRM entry format | NO | Create before lead volume increases |
| Onboarding checklist | NO | Create before first sale closes |
| Fulfillment tracker | NO | Create before first sale closes |
| Payment collection process | NO | Create before first sale closes |

### Should-Have for Consistent Execution

| Template | Exists? | Action |
|----------|---------|--------|
| Daily operating packet | YES | `business_workflow_test_run_template.md` |
| KPI tracker | YES | In code + test templates |
| Qualification scorecard | PARTIAL | Exists in BOT-001 packet, needs extraction |
| Outreach SOP | PARTIAL | Exists in BOT-001 packet, needs extraction |
| Content angle picker | PARTIAL | Exists in BOT-001 packet, needs extraction |
| Phase report template | IMPLICIT | Formalize from existing pattern |

### Nice-to-Have for Scale

| Template | Exists? | Action |
|----------|---------|--------|
| Weekly review rollup | NO | Create after 7+ operating days |
| Monthly review rollup | NO | Create after 30+ operating days |
| New venture kickstart | NO | Create when second entity activates |
| Testimonial capture script | NO | Create after first student completes |

---

## Operationalization Notes

Per the Operationalization Principle: after anything works → document → skill or template → never rebuild from scratch → always improvable.

**Immediate actions after BOT-001 execution**:
1. Extract any pattern that repeated into a template
2. Promote any template that worked into the `docs/operations/` directory
3. Update this inventory with new discoveries
4. Mark any template that failed or was unused

**Template naming convention**: `{domain}_{purpose}_template.md`
- `outreach_qualification_scorecard_template.md`
- `sales_call_script_template.md`
- `content_angle_picker_template.md`
